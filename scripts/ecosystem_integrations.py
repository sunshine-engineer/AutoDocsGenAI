"""Offline integration contracts; provider requests are deliberately blocked."""

from __future__ import annotations

import importlib.metadata
import json
import socket
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import patch


def run() -> dict:
    ChatAnthropic = import_module("langchain_anthropic").ChatAnthropic
    from langchain_core.embeddings import DeterministicFakeEmbedding
    from langchain_core.tools import tool

    ChatGroq = import_module("langchain_groq").ChatGroq
    ChatOllama = import_module("langchain_ollama").ChatOllama
    ChatOpenAI = import_module("langchain_openai").ChatOpenAI
    QdrantVectorStore = import_module("langchain_qdrant").QdrantVectorStore
    RecursiveCharacterTextSplitter = import_module(
        "langchain_text_splitters"
    ).RecursiveCharacterTextSplitter

    @tool
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    checks = []
    with patch.object(
        socket.socket,
        "connect",
        side_effect=RuntimeError("network blocked by offline contract"),
    ):
        for name, factory in [
            (
                "openai",
                lambda: ChatOpenAI(model="test-model", api_key="offline-placeholder"),
            ),
            (
                "anthropic",
                lambda: ChatAnthropic(
                    model_name="test-model", api_key="offline-placeholder"
                ),
            ),
            (
                "groq",
                lambda: ChatGroq(model="test-model", api_key="offline-placeholder"),
            ),
            ("ollama", lambda: ChatOllama(model="qwen3:1.7b")),
        ]:
            model = factory()
            bound = model.bind_tools([add])
            assert bound is not None
            checks.append(
                {
                    "name": name,
                    "status": "passed",
                    "scope": "Construct client and bind tool schema only; provider inference NOT tested",
                }
            )
        splitter = RecursiveCharacterTextSplitter(chunk_size=24, chunk_overlap=4)
        chunks = splitter.split_text(
            "First documentation sentence. Second documentation sentence. Third sentence."
        )
        assert len(chunks) > 1 and all(len(chunk) <= 24 for chunk in chunks)
        checks.append(
            {
                "name": "text_splitter",
                "status": "passed",
                "scope": "Executed local chunking and checked size budget",
            }
        )
        store = QdrantVectorStore.from_texts(
            ["LangGraph uses graph state.", "LangChain composes runnables."],
            embedding=DeterministicFakeEmbedding(size=16),
            location=":memory:",
            collection_name="offline-reference",
        )
        hits = store.similarity_search("LangGraph uses graph state.", k=1)
        assert hits[0].page_content == "LangGraph uses graph state."
        store.client.close()
        checks.append(
            {
                "name": "qdrant",
                "status": "passed",
                "scope": "Executed in-memory insert and similarity retrieval with deterministic fake embeddings",
            }
        )
    return {
        "checks": checks,
        "distributions": {
            dist.metadata["Name"]: dist.version
            for dist in importlib.metadata.distributions()
        },
        "network": "socket.connect blocked throughout checks",
        "limits": "No hosted inference, production vector server, credentials, GPU embeddings, or provider response validation.",
    }


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(run(), indent=2), encoding="utf-8")
