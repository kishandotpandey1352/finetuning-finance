import argparse
import json
from pathlib import Path

import torch
import evaluate
from bert_score import score
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


def load_jsonl(path: str):
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        raise ValueError(f"No records found in {path}")

    return records


def build_prompt(record: dict) -> str:
    return f"""### Instruction:
{record["instruction"]}

### Input:
{record["input"]}

### Response:
"""


def generate_prediction(model, tokenizer, prompt: str, max_new_tokens: int):
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)

    inputs = {
        key: value.to(model.device)
        for key, value in inputs.items()
    }

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    if "### Response:" in generated_text:
        return generated_text.split("### Response:")[-1].strip()

    return generated_text.strip()


def mock_prediction(record: dict) -> str:
    task = record.get("metadata", {}).get("task", "unknown")

    if task == "summarization":
        return "The text discusses financial performance, revenue trends, and business drivers."

    if task == "risk_analysis":
        return "The text identifies a financial or business risk."

    if task == "financial_qa":
        return "The answer explains the finance concept using the provided context."

    return "No prediction available."


def compute_metrics(predictions, references):
    rouge = evaluate.load("rouge")

    rouge_result = rouge.compute(
        predictions=predictions,
        references=references,
    )

    precision, recall, f1 = score(
        predictions,
        references,
        lang="en",
        model_type="distilbert-base-uncased",
        verbose=False,
    )

    bertscore_result = {
        "bertscore_precision": float(precision.mean()),
        "bertscore_recall": float(recall.mean()),
        "bertscore_f1": float(f1.mean()),
    }

    results = {}
    results.update(rouge_result)
    results.update(bertscore_result)

    return results


def save_report(output_path: str, metrics: dict, examples: list):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "metrics": metrics,
        "examples": examples,
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Evaluation report saved to: {path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate base or fine-tuned model")

    parser.add_argument(
        "--dataset-path",
        type=str,
        default="data/instruction/finance_gold_v1.jsonl",
        help="Evaluation JSONL dataset",
    )

    parser.add_argument(
        "--model-name",
        type=str,
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Base model name",
    )

    parser.add_argument(
        "--adapter-path",
        type=str,
        default=None,
        help="Optional LoRA adapter path",
    )

    parser.add_argument(
        "--output-report",
        type=str,
        default="reports/evaluation_report.json",
        help="Path to save evaluation report",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of examples to evaluate",
    )

    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=128,
        help="Max generated tokens",
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run evaluation with mock predictions instead of model generation",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Model Evaluation")
    print("=" * 80)

    records = load_jsonl(args.dataset_path)
    records = records[: args.limit]

    print(f"Loaded {len(records)} evaluation records")

    predictions = []
    references = []
    examples = []

    model = None
    tokenizer = None

    if not args.mock:
        print(f"Loading model: {args.model_name}")

        tokenizer = AutoTokenizer.from_pretrained(args.model_name)

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            args.model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )

        if args.adapter_path:
            print(f"Loading LoRA adapter: {args.adapter_path}")
            model = PeftModel.from_pretrained(model, args.adapter_path)

        model.eval()

    for idx, record in enumerate(records):
        reference = record["output"]

        if args.mock:
            prediction = mock_prediction(record)
        else:
            prompt = build_prompt(record)
            prediction = generate_prediction(
                model=model,
                tokenizer=tokenizer,
                prompt=prompt,
                max_new_tokens=args.max_new_tokens,
            )

        predictions.append(prediction)
        references.append(reference)

        examples.append(
            {
                "id": idx,
                "instruction": record["instruction"],
                "input": record["input"],
                "reference": reference,
                "prediction": prediction,
                "metadata": record.get("metadata", {}),
            }
        )

        print(f"Evaluated example {idx + 1}/{len(records)}")

    metrics = compute_metrics(predictions, references)

    print("\nMetrics:")
    for key, value in metrics.items():
        print(f"{key}: {value:.4f}")

    save_report(
        output_path=args.output_report,
        metrics=metrics,
        examples=examples,
    )

    print("=" * 80)
    print("Evaluation complete")
    print("=" * 80)


if __name__ == "__main__":
    main()