import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

import boto3
import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

logger = logging.getLogger("llama3-finance-trainer")


def get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_s3_uri(s3_uri: str):
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Expected S3 URI, got: {s3_uri}")
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    return bucket, key


def download_s3_file(s3_uri: str, local_path: Path) -> None:
    bucket, key = parse_s3_uri(s3_uri)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading %s to %s", s3_uri, local_path)
    s3 = boto3.client("s3")
    s3.download_file(bucket, key, str(local_path))


def upload_directory_to_s3(local_dir: Path, s3_uri: str) -> None:
    bucket, prefix = parse_s3_uri(s3_uri)
    s3 = boto3.client("s3")

    logger.info("Uploading directory %s to %s", local_dir, s3_uri)

    for file_path in local_dir.rglob("*"):
        if file_path.is_file():
            relative_key = file_path.relative_to(local_dir).as_posix()
            s3_key = f"{prefix.rstrip('/')}/{relative_key}"
            logger.info("Uploading %s to s3://%s/%s", file_path, bucket, s3_key)
            s3.upload_file(str(file_path), bucket, s3_key)


def get_secret_value(secret_id: Optional[str]) -> Optional[str]:
    if not secret_id:
        return None

    logger.info("Reading secret from AWS Secrets Manager: %s", secret_id)
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_id)
    return response.get("SecretString")


def format_instruction(example: Dict[str, str]) -> str:
    instruction = example.get("instruction", "").strip()
    user_input = example.get("input", "").strip()
    output = example.get("output", "").strip()

    if user_input:
        prompt = (
            "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
            "You are a careful financial AI assistant. Provide accurate, concise, risk-aware answers.\n"
            "<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
            f"{instruction}\n\n{user_input}\n"
            "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
            f"{output}<|eot_id|>"
        )
    else:
        prompt = (
            "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
            "You are a careful financial AI assistant. Provide accurate, concise, risk-aware answers.\n"
            "<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
            f"{instruction}\n"
            "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
            f"{output}<|eot_id|>"
        )

    return prompt


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    run_id = get_env("RUN_ID", f"run-{int(time.time())}")
    base_model_name = get_env("BASE_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
    train_dataset_s3_uri = get_env("TRAIN_DATASET_S3_URI", required=True)
    eval_dataset_s3_uri = get_env("EVAL_DATASET_S3_URI", required=True)
    output_s3_uri = get_env("OUTPUT_S3_URI", required=True)

    hf_token_secret_id = get_env("HF_TOKEN_SECRET_ID", "")
    hf_token = get_env("HF_TOKEN", "")

    if not hf_token and hf_token_secret_id:
        hf_token = get_secret_value(hf_token_secret_id) or ""

    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token

    max_seq_length = int(get_env("MAX_SEQ_LENGTH", "1024"))
    num_train_epochs = float(get_env("NUM_TRAIN_EPOCHS", "1"))
    per_device_train_batch_size = int(get_env("PER_DEVICE_TRAIN_BATCH_SIZE", "1"))
    gradient_accumulation_steps = int(get_env("GRADIENT_ACCUMULATION_STEPS", "8"))
    learning_rate = float(get_env("LEARNING_RATE", "2e-4"))
    lora_r = int(get_env("LORA_R", "16"))
    lora_alpha = int(get_env("LORA_ALPHA", "32"))
    lora_dropout = float(get_env("LORA_DROPOUT", "0.05"))

    work_dir = Path("/tmp/finance-llm-training")
    data_dir = work_dir / "data"
    output_dir = work_dir / "outputs" / run_id
    adapter_dir = output_dir / "adapter"
    report_dir = output_dir / "reports"

    if work_dir.exists():
        shutil.rmtree(work_dir)

    data_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    train_local_path = data_dir / "train.jsonl"
    eval_local_path = data_dir / "eval.jsonl"

    download_s3_file(train_dataset_s3_uri, train_local_path)
    download_s3_file(eval_dataset_s3_uri, eval_local_path)

    train_dataset = load_dataset("json", data_files=str(train_local_path), split="train")
    eval_dataset = load_dataset("json", data_files=str(eval_local_path), split="train")

    train_dataset = train_dataset.map(lambda row: {"text": format_instruction(row)})
    eval_dataset = eval_dataset.map(lambda row: {"text": format_instruction(row)})

    logger.info("Train rows: %s", len(train_dataset))
    logger.info("Eval rows: %s", len(eval_dataset))

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    tokenizer = AutoTokenizer.from_pretrained(
        base_model_name,
        token=hf_token or None,
        use_fast=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        token=hf_token or None,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=str(output_dir / "trainer"),
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        logging_steps=5,
        save_strategy="epoch",
        evaluation_strategy="epoch",
        report_to=[],
        bf16=torch.cuda.is_available(),
        fp16=False,
        optim="paged_adamw_8bit",
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        packing=False,
    )

    train_result = trainer.train()
    eval_result = trainer.evaluate()

    logger.info("Saving LoRA adapter to %s", adapter_dir)
    trainer.model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    train_metrics = train_result.metrics
    eval_metrics = eval_result

    config_payload = {
        "run_id": run_id,
        "base_model_name": base_model_name,
        "train_dataset_s3_uri": train_dataset_s3_uri,
        "eval_dataset_s3_uri": eval_dataset_s3_uri,
        "output_s3_uri": output_s3_uri,
        "max_seq_length": max_seq_length,
        "num_train_epochs": num_train_epochs,
        "per_device_train_batch_size": per_device_train_batch_size,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "learning_rate": learning_rate,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "lora_dropout": lora_dropout,
    }

    write_json(report_dir / "config.json", config_payload)
    write_json(report_dir / "train_metrics.json", train_metrics)
    write_json(report_dir / "eval_metrics.json", eval_metrics)

    readme = f"""# Llama 3 Finance LoRA Adapter

Run ID: `{run_id}`

Base model: `{base_model_name}`

This artifact contains a PEFT LoRA adapter trained for finance instruction tasks.

Files:
- `adapter/`
- `reports/config.json`
- `reports/train_metrics.json`
- `reports/eval_metrics.json`
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    upload_directory_to_s3(output_dir, output_s3_uri)

    logger.info("Training complete. Artifacts uploaded to %s", output_s3_uri)


if __name__ == "__main__":
    main()