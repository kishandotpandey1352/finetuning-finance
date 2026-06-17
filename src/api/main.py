import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.api.vllm_client import (
    VLLMClientError,
    extract_text,
    extract_usage,
    generate_chat_completion,
)


app = FastAPI(title=os.getenv("APP_NAME", "finance-ai-platform"))


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=10)
    max_tokens: int = Field(default=256, ge=32, le=1024)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


class ModelUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class SummarizeResponse(BaseModel):
    task: str
    summary: str
    model: str
    latency_seconds: float
    usage: ModelUsage


@app.get("/")
def root():
    return {
        "message": "Finance AI Platform API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": os.getenv("APP_NAME"),
        "serving_model": os.getenv("VLLM_MODEL_NAME", "finance-qwen1.5b"),
        "vllm_base_url": os.getenv("VLLM_BASE_URL"),
        "training_model": os.getenv("MODEL_NAME"),
    }


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    system_prompt = (
        "You are a finance AI assistant. Summarize financial text clearly, "
        "concisely, and accurately. Focus on revenue, costs, profitability, "
        "cash flow, risks, and business drivers when relevant."
    )

    user_prompt = f"""Summarize the following financial text: {request.text}"""

    start = time.perf_counter()

    try:
        response = await generate_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        summary = extract_text(response)
        usage = extract_usage(response)

    except VLLMClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    latency = time.perf_counter() - start

    return SummarizeResponse(
        task="summarization",
        summary=summary,
        model=os.getenv("VLLM_MODEL_NAME", "finance-qwen1.5b"),
        latency_seconds=latency,
        usage=usage,
    )