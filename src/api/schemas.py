from typing import Optional

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=10)
    max_new_tokens: int = Field(256, ge=32, le=1024)
    temperature: float = Field(0.2, ge=0.0, le=1.5)


class SummarizeResponse(BaseModel):
    summary: str
    model_id: str


class QARequest(BaseModel):
    question: str = Field(..., min_length=3)
    context: Optional[str] = None
    max_new_tokens: int = Field(256, ge=32, le=1024)
    temperature: float = Field(0.2, ge=0.0, le=1.5)


class QAResponse(BaseModel):
    answer: str
    model_id: str


class RiskAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10)
    max_new_tokens: int = Field(384, ge=32, le=1024)
    temperature: float = Field(0.2, ge=0.0, le=1.5)


class RiskAnalysisResponse(BaseModel):
    risk_analysis: str
    model_id: str


class HealthResponse(BaseModel):
    status: str
    service: str
    model_id: str


class ReadyResponse(BaseModel):
    ready: bool
    model_loaded: bool
    adapter_loaded: bool
    model_id: str