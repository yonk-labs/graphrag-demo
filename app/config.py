from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://graphrag:graphrag@localhost:5432/graphrag"
    llm_provider: str = "claude"
    embedding_provider: str = "local"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    vector_top_k: int = 10
    graph_max_hops: int = 2


settings = Settings()
