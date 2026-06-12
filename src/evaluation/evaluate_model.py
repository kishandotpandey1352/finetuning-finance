import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import evaluate
import torch
from bert_score import score as bert_score
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


SUPPORTED_TASKS = {"summarization", "risk_analysis", "financial_qa"}
REQUIRED_FIELDS = ["instruction", "input", "output"]


def validate_record(record: dict, source_path: Path, line_number: int) -> None:
    for field in REQUIRED_FIELDS:
        if field not in record:
            raise ValueError(
                f"Missing field '{field}' in {source_path} at line {line_number}"
            )

        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(
                f"Field '{field}' is empty or invalid in {source_path} at line {line_number}"
            )

    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError(
            f"Missing or invalid metadata object in {source_path} at line {line_number}"
        )

    task = metadata.get("task")
    if task not in SUPPORTED_TASKS:
        raise ValueError(
            f"Unsupported or missing metadata.task in {source_path} at line {line_number}: {task}"
        )


def load_dataset(
    dataset_path: Path,
    max_examples: int | None = None,
    max_examples_per_task: int | None = None,
) -> list[dict]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    records = []
    task_counts = {task: 0 for task in SUPPORTED_TASKS}

    with dataset_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Malformed JSON in {dataset_path} at line {line_number}: {error}"
                ) from error

            validate_record(record, dataset_path, line_number)
            task = record["metadata"]["task"]

            if (
                max_examples_per_task is not None
                and task_counts[task] >= max_examples_per_task
            ):
                continue

            records.append(
                {
                    "id": len(records),
                    "task": task,
                    "instruction": record["instruction"],
                    "input": record["input"],
                    "reference": record["output"],
                    "metadata": record["metadata"],
                }
            )
            task_counts[task] += 1

            if max_examples is not None and len(records) >= max_examples:
                break

    if not records:
        raise ValueError(f"No valid evaluation records loaded from: {dataset_path}")

    return records


def group_by_task(records: list[dict]) -> dict[str, list[dict]]:
    grouped = {task: [] for task in sorted(SUPPORTED_TASKS)}

    for record in records:
        grouped[record["task"]].append(record)

    return grouped


def generate_mock_predictions(records: list[dict]) -> list[dict]:
    predictions = []

    for record in records:
        predictions.append(
            {
                **record,
                "prediction": record["reference"],
            }
        )

    return predictions


def format_prompt(record: dict) -> str:
    return f"""### Instruction:
{record["instruction"]}

### Input:
{record["input"]}

### Response:
"""


def load_model_and_tokenizer(model_name: str, adapter: str | None, device_map: str):
    tokenizer_path = adapter if adapter else model_name
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map=device_map,
        trust_remote_code=True,
    )

    if adapter:
        model = PeftModel.from_pretrained(model, adapter)

    model.eval()
    return model, tokenizer


def generate_model_predictions(
    records: list[dict],
    model,
    tokenizer,
    max_new_tokens: int,
) -> list[dict]:
    predictions = []

    for record in records:
        prompt = format_prompt(record)
        inputs = tokenizer(prompt, return_tensors="pt")
        input_device = next(model.parameters()).device
        inputs = {key: value.to(input_device) for key, value in inputs.items()}
        prompt_length = inputs["input_ids"].shape[-1]

        with torch.no_grad():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        response_ids = generated_ids[0][prompt_length:]
        prediction = tokenizer.decode(response_ids, skip_special_tokens=True).strip()

        predictions.append(
            {
                **record,
                "prompt": prompt,
                "prediction": prediction,
            }
        )

    return predictions


def compute_task_metrics(predictions: list[dict], rouge_metric) -> dict:
    if not predictions:
        return {
            "num_examples": 0,
            "rouge1": None,
            "rouge2": None,
            "rougeL": None,
            "rougeLsum": None,
            "bertscore_precision": None,
            "bertscore_recall": None,
            "bertscore_f1": None,
        }

    predicted_texts = [record["prediction"] for record in predictions]
    reference_texts = [record["reference"] for record in predictions]

    rouge_result = rouge_metric.compute(
        predictions=predicted_texts,
        references=reference_texts,
    )

    precision, recall, f1 = bert_score(
        predicted_texts,
        reference_texts,
        lang="en",
        verbose=False,
    )

    return {
        "num_examples": len(predictions),
        "rouge1": float(rouge_result["rouge1"]),
        "rouge2": float(rouge_result["rouge2"]),
        "rougeL": float(rouge_result["rougeL"]),
        "rougeLsum": float(rouge_result["rougeLsum"]),
        "bertscore_precision": float(precision.mean()),
        "bertscore_recall": float(recall.mean()),
        "bertscore_f1": float(f1.mean()),
    }


def compute_metrics(predictions: list[dict]) -> dict:
    rouge_metric = evaluate.load("rouge")
    grouped = group_by_task(predictions)
    task_metrics = {}

    for task, task_predictions in grouped.items():
        task_metrics[task] = compute_task_metrics(task_predictions, rouge_metric)

    task_metrics["overall"] = compute_task_metrics(predictions, rouge_metric)
    return task_metrics


def write_predictions(predictions: list[dict], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        for record in predictions:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_metrics(metrics: dict, output_path: Path, run_info: dict) -> None:
    report = {
        "run": run_info,
        "metrics": metrics,
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_summary(metrics: dict, output_path: Path, run_info: dict) -> None:
    lines = [
        "# Evaluation Summary",
        "",
        f"Run name: `{run_info['run_name']}`",
        f"Dataset: `{run_info['dataset']}`",
        f"Mode: `{run_info['mode']}`",
        f"Examples: `{run_info['num_examples']}`",
        f"Created at: `{run_info['created_at']}`",
        "",
        "## Metrics by Task",
        "",
        "| Task | Examples | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for task in ["summarization", "risk_analysis", "financial_qa", "overall"]:
        task_metrics = metrics[task]
        lines.append(
            "| {task} | {num_examples} | {rouge1} | {rouge2} | {rougeL} | {bertscore_f1} |".format(
                task=task,
                num_examples=task_metrics["num_examples"],
                rouge1=format_metric(task_metrics["rouge1"]),
                rouge2=format_metric(task_metrics["rouge2"]),
                rougeL=format_metric(task_metrics["rougeL"]),
                bertscore_f1=format_metric(task_metrics["bertscore_f1"]),
            )
        )

    lines.extend(["", "## Notes", ""])

    if run_info["mode"] == "mock":
        lines.extend(
            [
                "- This run uses mock predictions, so each prediction is copied from the reference output.",
                "- Scores should be near perfect in mock mode. Use this to validate the evaluation pipeline before model loading is added.",
            ]
        )
    else:
        lines.extend(
            [
                f"- Model: `{run_info['model_name']}`",
                f"- Adapter: `{run_info['adapter']}`",
                "- Predictions were generated deterministically with `do_sample=False`.",
            ]
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_metric(value: float | None) -> str:
    if value is None:
        return "n/a"

    return f"{value:.4f}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate finance instruction-tuning predictions by task."
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default="data/instruction/finance_gold_v1.jsonl",
        help="Path to evaluation JSONL dataset.",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/evaluation",
        help="Directory where run reports should be saved.",
    )

    parser.add_argument(
        "--run-name",
        type=str,
        default="mock_eval",
        help="Name for this evaluation run.",
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use reference outputs as predictions.",
    )

    parser.add_argument(
        "--max-examples",
        type=int,
        default=None,
        help="Maximum number of examples to evaluate.",
    )

    parser.add_argument(
        "--max-examples-per-task",
        type=int,
        default=None,
        help="Maximum number of examples to evaluate for each task.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing output run directory.",
    )

    parser.add_argument(
        "--model-name",
        type=str,
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Base model name or path for real evaluation.",
    )

    parser.add_argument(
        "--adapter",
        type=str,
        default=None,
        help="Optional PEFT/LoRA adapter path.",
    )

    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=128,
        help="Maximum new tokens to generate for each prediction.",
    )

    parser.add_argument(
        "--device-map",
        type=str,
        default="auto",
        help="Device map passed to AutoModelForCausalLM.from_pretrained.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataset_path = Path(args.dataset)
    run_dir = Path(args.output_dir) / args.run_name

    if run_dir.exists() and not args.overwrite:
        raise FileExistsError(
            f"Output run directory already exists: {run_dir}. "
            "Use --overwrite to replace its report files."
        )

    run_dir.mkdir(parents=True, exist_ok=True)

    records = load_dataset(
        dataset_path,
        max_examples=args.max_examples,
        max_examples_per_task=args.max_examples_per_task,
    )

    if args.mock:
        predictions = generate_mock_predictions(records)
        mode = "mock"
    else:
        model, tokenizer = load_model_and_tokenizer(
            model_name=args.model_name,
            adapter=args.adapter,
            device_map=args.device_map,
        )
        predictions = generate_model_predictions(
            records=records,
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=args.max_new_tokens,
        )
        mode = "model"

    metrics = compute_metrics(predictions)

    run_info = {
        "run_name": args.run_name,
        "dataset": str(dataset_path),
        "output_dir": str(run_dir),
        "mode": mode,
        "model_name": args.model_name,
        "adapter": args.adapter,
        "max_new_tokens": args.max_new_tokens,
        "device_map": args.device_map,
        "num_examples": len(records),
        "max_examples": args.max_examples,
        "max_examples_per_task": args.max_examples_per_task,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    write_predictions(predictions, run_dir / "predictions.jsonl")
    write_metrics(metrics, run_dir / "metrics.json", run_info)
    write_summary(metrics, run_dir / "summary.md", run_info)

    print(f"Evaluated {len(records)} examples")
    print(f"Saved predictions to: {run_dir / 'predictions.jsonl'}")
    print(f"Saved metrics to: {run_dir / 'metrics.json'}")
    print(f"Saved summary to: {run_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
