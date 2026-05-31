import json
from pathlib import Path

import httpx
import numpy as np

from app.config import settings

DATA_PATH = Path(__file__).parent.parent / "data" / "faq.jsonl"


class RAGService:
    def __init__(self):
        self.embedder_name = settings.embedder_model
        self.llm_model = settings.llm_model
        self.docs: list[dict] = []
        self.embeddings: np.ndarray | None = None
        self.ready = False

        # Визначаємо base_url і auth header залежно від провайдера
        if settings.ollama_base_url:
            self._base_url = f"{settings.ollama_base_url}/v1"
            self._auth_header = "Bearer ollama"   # Ollama не перевіряє токен
        else:
            self._base_url = "https://api.openai.com/v1"
            self._auth_header = f"Bearer {settings.openai_api_key}"

    @property
    def docs_count(self) -> int:
        return len(self.docs)

    async def _embed(self, texts: list[str]) -> np.ndarray:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": self._auth_header},
                json={"model": self.embedder_name, "input": texts},
            )
            r.raise_for_status()
            vectors = [item["embedding"] for item in r.json()["data"]]
        arr = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.where(norms == 0, 1, norms)

    async def load(self):
        self.docs = [
            json.loads(line)
            for line in DATA_PATH.read_text().splitlines()
            if line.strip()
        ]
        texts = [f"{d['question']} {d['answer']}" for d in self.docs]
        self.embeddings = await self._embed(texts)
        self.ready = True

    async def _retrieve(self, question: str, top_k: int = 3) -> list[dict]:
        q_emb = (await self._embed([question]))[0]
        scores = self.embeddings @ q_emb
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [{"score": float(scores[i]), **self.docs[i]} for i in top_idx]

    async def answer(self, question: str) -> tuple[str, list[dict]]:
        sources = await self._retrieve(question)
        context = "\n\n".join(
            f"Q: {s['question']}\nA: {s['answer']}" for s in sources
        )
        prompt = (
            "Answer the user question using only the context below. "
            "If the answer is not in the context, say you don't know.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}"
        )

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": self._auth_header},
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
            )
            r.raise_for_status()
            answer = r.json()["choices"][0]["message"]["content"]

        return answer, sources