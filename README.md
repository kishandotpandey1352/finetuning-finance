# Finetuning Finance

Project scaffold for financial model finetuning.

# Finance AI Platform

A production-style project for fine-tuning and serving an LLM on financial data.

## Goal

Build an end-to-end finance AI platform covering:

- dataset curation
- QLoRA fine-tuning
- model evaluation
- vLLM inference
- quantization benchmarking
- FastAPI serving
- Prometheus/Grafana monitoring

## Architecture

See `reports/architecture.md`.

## Day 1 Status

- [x] Repo created
- [x] Project structure created
- [x] Financial PhraseBank download script added
- [x] Docker environment added
- [x] Architecture diagram v1 added

## Planned Stack

- Python
- Hugging Face Datasets
- Transformers
- PEFT
- bitsandbytes
- vLLM
- FastAPI
- Prometheus
- Grafana
- Docker

## commands to do intial setup
winget install Python.Python.3.11
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows PowerShell

pip install datasets pandas pyarrow
pip freeze > requirements.txt

## to run locally
docker compose build --no-cache
docker compose up
docker ps
http://localhost:8000/health
http://localhost:8000/docs

## Day 3
### Run cleaner through Docker:
docker compose run --rm data-cleaner
### Run API:
docker compose up finance-ai-platform --build

#### chunk : sample file created

echo Revenue increased by 18 percent due to stronger demand in cloud services. The company also reported higher operating expenses. > data\cleaned\sample.txt

docker exec -it finance-ai-platform python src/data/chunk.py --input data/cleaned/sample.txt --output data/cleaned/sample_chunks.jsonl

#### see the chunked sample file as output

docker exec -it finance-ai-platform cat data/cleaned/sample_chunks.jsonl

## day 5: Add instruction dataset preparation and architecture document
-- create instructions
docker exec -it finance-ai-platform python src/data/prepare_instruction_dataset.py --chunks data/cleaned/sample_chunks.jsonl --output data/instruction/sample_instruction_dataset.jsonl --task summarization

-- chek result
docker exec -it finance-ai-platform cat data/instruction/sample_instruction_dataset.jsonl

## 90 samples of gold dataset combined:
docker exec -it finance-ai-platform python src/data/combine_gold_dataset.py --input-dir data/instruction/gold --output data/instruction/finance_gold_v1.jsonl --shuffle

-- check combining
docker exec -it finance-ai-platform python src/data/combine_gold_dataset.py --input-dir data/instruction/gold --output data/instruction/finance_gold_v1.jsonl --shuffle

## model setup for training
docker exec -it finance-ai-platform python -c 

"from transformers import AutoTokenizer; 

AutoTokenizer.from_pretrained('Qwen/Qwen2.5-3B-Instruct'); 

print('Qwen2.5-3B tokenizer is available or downloaded successfully')"

-- To check whether the model files are already cached locally inside Docker
 
docker exec -it finance-ai-platform python -c "from huggingface_hub import scan_cache_dir; print(scan_cache_dir())"

-- To specifically try loading the model config without loading full weights:

docker exec -it finance-ai-platform python -c "from transformers import AutoConfig; cfg=AutoConfig.from_pretrained('Qwen/Qwen2.5-3B-Instruct'); print(cfg.model_type); print(cfg.num_hidden_layers)"

### run the training setup file:
docker exec -it finance-ai-platform python src/training/check_training_setup.py

### run the evaluation set up 
docker exec -it finance-ai-platform python src/evaluation/check_eval_setup.py

### run the local training on the Qwen 2.5-3B-instruct model
docker exec -it finance-ai-platform python src/training/train_qlora.py --model-name Qwen/Qwen2.5-3B-Instruct --dataset-path data/instruction/finance_gold_v1.jsonl --output-dir outputs/qlora-finance-v1 --max-steps 50 --max-length 512

### After the first run on 90 datasets, following results obtained:
Model: Qwen/Qwen2.5-3B-Instruct
Dataset: 90 gold examples
QLoRA: working
GPU: RTX 5060 Laptop GPU
Trainable params: 29.9M / 3.1B
Trainable %: 0.96%
Runtime: 121 seconds
Final train loss: ~1.004
Adapter saved: outputs/qlora-finance-v1

### Evaluation of the first run
--evaluation against this fine-tuned adapter:

docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_v1.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --adapter-path outputs/qlora-finance-v1 --output-report reports/evaluation_finetuned_qwen3b.json --limit 10 --max-new-tokens 128

Eg:
Metrics:
rouge1: 0.6265
rouge2: 0.4084
rougeL: 0.5627
rougeLsum: 0.5611
bertscore_precision: 0.9197
bertscore_recall: 0.9305
bertscore_f1: 0.9250
Evaluation report saved to: reports/evaluation_finetuned_qwen3b.json

--evaluate the base model for comparison:

docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_v1.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --output-report reports/evaluation_base_qwen3b.json --limit 10 --max-new-tokens 128

Eg:

Metrics:
rouge1: 0.1807
rouge2: 0.0860
rougeL: 0.1602
rougeLsum: 0.1593
bertscore_precision: 0.7571
bertscore_recall: 0.8317
bertscore_f1: 0.7898
Evaluation report saved to: reports/evaluation_base_qwen3b.json
================================================================================
Evaluation complete
=============================================

\\\Initial QLoRA Experiment Results

Base model: Qwen2.5-3B-Instruct
Fine-tuning method: QLoRA
Dataset: 90 manually curated finance instruction examples
Training steps: 50
Max sequence length: 512
Trainable parameters: 29.9M / 3.1B, approximately 0.96%

Results:
- ROUGE-L improved from 0.1602 to 0.5627
- BERTScore F1 improved from 0.7898 to 0.9250

Interpretation:
The fine-tuned adapter produced outputs that were substantially closer to the target finance summaries, risk labels, and QA answers. Because this was an initial small-data experiment, a held-out test set is required for stronger generalization claims.

## day 8 -  increased dataset size to 300 samples
combined 100 each into a new file:

docker exec -it finance-ai-platform python src/data/combine_gold_dataset.py --input-dir data/instruction/gold --output data/instruction/finance_gold_v2.jsonl --shuffle

-- count numbe rof rows
docker exec -it finance-ai-platform python -c "import json; p='data/instruction/finance_gold_v2.jsonl'; rows=[json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]; print(len(rows))"

-- 80/20 split
docker exec -it finance-ai-platform python src/data/split_dataset.py --input data/instruction/finance_gold_v2.jsonl --train-output data/instruction/finance_gold_train.jsonl --test-output data/instruction/finance_gold_test.jsonl --test-size 0.2 --seed 42

docker exec -it finance-ai-platform python src/data/split_dataset.py --input data/instruction/finance_gold_v1.jsonl --train-output data/instruction/finance_gold_train.jsonl --test-output data/instruction/finance_gold_test.jsonl --test-size 0.2 --seed 42

-- run training on train set only:

docker exec -it finance-ai-platform python src/training/train_qlora.py --model-name Qwen/Qwen2.5-3B-Instruct --dataset-path data/instruction/finance_gold_train.jsonl --output-dir outputs/qlora-finance-run2 --max-steps 150 --max-length 512


-- Evaluate base model on test set

docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_test.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --output-report reports/evaluation_base_qwen3b_run2_test.json --limit 60 --max-new-tokens 128


--Evaluate fine-tuned adapter on test set. This evaluates Qwen + your LoRA adapter:

docker exec -it finance-ai-platform python src/evaluation/evaluate_model.py --dataset-path data/instruction/finance_gold_test.jsonl --model-name Qwen/Qwen2.5-3B-Instruct --adapter-path outputs/qlora-finance-run2 --output-report reports/evaluation_finetuned_qwen3b_run1_test.json --limit 60 --max-new-tokens 128

---- Test run result on base model Qwen2.5-3B-Instruct::

Metrics:
rouge1: 0.1944
rouge2: 0.0658
rougeL: 0.1610
rougeLsum: 0.1612
bertscore_precision: 0.7550
bertscore_recall: 0.8349
bertscore_f1: 0.7926
Evaluation report saved to: reports/evaluation_base_qwen3b_run2_test.json

