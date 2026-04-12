from openai import OpenAI

from config import settings


class OpenAIEmbeddingProvider:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-3-small"

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(input=[text], model=self.model)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]
