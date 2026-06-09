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
docker compose build
docker compose up