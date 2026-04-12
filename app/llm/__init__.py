from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, prompt: str, context: list[str]) -> str: ...


def get_llm_provider(provider_name: str) -> LLMProvider:
    if provider_name == "claude":
        from llm.claude_llm import ClaudeLLMProvider
        return ClaudeLLMProvider()
    elif provider_name == "openai":
        from llm.openai_llm import OpenAILLMProvider
        return OpenAILLMProvider()
    elif provider_name == "ollama":
        from llm.ollama_llm import OllamaLLMProvider
        return OllamaLLMProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
