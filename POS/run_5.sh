CUDA_VISIBLE_DEVICES="1" python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="crf_freeze_12/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=5 --warmup_proportion=0.1 --seed=2019 --freeze_bert --use_crf

CUDA_VISIBLE_DEVICES="1" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="crf_freeze_12_id_log/" --trained_model_dir="crf_freeze_12/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019 --use_crf

CUDA_VISIBLE_DEVICES="1" python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="crf_freeze_12_ood_log/" --trained_model_dir="crf_freeze_12/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019 --OOD=1 --use_crf
