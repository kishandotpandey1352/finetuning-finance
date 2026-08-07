try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover
    from pydantic import BaseSettings  # type: ignore

    SettingsConfigDict = dict


class Settings(BaseSettings):
    openai_api_key: str | None = None
    agent_model: str = "gpt-4.1-mini"

    # Phase 3D document search
    document_embedding_model: str = "text-embedding-3-small"
    document_retrieval_top_k: int = 6
    document_min_similarity: float = 0.30

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()