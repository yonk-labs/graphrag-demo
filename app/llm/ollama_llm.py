import httpx

from config import settings

RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about an organization. "
    "Use ONLY the provided context to answer. If the context does not contain "
    "enough information, say so. Be specific and cite which documents or people "
    "informed your answer."
)


class OllamaLLMProvider:
    def __init__(self):
        self.base_url = settings.ollama_base_url

    def generate(self, prompt: str, context: list[str]) -> str:
        context_block = "\n\n---\n\n".join(context)
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": "llama3.2",
                "stream": False,
                "messages": [
                    {"role": "system", "content": RAG_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Context:\n{context_block}\n\n"
                            f"Question: {prompt}"
                        ),
                    },
                ],
            },
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
