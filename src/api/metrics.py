import subprocess
from typing import Any

from prometheus_client import Counter, Gauge, Histogram


API_REQUESTS_TOTAL = Counter(
    "finance_api_requests_total",
    "Total number of API requests.",
    ["endpoint", "status"],
)

API_LATENCY_SECONDS = Histogram(
    "finance_api_latency_seconds",
    "API request latency in seconds.",
    ["endpoint"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30, 60, 120),
)

API_TOKENS_TOTAL = Counter(
    "finance_api_tokens_total",
    "Total number of model tokens processed.",
    ["endpoint", "token_type"],
)

API_TOKENS_PER_SECOND = Gauge(
    "finance_api_tokens_per_second",
    "Tokens processed per second for the latest request.",
    ["endpoint"],
)

GPU_AVAILABLE = Gauge(
    "finance_gpu_available",
    "Whether GPU metrics are available. 1 means available, 0 means unavailable.",
)

GPU_UTILIZATION_PERCENT = Gauge(
    "finance_gpu_utilization_percent",
    "GPU utilization percentage from nvidia-smi.",
)

GPU_MEMORY_USED_MB = Gauge(
    "finance_gpu_memory_used_mb",
    "GPU memory used in MB from nvidia-smi.",
)

GPU_MEMORY_TOTAL_MB = Gauge(
    "finance_gpu_memory_total_mb",
    "Total GPU memory in MB from nvidia-smi.",
)


def record_success(endpoint: str, latency_seconds: float, usage: dict[str, Any]) -> None:
    API_REQUESTS_TOTAL.labels(endpoint=endpoint, status="success").inc()
    API_LATENCY_SECONDS.labels(endpoint=endpoint).observe(latency_seconds)

    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", 0))

    API_TOKENS_TOTAL.labels(endpoint=endpoint, token_type="prompt").inc(prompt_tokens)
    API_TOKENS_TOTAL.labels(endpoint=endpoint, token_type="completion").inc(completion_tokens)
    API_TOKENS_TOTAL.labels(endpoint=endpoint, token_type="total").inc(total_tokens)

    if latency_seconds > 0:
        API_TOKENS_PER_SECOND.labels(endpoint=endpoint).set(total_tokens / latency_seconds)


def record_failure(endpoint: str, latency_seconds: float) -> None:
    API_REQUESTS_TOTAL.labels(endpoint=endpoint, status="error").inc()
    API_LATENCY_SECONDS.labels(endpoint=endpoint).observe(latency_seconds)


def update_gpu_metrics() -> None:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )

        first_gpu = result.stdout.strip().splitlines()[0]
        utilization, memory_used, memory_total = [
            float(value.strip()) for value in first_gpu.split(",")
        ]

        GPU_AVAILABLE.set(1)
        GPU_UTILIZATION_PERCENT.set(utilization)
        GPU_MEMORY_USED_MB.set(memory_used)
        GPU_MEMORY_TOTAL_MB.set(memory_total)

    except Exception:
        GPU_AVAILABLE.set(0)