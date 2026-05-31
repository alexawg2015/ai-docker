import os

import pytest
from fastapi.testclient import TestClient

from app.main import app, rag

requires_keys = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


@requires_keys
def test_health_when_loaded():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@requires_keys
def test_metadata():
    with TestClient(app) as client:
        r = client.get("/metadata")
        assert r.status_code == 200
        body = r.json()
        assert body["docs_count"] == 20
        assert body["ready"] is True


@requires_keys
@pytest.mark.asyncio
async def test_retrieve_returns_relevant_doc():
    with TestClient(app):
        sources = await rag._retrieve("What is a vector database?", top_k=1)
        assert sources[0]["question"] == "What is a vector database?"
