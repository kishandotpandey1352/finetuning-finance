from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)


WebTrustTier = Literal[
    "public_authority",
    "trusted_domain",
    "finance_candidate",
    "general_web",
    "low_trust",
]


WebContentKind = Literal[
    "html",
    "text",
    "pdf",
]


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

    trust_tier: WebTrustTier

    ranking_score: float


class WebEvidencePassage(BaseModel):
    text: str

    score: float

    page_number: int | None = None

    matched_terms: list[str] = Field(
        default_factory=list,
    )


class WebFetchedSource(BaseModel):
    search_rank: int

    title: str

    requested_url: str

    final_url: str

    domain: str

    content_type: WebContentKind

    trust_tier: WebTrustTier

    http_status: int

    text_chars: int = 0

    evidence_passages: list[
        WebEvidencePassage
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )


class WebFetchFailure(BaseModel):
    search_rank: int

    title: str

    url: str

    reason: str


# =========================================================
# Phase 3H-D
# Persistent citation source
# =========================================================


class WebCitationSource(BaseModel):
    # Citation number is request-scoped.
    #
    # Database source IDs are persistent.
    #
    # Example:
    #
    # [Web Source 2001]
    #
    source_number: int = Field(
        ge=2001,
    )

    source_id: str

    source_type: Literal[
        "web"
    ] = "web"

    title: str

    url: str

    domain: str

    snippet: str

    page_number: int | None = None

    trust_tier: WebTrustTier

    provider: Literal[
        "serper"
    ] = "serper"

    content_type: WebContentKind

    evidence_score: float | None = None

    retrieved_at: str


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

    fetched_source_count: int = 0

    evidence_source_count: int = 0

    evidence_ready: bool = False

    fetched_sources: list[
        WebFetchedSource
    ] = Field(
        default_factory=list,
    )

    fetch_failures: list[
        WebFetchFailure
    ] = Field(
        default_factory=list,
    )

    # -----------------------------------------------------
    # Phase 3H-D
    # -----------------------------------------------------

    citation_ready: bool = False

    citation_source_count: int = 0

    citation_sources: list[
        WebCitationSource
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )