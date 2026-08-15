from app.core.config import settings

from app.schemas.web import (
    WebResearchInput,
    WebResearchOutput,
)

from app.services.serper_search import (
    search_web_with_serper,
)

from app.services.web_source_fetcher import (
    fetch_candidate_sources,
)

from app.services.web_source_ledger import (
    persist_web_citation_sources,
)


def web_research_tool(
    *,
    user_id: str,
    tool_input: WebResearchInput,
) -> WebResearchOutput:
    # -----------------------------------------------------
    # Phase 3H-B
    # Search discovery
    # -----------------------------------------------------

    search_output = (
        search_web_with_serper(
            tool_input
        )
    )

    if not (
        search_output.candidates
    ):
        return search_output

    # -----------------------------------------------------
    # Phase 3H-C
    # Fetch actual source pages / PDFs
    # -----------------------------------------------------

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
    ) = fetch_candidate_sources(
        query=(
            tool_input.query
        ),
        candidates=(
            search_output.candidates
        ),
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

    # -----------------------------------------------------
    # Phase 3H-D
    # Persist actual evidence into source_ledger
    # -----------------------------------------------------

    citation_sources = []

    if evidence_source_count > 0:
        try:
            citation_sources = (
                persist_web_citation_sources(
                    user_id=user_id,
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
        evidence_source_count > 0
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

    return (
        search_output
        .model_copy(
            update={
                "fetched_source_count":
                    len(
                        fetched_sources
                    ),

                "evidence_source_count":
                    evidence_source_count,

                "evidence_ready":
                    (
                        evidence_source_count
                        > 0
                    ),

                "fetched_sources":
                    fetched_sources,

                "fetch_failures":
                    fetch_failures,

                "citation_ready":
                    citation_ready,

                "citation_source_count":
                    len(
                        citation_sources
                    ),

                "citation_sources":
                    citation_sources,

                "warnings":
                    warnings,
            }
        )
    )