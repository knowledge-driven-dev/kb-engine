"""Application settings using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # General
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "kb_engine"
    postgres_password: str = "changeme"
    postgres_db: str = "kb_engine"
    database_url: str | None = None

    # Vector Store
    vector_store: str = "qdrant"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: str | None = None
    qdrant_collection: str = "kb_engine_embeddings"

    # Weaviate (alternative)
    weaviate_host: str = "localhost"
    weaviate_api_key: str | None = None

    # Graph Store
    graph_store: str = "neo4j"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    # Nebula (alternative)
    nebula_host: str = "localhost"
    nebula_port: int = 9669

    # OpenAI
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4-turbo-preview"

    # Chunking
    chunk_size_min: int = 100
    chunk_size_target: int = 512
    chunk_size_max: int = 1024
    chunk_overlap: int = 50

    # Extraction
    extraction_use_llm: bool = True
    extraction_confidence_threshold: float = 0.7

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Build database URL if not provided
        if self.database_url is None:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
