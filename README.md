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