import argparse
import json
from pathlib import Path
import os

import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)


def load_jsonl_dataset(path: str) -> Dataset:
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        raise ValueError(f"No records found in {path}")

    return Dataset.from_list(records)


def format_prompt(example: dict) -> str:
    instruction = example["instruction"]
    input_text = example["input"]
    output = example["output"]

    prompt = f"""### Instruction:
{instruction}

### Input:
{input_text}

### Response:
{output}"""

    return prompt


def tokenize_dataset(dataset: Dataset, tokenizer, max_length: int) -> Dataset:
    def tokenize(example):
        text = format_prompt(example)

        tokenized = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding=False,
        )

        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    return dataset.map(tokenize, remove_columns=dataset.column_names)


def create_bnb_config():
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )


def create_lora_config():
    return LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )


def main():
    parser = argparse.ArgumentParser(description="QLoRA fine-tuning script")

    parser.add_argument(
        "--model-name",
        type=str,
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Base model name",
    )

    parser.add_argument(
        "--dataset-path",
        type=str,
        default="data/instruction/finance_gold_v1.jsonl",
        help="Path to JSONL instruction dataset",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/qlora-finance",
        help="Directory to save LoRA adapter",
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="Max sequence length",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=1,
        help="Number of training epochs",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Max training steps for smoke test",
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
        help="Learning rate",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("QLoRA Training")
    print("=" * 80)
    print(f"Model: {args.model_name}")
    print(f"Dataset: {args.dataset_path}")
    print(f"Output dir: {args.output_dir}")
    print(f"CUDA available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    dataset = load_jsonl_dataset(args.dataset_path)
    print(f"Loaded dataset with {len(dataset)} records")

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, token=os.getenv("HF_TOKEN"))

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = create_bnb_config()

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    model.config.use_cache = False
    model.gradient_checkpointing_enable()

    model = prepare_model_for_kbit_training(model)

    lora_config = create_lora_config()
    model = get_peft_model(model, lora_config)

    print("Trainable parameters:")
    model.print_trainable_parameters()

    tokenized_dataset = tokenize_dataset(
        dataset=dataset,
        tokenizer=tokenizer,
        max_length=args.max_length,
    )

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=args.learning_rate,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        logging_steps=1,
        save_steps=10,
        save_total_limit=2,
        fp16=True,
        optim="paged_adamw_8bit",
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )

    trainer.train()

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    print("=" * 80)
    print("Training complete")
    print(f"LoRA adapter saved to: {args.output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()