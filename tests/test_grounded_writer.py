from __future__ import annotations

import json

import httpx
import pytest

from generation.contracts import EvidenceChunk, PageDraft, validate_citations
from generation.ollama import write_page


def evidence(**updates):
    return EvidenceChunk.model_validate(
        {
            "chunk_id": "fixture-1",
            "package": "fixture",
            "version": "1.0",
            "source_url": "https://example.com/fixture",
            "content": "A Widget stores a single integer value and exposes that value through the read method.",
            **updates,
        }
    )


def draft(**updates):
    return PageDraft.model_validate(
        {
            "title": "Widget",
            "abstained": False,
            "reason": "",
            "sections": [
                {
                    "heading": "Definition",
                    "claims": [
                        {
                            "text": "Widget stores one integer.",
                            "citations": [
                                {
                                    "chunk_id": "fixture-1",
                                    "quote": "A Widget stores a single integer value",
                                }
                            ],
                        }
                    ],
                }
            ],
            **updates,
        }
    )


def test_citation_integrity_and_abstention():
    assert validate_citations(draft(), [evidence()], "fixture", "1.0") == []
    abstained = draft(
        abstained=True, reason="Insufficient source evidence", sections=[]
    )
    assert validate_citations(abstained, [evidence()], "fixture", "1.0") == []
    assert validate_citations(draft(sections=[]), [evidence()], "fixture", "1.0")
    assert validate_citations(draft(abstained=True), [evidence()], "fixture", "1.0")


@pytest.mark.parametrize("change", ["unknown", "wrong_quote", "wrong_version"])
def test_citations_reject_unknown_unmatched_and_wrong_version(change):
    page = draft().model_dump()
    chunks = [evidence()]
    if change == "unknown":
        page["sections"][0]["claims"][0]["citations"][0]["chunk_id"] = "unknown"
    elif change == "wrong_quote":
        page["sections"][0]["claims"][0]["citations"][0][
            "quote"
        ] = "An invented quotation not found in the source."
    else:
        chunks = [evidence(version="2.0")]
    assert validate_citations(PageDraft.model_validate(page), chunks, "fixture", "1.0")


def test_claims_without_citations_fail_schema_validation():
    payload = draft().model_dump()
    payload["sections"][0]["claims"][0]["citations"] = []
    with pytest.raises(ValueError):
        PageDraft.model_validate(payload)


def test_ollama_request_is_bounded_structured_and_records_digest():
    seen = []

    def handle(request):
        seen.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={"models": [{"name": "test:small", "digest": "sha256:fixture"}]},
            )
        payload = json.loads(request.content)
        assert payload["stream"] is False and payload["think"] is False
        assert payload["options"]["num_predict"] == 1200
        assert payload["format"]["type"] == "object"
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "stop",
                "message": {"content": draft().model_dump_json()},
                "prompt_eval_count": 100,
                "eval_count": 50,
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = write_page(
            client,
            base_url="http://localhost:11434",
            model="test:small",
            package="fixture",
            version="1.0",
            title="Widget",
            evidence=[evidence()],
        )
    assert result.model_digest == "sha256:fixture"
    assert result.prompt_tokens == 100 and result.output_tokens == 50
    assert result.citation_issues == ()
    assert len(seen) == 2


def test_writing_rejects_mixed_versions_before_network():
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: pytest.fail("no request expected"))
        ) as client,
        pytest.raises(ValueError, match="match"),
    ):
        write_page(
            client,
            base_url="http://localhost:11434",
            model="test",
            package="fixture",
            version="1.0",
            title="Widget",
            evidence=[evidence(version="2.0")],
        )
