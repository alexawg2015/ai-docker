from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.rag import RAGService

rag = RAGService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rag.load()
    yield


app = FastAPI(title="rag-boilerplate", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str


@app.get("/health")
async def health():
    return {"status": "ok" if rag.ready else "loading"}


@app.get("/metadata")
async def metadata():
    return {
        "embedder": rag.embedder_name,
        "llm": rag.llm_model,
        "docs_count": rag.docs_count,
        "ready": rag.ready,
    }


@app.post("/ask")
async def ask(req: AskRequest):
    if not rag.ready:
        raise HTTPException(status_code=503, detail="model still loading")
    answer, sources = await rag.answer(req.question)
    return {"answer": answer, "sources": sources}

# test cache
# test cache 2
# test cache 3