from app.schemas.web import (
    WebResearchInput,
    WebResearchOutput,
)

from app.services.serper_search import (
    search_web_with_serper,
)


def web_research_tool(
    *,
    user_id: str,
    tool_input: WebResearchInput,
) -> WebResearchOutput:
    # user_id is intentionally accepted now because
    # 3H-D will use it for source-ledger persistence.
    #
    # 3H-B itself does not persist anything yet.
    _ = user_id

    return search_web_with_serper(
        tool_input
    )