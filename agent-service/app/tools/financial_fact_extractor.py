from __future__ import annotations

import re

from decimal import Decimal
from typing import Any

from supabase import (
    Client,
    create_client,
)

from app.core.config import (
    settings,
)

from app.schemas.facts import (
    FinancialFactExtractionRequest,
)

from app.schemas.tools import (
    FinancialFactExtractorInput,
    FinancialFactExtractorOutput,
    FinancialFactToolDocumentSummary,
    FinancialFactToolFact,
    FinancialFactToolSource,
)

from app.services.financial_fact_extractor import (
    extract_financial_facts,
)

from app.services.fact_validator import (
    validate_document_facts,
)


# ============================================================
# Errors
# ============================================================


class FinancialFactToolError(
    RuntimeError,
):
    pass


# ============================================================
# Query relevance
#
# These words are ONLY used for ranking existing facts.
# They are not an allowed metric vocabulary.
# ============================================================


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "show",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "what",
    "which",
    "with",
    "annual",
    "are",
    "as",
    "at",
    "be",
    "by",
    "compare",
    "comparison",
    "did",
    "do",
    "does",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "quarter",
    "quarterly",
    "show",
    "the",
    "their",
    "this",
    "to",
    "trend",
    "value",
    "values",
    "was",
    "were",
    "what",
    "which",
    "with",
    "year",
    "years",
    
}


# ============================================================
# Infrastructure
# ============================================================


def _get_supabase_client() -> Client:
    if not settings.supabase_url:
        raise FinancialFactToolError(
            "SUPABASE_URL is required "
            "for financial fact tool execution."
        )

    if (
        not settings
        .supabase_service_role_key
    ):
        raise FinancialFactToolError(
            "SUPABASE_SERVICE_ROLE_KEY "
            "is required for financial "
            "fact tool execution."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


# ============================================================
# Generic helpers
# ============================================================


def _clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .split()
    )


def _normalize_search_text(
    value: Any,
) -> str:
    text = (
        _clean_text(
            value
        )
        .lower()
    )

    text = re.sub(
        r"[^a-z0-9%]+",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


def _significant_tokens(
    value: Any,
) -> set[str]:
    normalized = (
        _normalize_search_text(
            value
        )
    )

    return {
        token
        for token
        in normalized.split()
        if (
            token
            and token
            not in STOP_WORDS
            and (
                len(token) >= 3
                or token.isdigit()
            )
        )
    }


def _as_decimal(
    value: Any,
) -> Decimal | None:
    if (
        value is None
        or value == ""
    ):
        return None

    try:
        return Decimal(
            str(value)
        )

    except Exception:
        return None


# ============================================================
# Existing validated facts
# ============================================================


def _load_validated_fact_rows(
    *,
    client: Client,
    user_id: str,
    document_id: str,
) -> list[
    dict[str, Any]
]:
    response = (
        client
        .table(
            "analysis_facts"
        )
        .select(
            (
                "id,"
                "document_id,"
                "source_ledger_id,"
                "company,"
                "metric_key,"
                "canonical_metric_key,"
                "metric_label,"
                "value_type,"
                "numeric_value,"
                "normalized_numeric_value,"
                "text_value,"
                "raw_value,"
                "unit_key,"
                "unit_label,"
                "currency,"
                "scale,"
                "period_label,"
                "period_start,"
                "period_end,"
                "category,"
                "statement_type,"
                "validation_score,"
                "validation_status"
            )
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
        .eq(
            "validation_status",
            "validated",
        )
        .execute()
    )

    return (
        response.data
        or []
    )


def _load_status_counts(
    *,
    client: Client,
    user_id: str,
    document_id: str,
) -> dict[str, int]:
    response = (
        client
        .table(
            "analysis_facts"
        )
        .select(
            "validation_status"
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
        .execute()
    )

    counts = {
        "pending": 0,
        "validated": 0,
        "rejected": 0,
        "conflict": 0,
    }

    for row in (
        response.data
        or []
    ):
        status = str(
            row.get(
                "validation_status",
                "",
            )
        )

        if status in counts:
            counts[
                status
            ] += 1

    return counts

def _fact_matches_query(
    *,
    row: dict[str, Any],
    query: str,
    requested_metrics: list[str],
) -> bool:
    query_text = " ".join(
        [
            query,
            *requested_metrics,
        ]
    )

    query_tokens = (
        _significant_tokens(
            query_text
        )
    )

    if not query_tokens:
        return False

    fact_text = " ".join(
        [
            _clean_text(
                row.get(
                    "metric_key"
                )
            ),
            _clean_text(
                row.get(
                    "canonical_metric_key"
                )
            ),
            _clean_text(
                row.get(
                    "metric_label"
                )
            ),
        ]
    )

    fact_tokens = (
        _significant_tokens(
            fact_text
        )
    )

    overlap = (
        query_tokens
        .intersection(
            fact_tokens
        )
    )

    if not overlap:
        return False

    if len(query_tokens) == 1:
        return True

    coverage = (
        len(overlap)
        / len(query_tokens)
    )

    return coverage >= 0.66


def _fact_relevance_score(
    *,
    row: dict[str, Any],
    query: str,
    requested_metrics: list[str],
) -> float:
    query_text = " ".join(
        [
            query,
            *requested_metrics,
        ]
    )

    query_tokens = (
        _significant_tokens(
            query_text
        )
    )

    if not query_tokens:
        return 0.0

    fact_text = " ".join(
        [
            _clean_text(
                row.get(
                    "metric_key"
                )
            ),
            _clean_text(
                row.get(
                    "canonical_metric_key"
                )
            ),
            _clean_text(
                row.get(
                    "metric_label"
                )
            ),
            _clean_text(
                row.get(
                    "company"
                )
            ),
            _clean_text(
                row.get(
                    "category"
                )
            ),
            _clean_text(
                row.get(
                    "statement_type"
                )
            ),
            _clean_text(
                row.get(
                    "period_label"
                )
            ),
        ]
    )

    fact_tokens = (
        _significant_tokens(
            fact_text
        )
    )

    overlap = (
        query_tokens
        .intersection(
            fact_tokens
        )
    )

    if not overlap:
        return 0.0

    coverage = (
        len(overlap)
        / max(
            1,
            len(query_tokens),
        )
    )

    score = (
        float(
            len(overlap)
        )
        + coverage
    )

    normalized_query = (
        _normalize_search_text(
            query_text
        )
    )

    normalized_label = (
        _normalize_search_text(
            row.get(
                "metric_label"
            )
        )
    )

    if (
        normalized_label
        and normalized_label
        in normalized_query
    ):
        score += 3.0

    canonical_key = (
        _normalize_search_text(
            row.get(
                "canonical_metric_key"
            )
        )
    )

    if (
        canonical_key
        and canonical_key
        in normalized_query
    ):
        score += 2.0

    validation_score = float(
        row.get(
            "validation_score"
        )
        or 0.0
    )

    score += (
        max(
            0.0,
            min(
                validation_score,
                1.0,
            ),
        )
        * 0.25
    )

    return score


def _rank_relevant_rows(
    *,
    rows: list[
        dict[str, Any]
    ],
    query: str,
    requested_metrics: list[str],
) -> list[
    dict[str, Any]
]:
    ranked: list[
        tuple[
            float,
            dict[str, Any],
        ]
    ] = []

    for row in rows:
        if not _fact_matches_query(
            row=row,
            query=query,
            requested_metrics=(
                requested_metrics
            ),
        ):
            continue

        score = (
            _fact_relevance_score(
                row=row,
                query=query,
                requested_metrics=(
                    requested_metrics
                ),
            )
        )

        ranked.append(
            (
                score,
                row,
            )
        )

    ranked.sort(
        key=lambda item: (
            item[0],
            float(
                item[1].get(
                    "validation_score"
                )
                or 0.0
            ),
        ),
        reverse=True,
    )

    return [
        row
        for (
            _score,
            row,
        ) in ranked
    ]

# ============================================================
# Source ledger loading
# ============================================================


def _load_source_rows(
    *,
    client: Client,
    user_id: str,
    source_ledger_ids: list[str],
) -> dict[
    str,
    dict[str, Any],
]:
    if not source_ledger_ids:
        return {}

    response = (
        client
        .table(
            "source_ledger"
        )
        .select(
            (
                "id,"
                "document_id,"
                "chunk_id,"
                "source_title,"
                "page_number,"
                "source_snippet,"
                "retrieval_score"
            )
        )
        .eq(
            "user_id",
            user_id,
        )
        .in_(
            "id",
            source_ledger_ids,
        )
        .execute()
    )

    return {
        str(
            row["id"]
        ): row
        for row
        in (
            response.data
            or []
        )
    }


# ============================================================
# Extraction + validation
# ============================================================


def _extract_and_validate_document(
    *,
    user_id: str,
    document_id: str,
    tool_input: FinancialFactExtractorInput,
) -> tuple[
    FinancialFactToolDocumentSummary,
    list[
        dict[str, Any]
    ],
]:
    extraction = (
        extract_financial_facts(
            user_id=user_id,
            request=(
                FinancialFactExtractionRequest(
                    document_id=(
                        document_id
                    ),
                    company_hint=None,
                    requested_metrics=(
                        tool_input
                        .requested_metrics
                    ),
                    focus_queries=[
                        tool_input.query
                    ],
                    top_k_per_query=8,
                    max_sources=24,
                    max_facts=(
                        tool_input
                        .max_facts_per_document
                    ),
                    include_text_facts=False,
                    persist=True,
                )
            ),
        )
    )

    validation = (
        validate_document_facts(
            user_id=user_id,
            document_id=document_id,
            revalidate=False,
        )
    )

    summary = (
        FinancialFactToolDocumentSummary(
            document_id=document_id,
            ok=True,
            extraction_performed=True,
            extracted_count=(
                extraction
                .candidate_count
            ),
            persisted_count=(
                extraction
                .persisted_count
            ),
            processed_count=(
                validation
                .processed_count
            ),
            validated_count=(
                validation
                .validated_count
            ),
            rejected_count=(
                validation
                .rejected_count
            ),
            conflict_count=(
                validation
                .conflict_count
            ),
            warnings=[
                *extraction.warnings,
                *validation.warnings,
            ],
        )
    )

    client = (
        _get_supabase_client()
    )

    rows = (
        _load_validated_fact_rows(
            client=client,
            user_id=user_id,
            document_id=document_id,
        )
    )

    return (
        summary,
        rows,
    )


# ============================================================
# Output building
# ============================================================


def _build_output(
    *,
    client: Client,
    user_id: str,
    tool_input: FinancialFactExtractorInput,
    summaries: list[
        FinancialFactToolDocumentSummary
    ],
    fact_rows: list[
        dict[str, Any]
    ],
    warnings: list[str],
) -> FinancialFactExtractorOutput:
    ranked_rows = sorted(
        fact_rows,
        key=lambda row: (
            _fact_relevance_score(
                row=row,
                query=(
                    tool_input.query
                ),
                requested_metrics=(
                    tool_input
                    .requested_metrics
                ),
            ),
            float(
                row.get(
                    "validation_score"
                )
                or 0.0
            ),
        ),
        reverse=True,
    )

    relevant_rows = [
        row
        for row in ranked_rows
        if (
            _fact_matches_query(
                row=row,
                query=(
                    tool_input.query
                ),
                requested_metrics=(
                    tool_input
                    .requested_metrics
                ),
            )
        )
    ]

    selected_rows = (
        relevant_rows[
            :
            tool_input
            .max_returned_facts
        ]
    )

    if not selected_rows:
        warnings.append(
            (
                "No validated financial fact "
                "matched the requested metric."
            )
        )

        if selected_rows:
            warnings.append(
                (
                    "No validated fact had a "
                    "strong lexical match to the "
                    "question. Returning the "
                    "highest-confidence validated "
                    "facts for context."
                )
            )

    source_ids = list(
        {
            str(
                row[
                    "source_ledger_id"
                ]
            )
            for row
            in selected_rows
            if row.get(
                "source_ledger_id"
            )
        }
    )

    source_map = (
        _load_source_rows(
            client=client,
            user_id=user_id,
            source_ledger_ids=(
                source_ids
            ),
        )
    )

    # Start at 1001 so these citation numbers do not
    # collide with normal document_search [Source 1],
    # [Source 2], etc.
    source_number_map: dict[
        str,
        int,
    ] = {}

    sources: list[
        FinancialFactToolSource
    ] = []

    next_source_number = 1001

    for row in selected_rows:
        source_id = str(
            row.get(
                "source_ledger_id"
            )
            or ""
        )

        if (
            not source_id
            or source_id
            in source_number_map
        ):
            continue

        source = (
            source_map.get(
                source_id
            )
        )

        if source is None:
            continue

        source_number_map[
            source_id
        ] = (
            next_source_number
        )

        sources.append(
            FinancialFactToolSource(
                source_number=(
                    next_source_number
                ),
                source_ledger_id=(
                    source_id
                ),
                document_id=str(
                    source.get(
                        "document_id",
                        "",
                    )
                ),
                chunk_id=(
                    str(
                        source.get(
                            "chunk_id"
                        )
                    )
                    if source.get(
                        "chunk_id"
                    )
                    else None
                ),
                source_title=(
                    _clean_text(
                        source.get(
                            "source_title"
                        )
                    )
                    or None
                ),
                page_number=(
                    source.get(
                        "page_number"
                    )
                ),
                source_snippet=(
                    _clean_text(
                        source.get(
                            "source_snippet"
                        )
                    )
                ),
                retrieval_score=(
                    float(
                        source.get(
                            "retrieval_score"
                        )
                    )
                    if (
                        source.get(
                            "retrieval_score"
                        )
                        is not None
                    )
                    else None
                ),
            )
        )

        next_source_number += 1

    facts: list[
        FinancialFactToolFact
    ] = []

    for row in selected_rows:
        source_id = str(
            row.get(
                "source_ledger_id"
            )
            or ""
        )

        source_number = (
            source_number_map.get(
                source_id
            )
        )

        # A validated fact without a usable provenance
        # source is not safe to expose to the answer model.
        if source_number is None:
            warnings.append(
                (
                    "Skipped validated fact "
                    f"{row.get('id')} because "
                    "its source ledger entry "
                    "could not be loaded."
                )
            )

            continue

        facts.append(
            FinancialFactToolFact(
                fact_id=str(
                    row[
                        "id"
                    ]
                ),
                document_id=str(
                    row[
                        "document_id"
                    ]
                ),
                source_number=(
                    source_number
                ),
                company=(
                    _clean_text(
                        row.get(
                            "company"
                        )
                    )
                    or None
                ),
                metric_key=str(
                    row.get(
                        "metric_key",
                        "",
                    )
                ),
                canonical_metric_key=(
                    _clean_text(
                        row.get(
                            "canonical_metric_key"
                        )
                    )
                    or None
                ),
                metric_label=str(
                    row.get(
                        "metric_label",
                        "",
                    )
                ),
                value_type=str(
                    row.get(
                        "value_type",
                        "",
                    )
                ),
                numeric_value=(
                    _as_decimal(
                        row.get(
                            "numeric_value"
                        )
                    )
                ),
                normalized_numeric_value=(
                    _as_decimal(
                        row.get(
                            "normalized_numeric_value"
                        )
                    )
                ),
                text_value=(
                    _clean_text(
                        row.get(
                            "text_value"
                        )
                    )
                    or None
                ),
                raw_value=str(
                    row.get(
                        "raw_value",
                        "",
                    )
                ),
                unit_key=(
                    _clean_text(
                        row.get(
                            "unit_key"
                        )
                    )
                    or None
                ),
                unit_label=(
                    _clean_text(
                        row.get(
                            "unit_label"
                        )
                    )
                    or None
                ),
                currency=(
                    _clean_text(
                        row.get(
                            "currency"
                        )
                    )
                    or None
                ),
                scale=(
                    _clean_text(
                        row.get(
                            "scale"
                        )
                    )
                    or None
                ),
                period_label=(
                    _clean_text(
                        row.get(
                            "period_label"
                        )
                    )
                    or None
                ),
                period_start=(
                    row.get(
                        "period_start"
                    )
                ),
                period_end=(
                    row.get(
                        "period_end"
                    )
                ),
                category=(
                    _clean_text(
                        row.get(
                            "category"
                        )
                    )
                    or None
                ),
                statement_type=(
                    _clean_text(
                        row.get(
                            "statement_type"
                        )
                    )
                    or None
                ),
                validation_score=(
                    float(
                        row.get(
                            "validation_score"
                        )
                    )
                    if (
                        row.get(
                            "validation_score"
                        )
                        is not None
                    )
                    else None
                ),
            )
        )

    return (
        FinancialFactExtractorOutput(
            ok=any(
                summary.ok
                for summary
                in summaries
            ),
            query=(
                tool_input.query
            ),
            document_summaries=(
                summaries
            ),
            facts=facts,
            sources=sources,
            warnings=warnings,
        )
    )


# ============================================================
# Public tool
# ============================================================


def financial_fact_extractor_tool(
    *,
    user_id: str,
    tool_input: FinancialFactExtractorInput,
) -> FinancialFactExtractorOutput:
    client = (
        _get_supabase_client()
    )

    summaries: list[
        FinancialFactToolDocumentSummary
    ] = []

    all_rows: list[
        dict[str, Any]
    ] = []

    warnings: list[str] = []

    for document_id in (
        tool_input.document_ids
    ):
        try:
            existing_rows = (
                _load_validated_fact_rows(
                    client=client,
                    user_id=user_id,
                    document_id=(
                        document_id
                    ),
                )
            )

            relevant_existing = (
                _rank_relevant_rows(
                    rows=existing_rows,
                    query=(
                        tool_input.query
                    ),
                    requested_metrics=(
                        tool_input
                        .requested_metrics
                    ),
                )
            )

            # Reuse source-backed validated facts instead
            # of repeatedly paying for LLM extraction.
            if relevant_existing:
                counts = (
                    _load_status_counts(
                        client=client,
                        user_id=user_id,
                        document_id=(
                            document_id
                        ),
                    )
                )

                summaries.append(
                    FinancialFactToolDocumentSummary(
                        document_id=(
                            document_id
                        ),
                        ok=True,
                        extraction_performed=False,
                        extracted_count=0,
                        persisted_count=0,
                        processed_count=0,
                        validated_count=(
                            counts[
                                "validated"
                            ]
                        ),
                        rejected_count=(
                            counts[
                                "rejected"
                            ]
                        ),
                        conflict_count=(
                            counts[
                                "conflict"
                            ]
                        ),
                        warnings=[
                            (
                                "Reused existing "
                                "validated financial facts."
                            )
                        ],
                    )
                )

                all_rows.extend(
                    relevant_existing
                )

                continue

            (
                summary,
                extracted_rows,
            ) = (
                _extract_and_validate_document(
                    user_id=user_id,
                    document_id=(
                        document_id
                    ),
                    tool_input=(
                        tool_input
                    ),
                )
            )

            summaries.append(
                summary
            )

            all_rows.extend(
                extracted_rows
            )

        except Exception as error:
            error_message = (
                f"Financial fact processing "
                f"failed for {document_id}: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            summaries.append(
                FinancialFactToolDocumentSummary(
                    document_id=(
                        document_id
                    ),
                    ok=False,
                    error=(
                        error_message
                    ),
                )
            )

            warnings.append(
                error_message
            )

    return _build_output(
        client=client,
        user_id=user_id,
        tool_input=tool_input,
        summaries=summaries,
        fact_rows=all_rows,
        warnings=warnings,
    )