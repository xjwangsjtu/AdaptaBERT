CUDA_VISIBLE_DEVICES="0" python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="crf_freeze_6/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=5 --warmup_proportion=0.1 --seed=2019 --partially_freeze_bert=6 --use_crf



CUDA_VISIBLE_DEVICES="1" python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="crf_freeze_12/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=5 --warmup_proportion=0.1 --seed=2019 --freeze_bert --use_crf



CUDA_VISIBLE_DEVICES="2" python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="nocrf_freeze_6/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=2019 --partially_freeze_bert=6



CUDA_VISIBLE_DEVICES="3" python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="nocrf_freeze_12/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=2019 --freeze_bert


#### After the above finish ####


CUDA_VISIBLE_DEVICES="0" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="crf_freeze_6_id_log/" --trained_model_dir="crf_freeze_6/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019 --use_crf

CUDA_VISIBLE_DEVICES="0" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="crf_freeze_6_ood_log/" --trained_model_dir="crf_freeze_6/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019 --OOD=1 --use_crf



CUDA_VISIBLE_DEVICES="1" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="crf_freeze_12_id_log/" --trained_model_dir="crf_freeze_12/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019 --use_crf

CUDA_VISIBLE_DEVICES="1" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="crf_freeze_12_ood_log/" --trained_model_dir="crf_freeze_12/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019 --OOD=1 --use_crf



CUDA_VISIBLE_DEVICES="2" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="nocrf_freeze_6_id_log/" --trained_model_dir="nocrf_freeze_6/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019

CUDA_VISIBLE_DEVICES="2" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="nocrf_freeze_6_ood_log/" --trained_model_dir="nocrf_freeze_6/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019 --OOD=1



CUDA_VISIBLE_DEVICES="3" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="nocrf_freeze_12_id_log/" --trained_model_dir="nocrf_freeze_12/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019

CUDA_VISIBLE_DEVICES="3" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="nocrf_freeze_12_ood_log/" --trained_model_dir="nocrf_freeze_12/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019 --OOD=1
