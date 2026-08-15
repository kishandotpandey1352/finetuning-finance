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


def web_research_tool(
    *,
    user_id: str,
    tool_input: WebResearchInput,
) -> WebResearchOutput:
    # Phase 3H-D will use user_id for
    # source-ledger persistence.
    _ = user_id

    search_output = (
        search_web_with_serper(
            tool_input
        )
    )

    if not search_output.candidates:
        return search_output

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
            search_output.model_copy(
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
        query=tool_input.query,
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

    elif evidence_source_count == 0:
        warnings.append(
            (
                "Web pages were fetched, "
                "but no relevant evidence "
                "passages were found."
            )
        )

    return (
        search_output.model_copy(
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

                "warnings":
                    warnings,
            }
        )
    )