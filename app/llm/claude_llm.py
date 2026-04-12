import anthropic

from config import settings

RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about an organization. "
    "Use ONLY the provided context to answer. If the context does not contain "
    "enough information, say so. Be specific and cite which documents or people "
    "informed your answer."
)


class ClaudeLLMProvider:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate(self, prompt: str, context: list[str]) -> str:
        context_block = "\n\n---\n\n".join(context)
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=RAG_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{context_block}\n\n"
                        f"Question: {prompt}"
                    ),
                }
            ],
        )
        return message.content[0].text
