# finetune a BERT model with PTB data (no CRF)
python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_1/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=100

# test the model above on PPCEME data
python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_1/" --trained_model_dir="_test_model_1/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=100
python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_1/" --trained_model_dir="_test_model_1/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=100 --OOD=1

# finetune a BERT model with PTB data (no CRF)
python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_2/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=200

# test the model above on PPCEME data
python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_2/" --trained_model_dir="_test_model_2/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=200
python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_2/" --trained_model_dir="_test_model_2/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=200 --OOD=1

# finetune a BERT model with PTB data (no CRF)
python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_3/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=300

# test the model above on PPCEME data
python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_3/" --trained_model_dir="_test_model_3/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=300
python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_3/" --trained_model_dir="_test_model_3/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=300 --OOD=1

# finetune a BERT model with PTB data (no CRF)
python -W ignore task-tuning.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_4/" --max_seq_length=256 --do_train --train_batch_size=16 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=400

# test the model above on PPCEME data
python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_4/" --trained_model_dir="_test_model_4/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=400
python -W ignore test.py --data_dir="data/processed/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_4/" --trained_model_dir="_test_model_4/" --max_seq_length=256 --do_test --eval_batch_size=1 --seed=400 --OOD=1
