from __future__ import annotations

from pydantic import BaseModel, Field


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