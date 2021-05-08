# run train with --partial_freeze_bert=3 6 or 9
python -W ignore task-tuning.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model/" --max_seq_length=128 --do_train --train_batch_size=32 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=2019 --partially_freeze_bert=9
