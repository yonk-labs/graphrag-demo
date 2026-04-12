from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


def get_embedding_provider(provider_name: str) -> EmbeddingProvider:
    if provider_name == "local":
        from embeddings.local import LocalEmbeddingProvider
        return LocalEmbeddingProvider()
    elif provider_name == "openai":
        from embeddings.openai_embed import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider()
    else:
        raise ValueError(f"Unknown embedding provider: {provider_name}")
