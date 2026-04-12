from openai import OpenAI

from config import settings

RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about an organization. "
    "Use ONLY the provided context to answer. If the context does not contain "
    "enough information, say so. Be specific and cite which documents or people "
    "informed your answer."
)


class OpenAILLMProvider:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate(self, prompt: str, context: list[str]) -> str:
        context_block = "\n\n---\n\n".join(context)
        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{context_block}\n\n"
                        f"Question: {prompt}"
                    ),
                },
            ],
        )
        return response.choices[0].message.content
