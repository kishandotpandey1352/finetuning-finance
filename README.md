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