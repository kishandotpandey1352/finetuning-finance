from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from demos.remitly_treasury.llm_commentary import (
    generate_treasury_commentary,
)
from demos.remitly_treasury.web_demo_service import (
    SUPPORTED_SCENARIOS,
    run_web_demo_scenario,
)


router = APIRouter(
    prefix="/api/demo/treasury",
    tags=["Treasury Demo"],
)


class TreasuryDemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal[
        "normal",
        "shortfall",
        "stale",
        "tool_failure",
        "unauthorized_tool",
    ]


@router.get("/scenarios")
async def list_treasury_demo_scenarios():
    return {"scenarios": list(SUPPORTED_SCENARIOS)}


@router.post("/run")
async def run_treasury_demo(request: TreasuryDemoRequest):
    try:
        return await run_web_demo_scenario(
            request.scenario,
            commentary_generator=generate_treasury_commentary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
