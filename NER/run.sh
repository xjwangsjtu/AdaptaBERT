# train on CoNLL
python -W ignore task-tuning.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_0/" --max_seq_length=128 --do_train --train_batch_size=32 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=2019

# test on WNUT
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_0/" --trained_model_dir="_test_model_0/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=2019
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval_0_ood/" --trained_model_dir="_test_model_0/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=2019 --OOD=1

# train on CoNLL
python -W ignore task-tuning.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_1/" --max_seq_length=128 --do_train --train_batch_size=32 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=100

# test on WNUT
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model_1/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=100
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model_1/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=100 --OOD=1


# train on CoNLL
python -W ignore task-tuning.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_2/" --max_seq_length=128 --do_train --train_batch_size=32 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=200

# test on WNUT
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model_2/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=200
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model_2/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=200 --OOD=1


# train on CoNLL
python -W ignore task-tuning.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_3/" --max_seq_length=128 --do_train --train_batch_size=32 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=300

# test on WNUT
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model_3/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=300
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model_3/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=300 --OOD=1


# train on CoNLL
python -W ignore task-tuning.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_4/" --max_seq_length=128 --do_train --train_batch_size=32 --learning_rate=5e-5 --num_train_epochs=3 --warmup_proportion=0.1 --seed=400

# test on WNUT
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model_4/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=400
python -W ignore test.py --data_dir="data/" --bert_model="bert-base-cased" --output_dir="_test_model_eval/" --trained_model_dir="_test_model_4/" --max_seq_length=128 --do_test --eval_batch_size=1 --seed=400 --OOD=1
