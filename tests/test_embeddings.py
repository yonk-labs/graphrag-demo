import pytest
from embeddings import get_embedding_provider


def test_local_provider_returns_correct_dimensions():
    provider = get_embedding_provider("local")
    result = provider.embed("hello world")
    assert len(result) == 384
    assert all(isinstance(x, float) for x in result)


def test_local_provider_batch():
    provider = get_embedding_provider("local")
    results = provider.embed_batch(["hello", "world", "test"])
    assert len(results) == 3
    assert all(len(r) == 384 for r in results)


def test_similar_texts_have_higher_similarity():
    provider = get_embedding_provider("local")
    emb_a = provider.embed("database performance optimization")
    emb_b = provider.embed("improving database query speed")
    emb_c = provider.embed("chocolate cake recipe")

    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(x ** 2 for x in b) ** 0.5
        return dot / (norm_a * norm_b)

    sim_ab = cosine_sim(emb_a, emb_b)
    sim_ac = cosine_sim(emb_a, emb_c)
    assert sim_ab > sim_ac


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        get_embedding_provider("nonexistent")
