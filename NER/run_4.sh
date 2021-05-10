CUDA_VISIBLE_DEVICES="3" python -W ignore task-tuning.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="nocrf_freeze_12/" --max_seq_length=128 --do_train --train_batch_size=32 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=2019 --freeze_bert

CUDA_VISIBLE_DEVICES="3" python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="nocrf_freeze_12_id_log/" --trained_model_dir="nocrf_freeze_12/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=2019

CUDA_VISIBLE_DEVICES="3" python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="nocrf_freeze_12_ood_log/" --trained_model_dir="nocrf_freeze_12/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=2019 --OOD=1
