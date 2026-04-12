from sentence_transformers import SentenceTransformer

from config import settings

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


class LocalEmbeddingProvider:
    def embed(self, text: str) -> list[float]:
        model = _get_model()
        return model.encode(text).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = _get_model()
        return model.encode(texts).tolist()
