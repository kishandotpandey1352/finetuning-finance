try:
    from pydantic_settings import (
        BaseSettings,
        SettingsConfigDict,
    )
except ImportError:  # pragma: no cover
    from pydantic import BaseSettings  # type: ignore

    SettingsConfigDict = dict


class Settings(
    BaseSettings,
):
    openai_api_key: str | None = None

    agent_model: str = (
        "gpt-4.1-mini"
    )

    # -----------------------------------------------------
    # Phase 3D - document search
    # -----------------------------------------------------

    document_embedding_model: str = (
        "text-embedding-3-small"
    )

    document_retrieval_top_k: int = 6

    document_min_similarity: float = (
        0.30
    )

    supabase_url: str | None = None

    supabase_service_role_key: (
        str | None
    ) = None

    # -----------------------------------------------------
    # Phase 3G-B - financial fact extraction
    # -----------------------------------------------------

    # If unset, the extractor falls back to agent_model.
    fact_extraction_model: str | None = (
        None
    )

    # Financial tables/KPI chunks sometimes have weaker
    # semantic similarity than narrative paragraphs.
    fact_extraction_min_similarity: float = (
        0.20
    )

    # Process several sources per structured-output call
    # rather than sending the entire document at once.
    fact_extraction_batch_sources: int = 6

    # Safety guard for context construction.
    fact_extraction_max_context_chars: int = (
        48000
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # Serper API settings for web search fallback.
    serper_api_key: str | None = None

    serper_search_enabled: bool = True

    serper_search_url: str = (
        "https://google.serper.dev/search"
    )

    serper_timeout_seconds: float = 12.0

    serper_max_results: int = 8

    serper_language: str = "en"


settings = Settings()