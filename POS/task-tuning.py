# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors and The HugginFace Inc. team.
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Code adapted from the examples in pytorch-pretrained-bert library"""

from __future__ import absolute_import, division, print_function

import argparse
import csv
import logging
import os
import random
import sys
import pickle

# os.environ['CUDA_VISIBLE_DEVICES'] = "0"

import numpy as np
import torch
from torch import nn
from torch.nn import CrossEntropyLoss
from torch.utils.data import (DataLoader, RandomSampler, SequentialSampler,
                              TensorDataset)
from torch.utils.data.distributed import DistributedSampler
from tqdm import tqdm, trange

from pytorch_pretrained_bert.file_utils import PYTORCH_PRETRAINED_BERT_CACHE
from pytorch_pretrained_bert.modeling import BertPreTrainedModel, BertModel, BertConfig, WEIGHTS_NAME, CONFIG_NAME
from pytorch_pretrained_bert.tokenization import BertTokenizer
from pytorch_pretrained_bert.optimization import BertAdam, warmup_linear

from crf import CRF

logging.basicConfig(format = '%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt = '%m/%d/%Y %H:%M:%S',
                    level = logging.INFO)
logger = logging.getLogger(__name__)


class MyBertForTokenClassification(BertPreTrainedModel):
    """BERT model for token-level classification.
    This module is composed of the BERT model with a linear layer on top of
    the full hidden state of the last layer.
    Params:
        `config`: a BertConfig class instance with the configuration to build a new model.
        `num_labels`: the number of classes for the classifier. Default = 2.
    Inputs:
        `input_ids`: a torch.LongTensor of shape [batch_size, sequence_length]
            with the word token indices in the vocabulary(see the tokens preprocessing logic in the scripts
            `extract_features.py`, `run_classifier.py` and `run_squad.py`)
        `token_type_ids`: an optional torch.LongTensor of shape [batch_size, sequence_length] with the token
            types indices selected in [0, 1]. Type 0 corresponds to a `sentence A` and type 1 corresponds to
            a `sentence B` token (see BERT paper for more details).
        `attention_mask`: an optional torch.LongTensor of shape [batch_size, sequence_length] with indices
            selected in [0, 1]. It's a mask to be used if the input sequence length is smaller than the max
            input sequence length in the current batch. It's the mask that we typically use for attention when
            a batch has varying length sentences.
        `labels`: labels for the classification output: torch.LongTensor of shape [batch_size, sequence_length]
            with indices selected in [0, ..., num_labels].
    Outputs:
        if `labels` is not `None`:
            Outputs the CrossEntropy classification loss of the output with the labels.
        if `labels` is `None`:
            Outputs the classification logits of shape [batch_size, sequence_length, num_labels].
    Example usage:
    ```python
    # Already been converted into WordPiece token ids
    input_ids = torch.LongTensor([[31, 51, 99], [15, 5, 0]])
    input_mask = torch.LongTensor([[1, 1, 1], [1, 1, 0]])
    token_type_ids = torch.LongTensor([[0, 0, 1], [0, 1, 0]])
    config = BertConfig(vocab_size_or_config_json_file=32000, hidden_size=768,
        num_hidden_layers=12, num_attention_heads=12, intermediate_size=3072)
    num_labels = 2
    model = BertForTokenClassification(config, num_labels)
    logits = model(input_ids, token_type_ids, input_mask)
    ```
    """
    def __init__(self, config, num_labels):
        super(MyBertForTokenClassification, self).__init__(config)
        self.num_labels = num_labels
        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.classifier = nn.Linear(config.hidden_size, num_labels)
        self.apply(self.init_bert_weights)

    def forward(self, input_ids, token_type_ids, attention_mask, labels=None, label_mask=None):
        sequence_output, _ = self.bert(input_ids, token_type_ids, attention_mask, output_all_encoded_layers=False)
        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)

        if labels is not None:
            loss_fct = CrossEntropyLoss()
            # Only keep active parts of the loss
            active_loss = label_mask.view(-1) == 1
            active_logits = logits.view(-1, self.num_labels)[active_loss]
            active_labels = labels.view(-1)[active_loss]
            loss = loss_fct(active_logits, active_labels)
            return loss
        else:
            return logits


class MyBertPlusCRFForTokenClassification(BertPreTrainedModel):
    def __init__(self, config, num_labels, device):
        super(MyBertPlusCRFForTokenClassification, self).__init__(config)
        self.num_labels = num_labels
        self.device = device
        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.classifier = nn.Linear(config.hidden_size, num_labels + 3)  # +3 for bos, eos, pad
        self.crf = CRF(num_labels, device=device).to(device)
        self.apply(self.init_bert_weights)

    def forward(self, input_ids, token_type_ids, attention_mask, labels=None, label_mask=None):
        sequence_output, _ = self.bert(input_ids, token_type_ids, attention_mask, output_all_encoded_layers=False)
        sequence_output = self.classifier(self.dropout(sequence_output))

        if labels is not None:
            orig_seq_len = sequence_output.size(1)
            seq_logits_list, seq_labels_list, seq_mask_list = [], [], []
            for seq_logits, seq_labels, seq_mask in zip(sequence_output, labels, label_mask):
                seq_logits = seq_logits[seq_mask != 0].unsqueeze(0)  # `!= 0` seems to be important here
                seq_logits = torch.cat(
                    [seq_logits, seq_logits.new_zeros((1, orig_seq_len - seq_logits.size(1), seq_logits.size(2)))], 1)

                seq_labels = seq_labels[seq_mask != 0].unsqueeze(0)
                seq_mask = torch.cat([seq_labels.new_ones((1, seq_labels.size(1))),
                                      seq_labels.new_zeros((1, orig_seq_len - seq_labels.size(1)))], 1)
                seq_labels = torch.cat([seq_labels, seq_labels.new_zeros((1, orig_seq_len - seq_labels.size(1)))], 1)

                seq_logits_list.append(seq_logits)
                seq_labels_list.append(seq_labels)
                seq_mask_list.append(seq_mask)
            cat_seq_logits = torch.cat(seq_logits_list, 0)
            cat_seq_labels = torch.cat(seq_labels_list, 0)
            cat_seq_mask = torch.cat(seq_mask_list, 0)

            return self.crf(cat_seq_logits, cat_seq_labels, mask=cat_seq_mask)
        else:
            return_logits_list = []
            for seq_logits, seq_mask in zip(sequence_output, label_mask):  # inefficient, need to optimize later
                seq_logits = seq_logits[seq_mask != 0].unsqueeze(0)
                _, path = self.crf.decode(seq_logits)  # use Viterbi
                return_logits = torch.ones((sequence_output.size(1), self.num_labels)).to(self.device)
                i_path = 0
                for j_seq_mask in range(len(seq_mask)):
                    if seq_mask[j_seq_mask] != 0:
                        return_logits[j_seq_mask][path[0][i_path]] = 10000
                        i_path += 1
                return_logits_list.append(return_logits.unsqueeze(0))
            return torch.cat(return_logits_list, 0)

class InputExample(object):
    """A single training/test example for simple sequence classification."""

    def __init__(self, guid, text, label=None):
        """Constructs a InputExample.
        Args:
            guid: Unique id for the example.
            text_a: string. The untokenized text of the first sequence. For single
            sequence tasks, only this sequence must be specified.
            text_b: (Optional) string. The untokenized text of the second sequence.
            Only must be specified for sequence pair tasks.
            label: (Optional) string. The label of the example. This should be
            specified for train and dev examples, but not for test examples.
        """
        self.guid = guid
        self.text = text # list of tokens
        self.label = label # list of labels


class InputFeatures(object):
    """A single set of features of data."""

    def __init__(self, input_ids, input_mask, segment_ids, label_ids, label_mask):
        self.input_ids = input_ids
        self.input_mask = input_mask
        self.segment_ids = segment_ids
        self.label_ids = label_ids
        self.label_mask = label_mask # necessary since the label mismatch for wordpieces


class DataProcessor(object):
    """Processor for the MRPC data set (GLUE version)."""

    def get_PTB_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_pkl(os.path.join(data_dir, "PTB_train.pkl")), "PTB_train")

    def get_PTB_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_pkl(os.path.join(data_dir, "PTB_dev.pkl")), "PTB_dev")

    def get_PTB_all_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_pkl(os.path.join(data_dir, "PTB_all.pkl")), "PTB_all")

    def get_PPCEME_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_pkl(os.path.join(data_dir, "PPCEME_train.pkl")), "PPCEME_train")

    def get_PPCEME_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_pkl(os.path.join(data_dir, "PPCEME_test.pkl")), "PPCEME_test")

    def get_PPCEME_all_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_pkl(os.path.join(data_dir, "PPCEME_all.pkl")), "PPCEME_all")

    def get_sep_PPCEME_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_pkl(os.path.join(data_dir, "sep_PPCEME_train.pkl")), "PPCEME_train")

    def get_sep_PPCEME_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_pkl(os.path.join(data_dir, "sep_PPCEME_test.pkl")), "PPCEME_test")

    def get_labels(self, data_dir):
        """See base class."""
        return self._read_pkl(os.path.join(data_dir, "PTB_taglist.pkl"))

    def get_coarse_map(self, data_dir):
        """See base class."""
        return self._read_pkl(os.path.join(data_dir, "coarse_map.pkl"))

    def _create_examples(self, data, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, elem) in enumerate(data):
            guid = "%s-%s" % (set_type, i)
            text = elem[0]
            label = elem[1]
            examples.append(
                InputExample(guid=guid, text=text, label=label))
        return examples

    def _read_pkl(self, input_file):
        """Reads a tab separated value file."""
        data = pickle.load(open(input_file, 'rb'))
        return data


def convert_examples_to_features(examples, label_list, max_seq_length, tokenizer):
    """Loads a data file into a list of `InputBatch`s."""

    label_map = {label : i for i, label in enumerate(label_list)}
    features = []
    for (ex_index, example) in enumerate(examples):
        tokens = example.text

#         # Account for [CLS] and [SEP] with "- 2"
#         if len(tokens) > max_seq_length - 2:
#             tokens = tokens[:(max_seq_length - 2)]

        bert_tokens = []
        orig_to_tok_map = []

        bert_tokens.append("[CLS]")
        for token in tokens:
            new_tokens = tokenizer.tokenize(token)
            if len(bert_tokens) + len(new_tokens) > max_seq_length - 1:
                break
            else:
                orig_to_tok_map.append(len(bert_tokens))
                bert_tokens.extend(new_tokens)
        bert_tokens.append("[SEP]")

        # The convention in BERT is:
        # (a) For sequence pairs:
        #  tokens:   [CLS] is this jack ##son ##ville ? [SEP] no it is not . [SEP]
        #  type_ids: 0   0  0    0    0     0       0 0    1  1  1  1   1 1
        # (b) For single sequences:
        #  tokens:   [CLS] the dog is hairy . [SEP]
        #  type_ids: 0   0   0   0  0     0 0
        #
        # Where "type_ids" are used to indicate whether this is the first
        # sequence or the second sequence. The embedding vectors for `type=0` and
        # `type=1` were learned during pre-training and are added to the wordpiece
        # embedding vector (and position vector). This is not *strictly* necessary
        # since the [SEP] token unambigiously separates the sequences, but it makes
        # it easier for the model to learn the concept of sequences.
        #
        # For classification tasks, the first vector (corresponding to [CLS]) is
        # used as as the "sentence vector". Note that this only makes sense because
        # the entire model is fine-tuned.

        input_ids = tokenizer.convert_tokens_to_ids(bert_tokens)
        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        input_mask = [1] * len(input_ids)

        # Zero-pad up to the sequence length.
        padding = [0] * (max_seq_length - len(input_ids))
        input_ids += padding
        input_mask += padding

        assert len(input_ids) == max_seq_length
        assert len(input_mask) == max_seq_length

        segment_ids = [0] * max_seq_length # no use for our problem

        labels = example.label
        label_ids = [0] * max_seq_length
        label_mask = [0] * max_seq_length

        for label, target_index in zip(labels, orig_to_tok_map):
            label_ids[target_index] = label_map[label]
            label_mask[target_index] = 1

        assert len(segment_ids) == max_seq_length
        assert len(label_ids) == max_seq_length
        assert len(label_mask) == max_seq_length

        features.append(
                InputFeatures(input_ids=input_ids,
                              input_mask=input_mask,
                              segment_ids=segment_ids,
                              label_ids=label_ids,
                              label_mask=label_mask))
    return features

def accuracy(out, label_ids, label_mask, coarse_map=None):
    # axis-0: seqs in batch; axis-1: toks in seq; axis-2: potential labels of tok
    outputs = np.argmax(out, axis=2)
    if coarse_map:
        matched = np.zeros((outputs.shape[0], outputs.shape[1]), dtype=bool)
        for i in range(outputs.shape[0]):
            for j in range(outputs.shape[1]):
                if coarse_map[label_ids[i][j]] == -1: # if ground truth label should be ignored according to the coarse tagset
                    label_mask[i][j] = 0
                elif coarse_map[outputs[i][j]] == coarse_map[label_ids[i][j]]:
                    matched[i][j] = True
    else:
        matched = outputs == label_ids
    num_correct = np.sum(matched * label_mask)
    num_total = np.sum(label_mask)
    return num_correct, num_total

def main():
    parser = argparse.ArgumentParser()

    ## Required parameters
    parser.add_argument("--data_dir",
                        default=None,
                        type=str,
                        required=True,
                        help="The input data dir. Should contain the .tsv files (or other data files) for the task.")
    parser.add_argument("--bert_model", default=None, type=str, required=True,
                        help="Bert pre-trained model selected in the list: bert-base-uncased, "
                        "bert-large-uncased, bert-base-cased, bert-large-cased, bert-base-multilingual-uncased, "
                        "bert-base-multilingual-cased, bert-base-chinese.")
    parser.add_argument("--output_dir",
                        default=None,
                        type=str,
                        required=True,
                        help="The output directory where the model predictions and checkpoints will be written.")

    ## Other parameters
    parser.add_argument("--cache_dir",
                        default="",
                        type=str,
                        help="Where do you want to store the pre-trained models downloaded from s3")
    parser.add_argument("--trained_model_dir",
                        default="",
                        type=str,
                        help="Where is the fine-tuned (with the cloze-style LM objective) BERT model?")
    parser.add_argument("--max_seq_length",
                        default=128,
                        type=int,
                        help="The maximum total input sequence length after WordPiece tokenization. \n"
                             "Sequences longer than this will be truncated, and sequences shorter \n"
                             "than this will be padded.")
    parser.add_argument("--do_train",
                        action='store_true',
                        help="Whether to run training.")
    parser.add_argument("--do_eval",
                        action='store_true',
                        help="Whether to run eval on the dev set.")
    parser.add_argument("--do_test",
                        action='store_true',
                        help="Whether to run eval on the test set.")
    parser.add_argument("--do_lower_case",
                        action='store_true',
                        help="Set this flag if you are using an uncased model.")
    parser.add_argument("--train_batch_size",
                        default=32,
                        type=int,
                        help="Total batch size for training.")
    parser.add_argument("--eval_batch_size",
                        default=8,
                        type=int,
                        help="Total batch size for eval.")
    parser.add_argument("--learning_rate",
                        default=5e-5,
                        type=float,
                        help="The initial learning rate for Adam.")
    parser.add_argument("--num_train_epochs",
                        default=3.0,
                        type=float,
                        help="Total number of training epochs to perform.")
    parser.add_argument("--warmup_proportion",
                        default=0.1,
                        type=float,
                        help="Proportion of training to perform linear learning rate warmup for. "
                             "E.g., 0.1 = 10%% of training.")
    parser.add_argument("--no_cuda",
                        action='store_true',
                        help="Whether not to use CUDA when available")
    parser.add_argument("--local_rank",
                        type=int,
                        default=-1,
                        help="local_rank for distributed training on gpus")
    parser.add_argument('--seed',
                        type=int,
                        default=42,
                        help="random seed for initialization")
    parser.add_argument('--gradient_accumulation_steps',
                        type=int,
                        default=1,
                        help="Number of updates steps to accumulate before performing a backward/update pass.")
    parser.add_argument('--fp16',
                        action='store_true',
                        help="Whether to use 16-bit float precision instead of 32-bit")
    parser.add_argument('--loss_scale',
                        type=float, default=0,
                        help="Loss scaling to improve fp16 numeric stability. Only used when fp16 set to True.\n"
                             "0 (default value): dynamic loss scaling.\n"
                             "Positive power of 2: static loss scaling value.\n")
    parser.add_argument('--freeze_bert',
                        action='store_true',
                        help="Whether to freeze BERT")
    parser.add_argument('--save_all_epochs',
                        action='store_true',
                        help="Whether to save model in each epoch")
    parser.add_argument('--coarse_tagset',
                        action='store_true',
                        help="Whether to save model in each epoch")
    parser.add_argument('--supervised_training',
                        action='store_true',
                        help="Only use this for supervised top-line model")
    parser.add_argument('--partially_freeze_bert',
                        type=int,
                        default=-1,
                        help="number of bottom layers frozen")
    parser.add_argument('--use_crf',
                        action='store_true',
                        help="whether to use CRF")
    args = parser.parse_args()

    if args.local_rank == -1 or args.no_cuda:
        device = torch.device("cuda" if torch.cuda.is_available() and not args.no_cuda else "cpu")
        n_gpu = torch.cuda.device_count()
    else:
        torch.cuda.set_device(args.local_rank)
        device = torch.device("cuda", args.local_rank)
        n_gpu = 1
        # Initializes the distributed backend which will take care of sychronizing nodes/GPUs
        torch.distributed.init_process_group(backend='nccl')
    logger.info("device: {} n_gpu: {}, distributed training: {}, 16-bits training: {}".format(
        device, n_gpu, bool(args.local_rank != -1), args.fp16))

    if args.gradient_accumulation_steps < 1:
        raise ValueError("Invalid gradient_accumulation_steps parameter: {}, should be >= 1".format(
                            args.gradient_accumulation_steps))

    args.train_batch_size = args.train_batch_size // args.gradient_accumulation_steps

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if n_gpu > 0:
        torch.cuda.manual_seed_all(args.seed)

    if not args.do_train and not args.do_eval and not args.do_test:
        raise ValueError("At least one of `do_train` or `do_eval` or `do_test` must be True.")

    if os.path.exists(args.output_dir) and os.listdir(args.output_dir) and args.do_train:
        #raise ValueError("Output directory ({}) already exists and is not empty.".format(args.output_dir))
        print("WARNING: Output directory already exists and is not empty.")
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    processor = DataProcessor()
    label_list = processor.get_labels(args.data_dir)
    num_labels = len(label_list)
    coarse_map = processor.get_coarse_map(args.data_dir)

    tokenizer = BertTokenizer.from_pretrained(args.bert_model, do_lower_case=args.do_lower_case)

    train_examples = None
    num_train_optimization_steps = None
    if args.do_train:
        if args.supervised_training:
            train_examples = processor.get_sep_PPCEME_train_examples(args.data_dir)
        else:
            train_examples = processor.get_PTB_train_examples(args.data_dir)
        num_train_optimization_steps = int(
            len(train_examples) / args.train_batch_size / args.gradient_accumulation_steps) * args.num_train_epochs
        if args.local_rank != -1:
            num_train_optimization_steps = num_train_optimization_steps // torch.distributed.get_world_size()

    # Prepare model
    cache_dir = args.cache_dir if args.cache_dir else os.path.join(PYTORCH_PRETRAINED_BERT_CACHE, 'distributed_{}'.format(args.local_rank))
    if args.trained_model_dir: # load in fine-tuned (with cloze-style LM objective) model
        if os.path.exists(os.path.join(args.output_dir, WEIGHTS_NAME)):
            previous_state_dict = torch.load(os.path.join(args.output_dir, WEIGHTS_NAME))
        else:
            from collections import OrderedDict
            previous_state_dict = OrderedDict()
        distant_state_dict = torch.load(os.path.join(args.trained_model_dir, WEIGHTS_NAME))
        previous_state_dict.update(distant_state_dict) # note that the final layers of previous model and distant model must have different attribute names!
        if args.use_crf:
            model = MyBertPlusCRFForTokenClassification.from_pretrained(args.trained_model_dir, state_dict=previous_state_dict, num_labels=num_labels, device=device)
        else:
            model = MyBertForTokenClassification.from_pretrained(args.trained_model_dir, state_dict=previous_state_dict, num_labels=num_labels)
    else:
        if args.use_crf:
            model = MyBertPlusCRFForTokenClassification.from_pretrained(args.bert_model, cache_dir=cache_dir, num_labels=num_labels, device=device)
        else:
            model = MyBertForTokenClassification.from_pretrained(args.bert_model, cache_dir=cache_dir, num_labels=num_labels)
    if args.fp16:
        model.half()
    model.to(device)
    if args.local_rank != -1:
        try:
            from apex.parallel import DistributedDataParallel as DDP
        except ImportError:
            raise ImportError("Please install apex from https://www.github.com/nvidia/apex to use distributed and fp16 training.")
        model = DDP(model)
    elif n_gpu > 1:
        model = torch.nn.DataParallel(model)

    # Prepare optimizer
    param_optimizer = list(model.named_parameters())
    if args.freeze_bert: # freeze BERT if needed
        frozen = ['bert']
    elif args.partially_freeze_bert != -1:
        if args.partially_freeze_bert not in [3,6,9]:
            raise ValueError("can only freeze 3, 6, or 9 layers")
        elif args.partially_freeze_bert == 3:
            frozen = ['bert.embeddings.',
                      'bert.encoder.layer.0.',
                      'bert.encoder.layer.1.',
                      'bert.encoder.layer.2.',
                     ]
        elif args.partially_freeze_bert == 6:
            frozen = ['bert.embeddings.',
                      'bert.encoder.layer.0.',
                      'bert.encoder.layer.1.',
                      'bert.encoder.layer.2.',
                      'bert.encoder.layer.3.',
                      'bert.encoder.layer.4.',
                      'bert.encoder.layer.5.',
                     ]
        elif args.partially_freeze_bert == 9:
            frozen = ['bert.embeddings.',
                      'bert.encoder.layer.0.',
                      'bert.encoder.layer.1.',
                      'bert.encoder.layer.2.',
                      'bert.encoder.layer.3.',
                      'bert.encoder.layer.4.',
                      'bert.encoder.layer.5.',
                      'bert.encoder.layer.6.',
                      'bert.encoder.layer.7.',
                      'bert.encoder.layer.8.',
                     ]
    else:
        frozen = []
    no_decay = ['bias', 'LayerNorm.bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {'params': [p for n, p in param_optimizer if (not any(fr in n for fr in frozen)) and (not any(nd in n for nd in no_decay))], 'weight_decay': 0.01},
        {'params': [p for n, p in param_optimizer if (not any(fr in n for fr in frozen)) and (any(nd in n for nd in no_decay))], 'weight_decay': 0.0}
        ]
    param_size = 0
    for d in optimizer_grouped_parameters:
        for p in d['params']:
            tmp_p = p.clone().detach()
            param_size += torch.numel(tmp_p)
    logger.info("  Parameter size = %d", param_size)
    
    if args.fp16:
        try:
            from apex.optimizers import FP16_Optimizer
            from apex.optimizers import FusedAdam
        except ImportError:
            raise ImportError("Please install apex from https://www.github.com/nvidia/apex to use distributed and fp16 training.")
        optimizer = FusedAdam(optimizer_grouped_parameters,
                              lr=args.learning_rate,
                              bias_correction=False,
                              max_grad_norm=1.0)
        if args.loss_scale == 0:
            optimizer = FP16_Optimizer(optimizer, dynamic_loss_scale=True)
        else:
            optimizer = FP16_Optimizer(optimizer, static_loss_scale=args.loss_scale)
    else:
        optimizer = BertAdam(optimizer_grouped_parameters,
                             lr=args.learning_rate,
                             warmup=args.warmup_proportion,
                             t_total=num_train_optimization_steps)

    global_step = 0
    nb_tr_steps = 0
    tr_loss = 0
    if args.do_train:
        train_features = convert_examples_to_features(
            train_examples, label_list, args.max_seq_length, tokenizer)
        logger.info("***** Running training *****")
        logger.info("  Num examples = %d", len(train_examples))
        logger.info("  Batch size = %d", args.train_batch_size)
        logger.info("  Num steps = %d", num_train_optimization_steps)
        all_input_ids = torch.tensor([f.input_ids for f in train_features], dtype=torch.long)
        all_input_mask = torch.tensor([f.input_mask for f in train_features], dtype=torch.long)
        all_segment_ids = torch.tensor([f.segment_ids for f in train_features], dtype=torch.long)
        all_label_ids = torch.tensor([f.label_ids for f in train_features], dtype=torch.long)
        all_label_mask = torch.tensor([f.label_mask for f in train_features], dtype=torch.long)
        train_data = TensorDataset(all_input_ids, all_input_mask, all_segment_ids, all_label_ids, all_label_mask)
        if args.local_rank == -1:
            train_sampler = RandomSampler(train_data)
        else:
            train_sampler = DistributedSampler(train_data)
        train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=args.train_batch_size)

        model.train()
        epoch_index = 0
        for _ in trange(int(args.num_train_epochs), desc="Epoch"):
            tr_loss = 0
            nb_tr_examples, nb_tr_steps = 0, 0
            for step, batch in enumerate(tqdm(train_dataloader, desc="Iteration")):
                batch = tuple(t.to(device) for t in batch)
                input_ids, input_mask, segment_ids, label_ids, label_mask = batch
                loss = model(input_ids, segment_ids, input_mask, label_ids, label_mask)
                if n_gpu > 1:
                    loss = loss.mean() # mean() to average on multi-gpu.
                if args.gradient_accumulation_steps > 1:
                    loss = loss / args.gradient_accumulation_steps

                if args.fp16:
                    optimizer.backward(loss)
                else:
                    loss.backward()

                tr_loss += loss.item()
                nb_tr_examples += input_ids.size(0)
                nb_tr_steps += 1
                if (step + 1) % args.gradient_accumulation_steps == 0:
                    if args.fp16:
                        # modify learning rate with special warm up BERT uses
                        # if args.fp16 is False, BertAdam is used that handles this automatically
                        lr_this_step = args.learning_rate * warmup_linear(global_step/num_train_optimization_steps, args.warmup_proportion)
                        for param_group in optimizer.param_groups:
                            param_group['lr'] = lr_this_step
                    optimizer.step()
                    optimizer.zero_grad()
                    global_step += 1
            if (args.local_rank == -1 or torch.distributed.get_rank() == 0) and args.save_all_epochs:
                # Save a trained model and the associated configuration
                model_to_save = model.module if hasattr(model, 'module') else model  # Only save the model it-self
                output_model_file = os.path.join(args.output_dir, WEIGHTS_NAME + ".epoch" + str(epoch_index))
                torch.save(model_to_save.state_dict(), output_model_file)
            epoch_index += 1

    if args.do_train and (args.local_rank == -1 or torch.distributed.get_rank() == 0):
        # Save a trained model and the associated configuration
        model_to_save = model.module if hasattr(model, 'module') else model  # Only save the model it-self
        output_model_file = os.path.join(args.output_dir, WEIGHTS_NAME)
        torch.save(model_to_save.state_dict(), output_model_file)
        output_config_file = os.path.join(args.output_dir, CONFIG_NAME)
        with open(output_config_file, 'w') as f:
            f.write(model_to_save.config.to_json_string())

    if args.do_eval and (args.local_rank == -1 or torch.distributed.get_rank() == 0):
        eval_examples = processor.get_PTB_dev_examples(args.data_dir)
        eval_features = convert_examples_to_features(
            eval_examples, label_list, args.max_seq_length, tokenizer)
        logger.info("***** Running evaluation *****")
        logger.info("  Num examples = %d", len(eval_examples))
        logger.info("  Batch size = %d", args.eval_batch_size)
        all_input_ids = torch.tensor([f.input_ids for f in eval_features], dtype=torch.long)
        all_input_mask = torch.tensor([f.input_mask for f in eval_features], dtype=torch.long)
        all_segment_ids = torch.tensor([f.segment_ids for f in eval_features], dtype=torch.long)
        all_label_ids = torch.tensor([f.label_ids for f in eval_features], dtype=torch.long)
        all_label_mask = torch.tensor([f.label_mask for f in eval_features], dtype=torch.long)
        eval_data = TensorDataset(all_input_ids, all_input_mask, all_segment_ids, all_label_ids, all_label_mask)
        # Run prediction for full data
        eval_sampler = SequentialSampler(eval_data)
        eval_dataloader = DataLoader(eval_data, sampler=eval_sampler, batch_size=args.eval_batch_size)

        model.eval()
        eval_loss, eval_accuracy = 0, 0
        nb_eval_steps, nb_eval_examples = 0, 0

        for input_ids, input_mask, segment_ids, label_ids, label_mask in tqdm(eval_dataloader, desc="Evaluating"):
            input_ids = input_ids.to(device)
            input_mask = input_mask.to(device)
            segment_ids = segment_ids.to(device)
            label_ids = label_ids.to(device)
            label_mask = label_mask.to(device)

            with torch.no_grad():
                tmp_eval_loss = model(input_ids, segment_ids, input_mask, label_ids, label_mask)
                logits = model(input_ids, segment_ids, input_mask)

            logits = logits.detach().cpu().numpy()
            label_ids = label_ids.to('cpu').numpy()
            label_mask = label_mask.to('cpu').numpy()
            if args.coarse_tagset:
                tmp_eval_correct, tmp_eval_total = accuracy(logits, label_ids, label_mask, coarse_map=coarse_map)
            else:
                tmp_eval_correct, tmp_eval_total = accuracy(logits, label_ids, label_mask)

            eval_loss += tmp_eval_loss.mean().item()
            eval_accuracy += tmp_eval_correct

            nb_eval_examples += tmp_eval_total
            nb_eval_steps += 1

        eval_loss = eval_loss / nb_eval_steps
        eval_accuracy = eval_accuracy / nb_eval_examples # micro average
        result = {'eval_loss': eval_loss,
                  'eval_accuracy': eval_accuracy}

        output_eval_file = os.path.join(args.output_dir, "eval_results.txt")
        with open(output_eval_file, "w") as writer:
            logger.info("***** Eval results *****")
            for key in sorted(result.keys()):
                logger.info("  %s = %s", key, str(result[key]))
                writer.write("%s = %s\n" % (key, str(result[key])))

    if args.do_test and (args.local_rank == -1 or torch.distributed.get_rank() == 0):
        test_examples = processor.get_sep_PPCEME_test_examples(args.data_dir)
        test_features = convert_examples_to_features(
            test_examples, label_list, args.max_seq_length, tokenizer)
        logger.info("***** Running final test *****")
        logger.info("  Num examples = %d", len(test_examples))
        logger.info("  Batch size = %d", args.eval_batch_size)
        all_input_ids = torch.tensor([f.input_ids for f in test_features], dtype=torch.long)
        all_input_mask = torch.tensor([f.input_mask for f in test_features], dtype=torch.long)
        all_segment_ids = torch.tensor([f.segment_ids for f in test_features], dtype=torch.long)
        all_label_ids = torch.tensor([f.label_ids for f in test_features], dtype=torch.long)
        all_label_mask = torch.tensor([f.label_mask for f in test_features], dtype=torch.long)
        test_data = TensorDataset(all_input_ids, all_input_mask, all_segment_ids, all_label_ids, all_label_mask)
        # Run prediction for full data
        test_sampler = SequentialSampler(test_data)
        test_dataloader = DataLoader(test_data, sampler=test_sampler, batch_size=args.eval_batch_size)

        model.eval()
        test_loss, test_accuracy = 0, 0
        nb_test_steps, nb_test_examples = 0, 0

        for input_ids, input_mask, segment_ids, label_ids, label_mask in tqdm(test_dataloader, desc="Testing"):
            input_ids = input_ids.to(device)
            input_mask = input_mask.to(device)
            segment_ids = segment_ids.to(device)
            label_ids = label_ids.to(device)
            label_mask = label_mask.to(device)

            with torch.no_grad():
                tmp_test_loss = model(input_ids, segment_ids, input_mask, label_ids, label_mask)
                logits = model(input_ids, segment_ids, input_mask, label_mask=label_mask)

            logits = logits.detach().cpu().numpy()
            label_ids = label_ids.to('cpu').numpy()
            label_mask = label_mask.to('cpu').numpy()
            if args.coarse_tagset:
                tmp_test_correct, tmp_test_total = accuracy(logits, label_ids, label_mask, coarse_map=coarse_map)
            else:
                tmp_test_correct, tmp_test_total = accuracy(logits, label_ids, label_mask)

            test_loss += tmp_test_loss.mean().item()
            test_accuracy += tmp_test_correct

            nb_test_examples += tmp_test_total
            nb_test_steps += 1

        test_loss = test_loss / nb_test_steps
        test_accuracy = test_accuracy / nb_test_examples # micro average
        result = {'test_loss': test_loss,
                  'test_accuracy': test_accuracy}

        output_test_file = os.path.join(args.output_dir, "test_results.txt")
        with open(output_test_file, "w") as writer:
            logger.info("***** Test results *****")
            for key in sorted(result.keys()):
                logger.info("  %s = %s", key, str(result[key]))
                writer.write("%s = %s\n" % (key, str(result[key])))

if __name__ == "__main__":
    main()
