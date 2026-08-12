from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Query,
)

from app.schemas.fact_api import (
    DocumentFinancialFactsResponse,
)

from app.services.fact_query_service import (
    FactQueryError,
    list_document_facts,
)


router = APIRouter(
    prefix="/facts",
    tags=["financial-facts"],
)


def _resolve_user_id(
    x_user_id: Annotated[
        str | None,
        Header(alias="X-User-Id"),
    ] = None,
) -> str:
    # Local development fallback.
    #
    # When real authentication is added,
    # replace this with the authenticated
    # user ID from your auth dependency.
    return (
        x_user_id
        or "local-demo-user"
    )


@router.get(
    "/documents/{document_id}",
    response_model=(
        DocumentFinancialFactsResponse
    ),
)
def get_document_facts(
    document_id: str,
    status: str = Query(
        default="validated",
        pattern=(
            "^(all|pending|validated|"
            "rejected|conflict)$"
        ),
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    x_user_id: Annotated[
        str | None,
        Header(alias="X-User-Id"),
    ] = None,
) -> DocumentFinancialFactsResponse:
    resolved_user_id = (
        x_user_id
        or "local-demo-user"
    )

    try:
        return list_document_facts(
            user_id=resolved_user_id,
            document_id=document_id,
            status=status,
            offset=offset,
            limit=limit,
        )

    except FactQueryError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load financial "
                f"facts: {type(error).__name__}: "
                f"{error}"
            ),
        ) from error