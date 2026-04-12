import pytest
from llm import get_llm_provider


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_provider("nonexistent")


def test_claude_provider_instantiates():
    provider = get_llm_provider("claude")
    assert hasattr(provider, "generate")


def test_openai_provider_instantiates():
    provider = get_llm_provider("openai")
    assert hasattr(provider, "generate")


def test_ollama_provider_instantiates():
    provider = get_llm_provider("ollama")
    assert hasattr(provider, "generate")
