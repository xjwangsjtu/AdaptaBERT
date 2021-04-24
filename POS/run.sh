# finetune a BERT model with PTB data (no CRF)
python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=2019

# test the model above on PPCEME data
python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=2019
