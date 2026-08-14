from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)


class WebGapDecision(BaseModel):
    needs_web: bool = False

    reason: str | None = None

    requested_years: list[int] = Field(
        default_factory=list,
    )

    covered_years: list[int] = Field(
        default_factory=list,
    )

    missing_years: list[int] = Field(
        default_factory=list,
    )

    local_fact_count: int = 0

    local_source_count: int = 0


class WebResearchInput(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=4000,
    )

    gap_reason: str | None = Field(
        default=None,
        max_length=2000,
    )

    trusted_domains: list[str] = Field(
        default_factory=list,
        max_length=25,
    )

    max_results: int = Field(
        default=8,
        ge=1,
        le=20,
    )


class WebSearchCandidate(BaseModel):
    rank: int = Field(
        ge=1,
    )

    original_position: int | None = None

    title: str

    url: str

    domain: str

    snippet: str | None = None

    trust_tier: Literal[
        "public_authority",
        "trusted_domain",
        "finance_candidate",
        "general_web",
        "low_trust",
    ]

    ranking_score: float


class WebResearchOutput(BaseModel):
    ok: bool = True

    provider: Literal[
        "serper"
    ] = "serper"

    query: str

    searched: bool = True

    candidate_count: int = 0

    candidates: list[
        WebSearchCandidate
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )