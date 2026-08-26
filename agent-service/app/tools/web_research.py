from __future__ import annotations

from app.core.config import (
    settings,
)

from app.schemas.web import (
    WebResearchInput,
    WebResearchOutput,
)

from app.services.fact_validator import (
    validate_web_facts,
)

from app.services.serper_search import (
    search_web_with_serper,
)

from app.services.web_fact_extractor import (
    extract_web_financial_facts,
    load_validated_web_facts,
)

from app.services.web_request_guard import (
    guard_web_research_request,
)

from app.services.web_source_fetcher import (
    fetch_candidate_sources,
)

from app.services.web_source_ledger import (
    persist_web_citation_sources,
)

from app.services.web_usage_limiter import (
    check_web_usage_limit,
)


# =========================================================
# Web research tool
# =========================================================


def web_research_tool(
    *,
    user_id: str,
    tool_input: WebResearchInput,
) -> WebResearchOutput:
    """
    Execute the complete web-research pipeline.

    Phase 3H-B:
        Serper search discovery.

    Phase 3H-C:
        Safe source fetching and evidence extraction.

    Phase 3H-D:
        Persist verified evidence into source_ledger
        and create request-scoped [Web Source N]
        citations.

    Phase 3H-E:
        Optionally extract structured financial facts,
        persist them as pending analysis_facts,
        deterministically validate them, and expose only
        validated facts.

    Phase 3H-F-B:
        Apply product-level query, domain, result-count,
        and per-user hourly search limits before Serper is
        called.
    """

    # =====================================================
    # Phase 3H-F-B
    # Product-level web request controls
    # =====================================================

    guarded_request = (
        guard_web_research_request(
            tool_input
        )
    )

    # -----------------------------------------------------
    # Construct a sanitized WebResearchInput.
    #
    # IMPORTANT:
    #
    # The original implementation created guarded_request
    # but still sent the original tool_input to Serper.
    #
    # That meant:
    #
    #   max_results
    #   trusted_domains
    #   cleaned query
    #
    # were not actually enforced at the provider boundary.
    #
    # From this point onward, provider-facing search uses
    # guarded_tool_input.
    # -----------------------------------------------------

    guarded_tool_input = (
        tool_input.model_copy(
            update={
                "query":
                    guarded_request.query,

                "trusted_domains":
                    guarded_request
                    .trusted_domains,

                "max_results":
                    guarded_request
                    .max_results,
            }
        )
    )

    # -----------------------------------------------------
    # Reserve one hourly web-search allowance.
    #
    # In 3H-F-C caching, this will move AFTER cache lookup,
    # so cache hits do not consume search quota.
    #
    # For 3H-F-B, no cache exists yet, so every real
    # web_research invocation reaching this point consumes
    # one allowance.
    # -----------------------------------------------------

    check_web_usage_limit(
        user_id=user_id,
    )

    # =====================================================
    # Phase 3H-B
    # Search discovery
    # =====================================================

    search_output = (
        search_web_with_serper(
            guarded_tool_input
        )
    )

    # -----------------------------------------------------
    # Nothing discovered.
    #
    # There is nothing further to:
    #
    #   fetch
    #   persist
    #   cite
    #   structure
    # -----------------------------------------------------

    if not (
        search_output.candidates
    ):
        return search_output

    # =====================================================
    # Phase 3H-C
    # Fetch actual source pages / PDFs
    # =====================================================

    if not (
        settings.web_fetch_enabled
    ):
        warnings = list(
            search_output.warnings
        )

        warnings.append(
            (
                "Web search succeeded, but "
                "source fetching is disabled."
            )
        )

        return (
            search_output
            .model_copy(
                update={
                    "warnings":
                        warnings,
                }
            )
        )

    (
        fetched_sources,
        fetch_failures,
    ) = (
        fetch_candidate_sources(
            query=(
                guarded_request.query
            ),

            candidates=(
                search_output.candidates
            ),
        )
    )

    evidence_source_count = sum(
        1
        for source
        in fetched_sources
        if source.evidence_passages
    )

    warnings = list(
        search_output.warnings
    )

    if not fetched_sources:
        warnings.append(
            (
                "Search candidates were "
                "found, but no candidate "
                "source could be fetched "
                "successfully."
            )
        )

    elif (
        evidence_source_count
        == 0
    ):
        warnings.append(
            (
                "Web pages were fetched, "
                "but no relevant evidence "
                "passages were found."
            )
        )

    # =====================================================
    # Phase 3H-D
    # Persist verified evidence into source_ledger
    # =====================================================

    citation_sources = []

    if (
        evidence_source_count
        > 0
    ):
        try:
            citation_sources = (
                persist_web_citation_sources(
                    user_id=(
                        user_id
                    ),

                    fetched_sources=(
                        fetched_sources
                    ),

                    first_source_number=(
                        2001
                    ),
                )
            )

        except Exception as error:
            warnings.append(
                (
                    "Web evidence was fetched "
                    "but could not be persisted "
                    "to source_ledger: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

    citation_ready = bool(
        citation_sources
    )

    if (
        evidence_source_count
        > 0
        and not citation_ready
    ):
        warnings.append(
            (
                "Fetched web evidence is not "
                "citation-ready because no "
                "persistent source ledger "
                "records were created."
            )
        )

    # =====================================================
    # Phase 3H-E
    # Structured web financial facts
    # =====================================================

    structured_fact_attempted = False

    structured_fact_candidate_count = 0

    structured_fact_persisted_count = 0

    structured_fact_validated_count = 0

    structured_fact_rejected_count = 0

    structured_fact_conflict_count = 0

    validated_facts = []

    # -----------------------------------------------------
    # Structured extraction is allowed only when:
    #
    # 1. Evidence is citation-ready.
    # 2. Planner requested structured financial facts.
    # 3. Web fact extraction is enabled.
    #
    # This guarantees raw Serper snippets and unpersisted
    # fetched content cannot become usable analysis_facts.
    # -----------------------------------------------------

    if (
        citation_ready
        and (
            guarded_tool_input
            .extract_structured_facts
        )
        and (
            settings
            .web_fact_extraction_enabled
        )
    ):
        structured_fact_attempted = True

        try:
            # =============================================
            # 3H-E-1
            # Extract candidates only from persisted,
            # citation-ready evidence.
            # =============================================

            extraction = (
                extract_web_financial_facts(
                    user_id=(
                        user_id
                    ),

                    question=(
                        guarded_request.query
                    ),

                    citation_sources=(
                        citation_sources
                    ),
                )
            )

            structured_fact_candidate_count = (
                extraction
                .candidate_count
            )

            structured_fact_persisted_count = (
                extraction
                .persisted_count
            )

            warnings.extend(
                extraction.warnings
            )

            # =============================================
            # 3H-E-2
            # Validate only facts that were actually
            # persisted.
            # =============================================

            if extraction.fact_ids:
                validation = (
                    validate_web_facts(
                        user_id=(
                            user_id
                        ),

                        fact_ids=(
                            extraction
                            .fact_ids
                        ),
                    )
                )

                structured_fact_validated_count = (
                    validation
                    .validated_count
                )

                structured_fact_rejected_count = (
                    validation
                    .rejected_count
                )

                structured_fact_conflict_count = (
                    validation
                    .conflict_count
                )

                warnings.extend(
                    validation.warnings
                )

                # =========================================
                # 3H-E-3
                # Expose only validated persisted facts.
                #
                # pending / rejected / conflict facts stay
                # unavailable to downstream calculations
                # and answer generation.
                # =========================================

                validated_facts = (
                    load_validated_web_facts(
                        user_id=(
                            user_id
                        ),

                        fact_ids=(
                            extraction
                            .fact_ids
                        ),

                        citation_sources=(
                            citation_sources
                        ),
                    )
                )

            elif (
                extraction.attempted
                and (
                    extraction
                    .candidate_count
                    == 0
                )
            ):
                warnings.append(
                    (
                        "Structured web fact "
                        "extraction completed but "
                        "returned no financial "
                        "fact candidates."
                    )
                )

        except Exception as error:
            # -------------------------------------------------
            # Structured fact failure must never destroy
            # already verified/citation-ready web evidence.
            #
            # Narrative evidence remains usable.
            # -------------------------------------------------

            warnings.append(
                (
                    "Structured web fact "
                    "processing failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

    structured_fact_ready = bool(
        validated_facts
    )

    # =====================================================
    # Final WebResearchOutput
    # =====================================================

    return (
        search_output
        .model_copy(
            update={
                # =========================================
                # Phase 3H-C
                # =========================================

                "fetched_source_count":
                    len(
                        fetched_sources
                    ),

                "evidence_source_count":
                    (
                        evidence_source_count
                    ),

                "evidence_ready":
                    (
                        evidence_source_count
                        > 0
                    ),

                "fetched_sources":
                    fetched_sources,

                "fetch_failures":
                    fetch_failures,

                # =========================================
                # Phase 3H-D
                # =========================================

                "citation_ready":
                    citation_ready,

                "citation_source_count":
                    len(
                        citation_sources
                    ),

                "citation_sources":
                    citation_sources,

                # =========================================
                # Phase 3H-E
                # =========================================

                "structured_fact_attempted":
                    (
                        structured_fact_attempted
                    ),

                "structured_fact_ready":
                    (
                        structured_fact_ready
                    ),

                "structured_fact_candidate_count":
                    (
                        structured_fact_candidate_count
                    ),

                "structured_fact_persisted_count":
                    (
                        structured_fact_persisted_count
                    ),

                "structured_fact_validated_count":
                    (
                        structured_fact_validated_count
                    ),

                "structured_fact_rejected_count":
                    (
                        structured_fact_rejected_count
                    ),

                "structured_fact_conflict_count":
                    (
                        structured_fact_conflict_count
                    ),

                "validated_facts":
                    validated_facts,

                # =========================================
                # Combined warnings
                # =========================================

                "warnings":
                    warnings,
            }
        )
    )