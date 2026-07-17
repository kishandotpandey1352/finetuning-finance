import time
from contextlib import contextmanager

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


REQUEST_COUNT = Counter(
    "finance_api_requests_total",
    "Total number of API requests.",
    ["endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "finance_api_request_latency_seconds",
    "Request latency in seconds.",
    ["endpoint"],
)

MODEL_GENERATION_COUNT = Counter(
    "finance_model_generations_total",
    "Total number of model generations.",
    ["task"],
)

MODEL_GENERATION_LATENCY = Histogram(
    "finance_model_generation_latency_seconds",
    "Model generation latency in seconds.",
    ["task"],
)


@contextmanager
def track_latency(histogram: Histogram, labels: dict):
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        histogram.labels(**labels).observe(elapsed)


def metrics_response() -> bytes:
    return generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST