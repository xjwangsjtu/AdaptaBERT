# train on CoNLL
python -W ignore task-tuning.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model/" --max_seq_length=128 --do_train --train_batch_size=32 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=2019

# test on WNUT
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=2019
