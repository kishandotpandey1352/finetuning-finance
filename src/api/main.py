import logging
import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import Response

from src.api.auth import verify_api_key
from src.api.metrics import (
    MODEL_GENERATION_COUNT,
    MODEL_GENERATION_LATENCY,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    metrics_content_type,
    metrics_response,
    track_latency,
)
from src.api.schemas import (
    HealthResponse,
    QARequest,
    QAResponse,
    ReadyResponse,
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from src.inference.model_loader_eks import get_finance_llm


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

logger = logging.getLogger("finance-api")

MODEL_ID = os.getenv("MODEL_ID", "qwen2.5-3b-finance-runB-r16-lr2e4")
SERVICE_NAME = os.getenv("SERVICE_NAME", "finance-llm-inference-api")
USE_MOCK_MODEL = os.getenv("USE_MOCK_MODEL", "false").lower() == "true"

app = FastAPI(
    title="Finance LLM Inference API",
    description="Secure FastAPI service for finance summarization, QA, and risk analysis.",
    version="1.0.0",
)

_model_loaded = False
_adapter_loaded = False


class MockFinanceLLM:
    def generate(
        self,
        user_message: str,
        max_new_tokens: int = 256,
        temperature: float = 0.2,
        **kwargs,
    ) -> str:
        return (
            "Mock finance response: The text indicates potential margin pressure, "
            "interest expense risk, and business execution risk. This response verifies "
            "that the secure API layer is working."
        )


def get_model():
    global _model_loaded, _adapter_loaded

    if USE_MOCK_MODEL:
        _model_loaded = True
        _adapter_loaded = True
        return MockFinanceLLM()

    try:
        model = get_finance_llm()
        model.load()
        _model_loaded = model.model is not None
        _adapter_loaded = model.model is not None
        return model
    except Exception as exc:
        logger.exception("Failed to load finance model.")
        _model_loaded = False
        _adapter_loaded = False
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model is not available: {exc}",
        ) from exc


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        model_id=MODEL_ID,
    )


@app.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    if USE_MOCK_MODEL:
        return ReadyResponse(
            ready=True,
            model_loaded=True,
            adapter_loaded=True,
            model_id=MODEL_ID,
        )

    return ReadyResponse(
        ready=_model_loaded and _adapter_loaded,
        model_loaded=_model_loaded,
        adapter_loaded=_adapter_loaded,
        model_id=MODEL_ID,
    )


@app.post(
    "/summarize",
    response_model=SummarizeResponse,
    dependencies=[Depends(verify_api_key)],
)
def summarize(request: SummarizeRequest) -> SummarizeResponse:
    endpoint = "/summarize"

    with track_latency(REQUEST_LATENCY, {"endpoint": endpoint}):
        try:
            model = get_model()

            prompt = (
                "Summarize the following financial text. "
                "Focus on key business drivers, risks, and important financial details.\n\n"
                f"{request.text}"
            )

            with track_latency(MODEL_GENERATION_LATENCY, {"task": "summarize"}):
                summary = model.generate(
                    prompt,
                    max_new_tokens=request.max_new_tokens,
                    temperature=request.temperature,
                )

            MODEL_GENERATION_COUNT.labels(task="summarize").inc()
            REQUEST_COUNT.labels(endpoint=endpoint, status="success").inc()

            return SummarizeResponse(summary=summary, model_id=MODEL_ID)

        except HTTPException:
            REQUEST_COUNT.labels(endpoint=endpoint, status="error").inc()
            raise
        except Exception as exc:
            logger.exception("Summarization failed.")
            REQUEST_COUNT.labels(endpoint=endpoint, status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Summarization failed: {exc}",
            ) from exc


@app.post(
    "/qa",
    response_model=QAResponse,
    dependencies=[Depends(verify_api_key)],
)
def qa(request: QARequest) -> QAResponse:
    endpoint = "/qa"

    with track_latency(REQUEST_LATENCY, {"endpoint": endpoint}):
        try:
            model = get_model()

            if request.context:
                prompt = (
                    "Answer the financial question using the provided context. "
                    "Be concise and mention uncertainty where relevant.\n\n"
                    f"Context:\n{request.context}\n\n"
                    f"Question:\n{request.question}"
                )
            else:
                prompt = (
                    "Answer the following financial question. "
                    "Be concise and risk-aware.\n\n"
                    f"Question:\n{request.question}"
                )

            with track_latency(MODEL_GENERATION_LATENCY, {"task": "qa"}):
                answer = model.generate(
                    prompt,
                    max_new_tokens=request.max_new_tokens,
                    temperature=request.temperature,
                )

            MODEL_GENERATION_COUNT.labels(task="qa").inc()
            REQUEST_COUNT.labels(endpoint=endpoint, status="success").inc()

            return QAResponse(answer=answer, model_id=MODEL_ID)

        except HTTPException:
            REQUEST_COUNT.labels(endpoint=endpoint, status="error").inc()
            raise
        except Exception as exc:
            logger.exception("QA failed.")
            REQUEST_COUNT.labels(endpoint=endpoint, status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"QA failed: {exc}",
            ) from exc


@app.post(
    "/risk-analysis",
    response_model=RiskAnalysisResponse,
    dependencies=[Depends(verify_api_key)],
)
def risk_analysis(request: RiskAnalysisRequest) -> RiskAnalysisResponse:
    endpoint = "/risk-analysis"

    with track_latency(REQUEST_LATENCY, {"endpoint": endpoint}):
        try:
            model = get_model()

            prompt = (
                "Analyze the financial risks in the following text. "
                "Group the answer into market risk, credit risk, liquidity risk, "
                "operational risk, and business risk where applicable.\n\n"
                f"{request.text}"
            )

            with track_latency(MODEL_GENERATION_LATENCY, {"task": "risk_analysis"}):
                analysis = model.generate(
                    prompt,
                    max_new_tokens=request.max_new_tokens,
                    temperature=request.temperature,
                )

            MODEL_GENERATION_COUNT.labels(task="risk_analysis").inc()
            REQUEST_COUNT.labels(endpoint=endpoint, status="success").inc()

            return RiskAnalysisResponse(risk_analysis=analysis, model_id=MODEL_ID)

        except HTTPException:
            REQUEST_COUNT.labels(endpoint=endpoint, status="error").inc()
            raise
        except Exception as exc:
            logger.exception("Risk analysis failed.")
            REQUEST_COUNT.labels(endpoint=endpoint, status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Risk analysis failed: {exc}",
            ) from exc


@app.get("/metrics")
def metrics() -> Response:
    return Response(
        content=metrics_response(),
        media_type=metrics_content_type(),
    )