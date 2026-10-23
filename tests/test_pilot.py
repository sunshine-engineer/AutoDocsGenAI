# File: tests/test_pilot.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for pilot."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest

from discovery.release_snapshot import prepare_langchain_snapshot
from generation.pilot import PilotApproval, generate_pilot, outline_hash, pilot_evidence
from models.source_selection import SourceSelection


def snapshot_fixture(tmp_path, version="1.4.6"):
    """Prepare the snapshot fixture test fixture without shared production state.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
        version: Exact package release; version families are not accepted implicitly.

    Returns:
        The controlled fixture result used by this test.
    """

    def source(request):
        """Return a controlled source response without contacting external services.

        Args:
            request: Mock HTTP request or pytest request context used by this fixture.

        Returns:
            The controlled fixture result used by this test.
        """
        if request.url.host == "pypi.org":
            return httpx.Response(200, json={"info": {"version": version}})
        if request.url.host == "api.github.com":
            return httpx.Response(
                200, json={"object": {"type": "commit", "sha": "a" * 40}}
            )
        if request.url.path.endswith("pyproject.toml"):
            return httpx.Response(200, text=f'[project]\nversion = "{version}"\n')
        if request.url.path.endswith("factory.py"):
            text = 'def create_agent():\n    """Creates an agent graph that calls tools in a loop.\n\n    Args:\n        model: The model used by the agent.\n    """\n    pass\n'
        elif request.url.path.endswith("types.py"):
            text = 'class AgentMiddleware:\n    """Base middleware class for an agent with customizable behavior."""\n    def before_model(self, state, runtime):\n        """Run before the model is invoked."""\n        pass\n'
        elif request.url.path.endswith("README.md"):
            text = "## Quick Install\n\nuv add langchain\n\n## 🤔 What is this?\n\nLangChain provides pre-built agent architecture.\n\n## 📖 Documentation\n"
        else:
            text = '"""Entrypoint to building agents with LangChain."""\n'
        return httpx.Response(200, text=text)

    with httpx.Client(transport=httpx.MockTransport(source)) as client:
        path = prepare_langchain_snapshot(version, tmp_path / "sources", client)
    raw = json.loads(path.read_text())["source_selection"]
    selected = SourceSelection.model_validate(
        {**raw, "confirmed_by": "Test human", "confirmed_at": datetime.now(UTC)}
    )
    return path, PilotApproval(source=selected, outline_hash=outline_hash())


def model_client():
    """Prepare the model client test fixture without shared production state.

    Returns:
        The controlled fixture result used by this test.
    """

    def respond(request):
        """Return a controlled respond response without contacting external services.

        Args:
            request: Mock HTTP request or pytest request context used by this fixture.

        Returns:
            The controlled fixture result used by this test.
        """
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={"models": [{"name": "fixture:small", "digest": "sha256:test"}]},
            )
        payload = json.loads(request.content)
        content = json.loads(payload["messages"][1]["content"])
        chunk = content["evidence"][0]
        draft = {
            "title": content["title"],
            "abstained": False,
            "reason": "",
            "sections": [
                {
                    "heading": "Definition",
                    "claims": [
                        {
                            "text": "Fixture-supported claim for workflow testing.",
                            "citations": [
                                {
                                    "chunk_id": chunk["chunk_id"],
                                    "quote": chunk["content"][:40],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        return httpx.Response(
            200, json={"done": True, "message": {"content": json.dumps(draft)}}
        )

    return httpx.Client(transport=httpx.MockTransport(respond))


def test_approved_pilot_writes_five_review_only_records(tmp_path):
    """Verify approved pilot writes five review only records.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    snapshot, approval = snapshot_fixture(tmp_path)
    with model_client() as client:
        result = generate_pilot(
            snapshot,
            approval,
            tmp_path / "output",
            model="fixture:small",
            client=client,
        )
    assert len(result["pages"]) == 5
    assert all(
        not page["citation_issues"] and not page["abstained"]
        for page in result["pages"]
    )
    assert len(list((tmp_path / "output").rglob("*.md"))) == 5
    assert all(
        "REVIEW-ONLY DRAFT" in path.read_text()
        for path in (tmp_path / "output").rglob("*.md")
    )
    with model_client() as client, pytest.raises(ValueError, match="empty"):
        generate_pilot(
            snapshot,
            approval,
            tmp_path / "output",
            model="fixture:small",
            client=client,
        )


def test_pilot_rejects_unapproved_or_changed_outline_before_model_call(tmp_path):
    """Verify pilot rejects unapproved or changed outline before model call.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    snapshot, approval = snapshot_fixture(tmp_path)
    for changed in (
        approval.model_copy(update={"outline_hash": "f" * 64}),
        PilotApproval(
            source=approval.source.model_copy(
                update={"confirmed_by": None, "confirmed_at": None}
            ),
            outline_hash=outline_hash(),
        ),
    ):
        with (
            httpx.Client(
                transport=httpx.MockTransport(
                    lambda _: pytest.fail("model must not be called")
                )
            ) as client,
            pytest.raises(ValueError),
        ):
            generate_pilot(
                snapshot,
                changed,
                tmp_path / "output",
                model="fixture:small",
                client=client,
            )


def test_pilot_uses_function_implementation_not_empty_overload(tmp_path):
    """Verify pilot uses function implementation not empty overload.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    snapshot, _ = snapshot_fixture(tmp_path)
    pages = pilot_evidence(snapshot)
    function = next(page for page in pages if page["kind"] == "function")
    assert "Creates an agent graph" in function["evidence"][0].content
    assert "a" * 40 in function["evidence"][0].source_url


def test_pilot_can_regenerate_one_approved_topic_without_rewriting_other_pages(
    tmp_path,
):
    """Verify pilot can regenerate one approved topic without rewriting other pages.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    snapshot, approval = snapshot_fixture(tmp_path)
    with model_client() as client:
        result = generate_pilot(
            snapshot,
            approval,
            tmp_path / "single",
            model="fixture:small",
            client=client,
            topic="create_agent",
        )
    assert len(result["pages"]) == 1 and result["pages"][0]["title"] == "create_agent"
    assert len(list((tmp_path / "single").rglob("*.md"))) == 1
    with model_client() as client, pytest.raises(ValueError, match="outside"):
        generate_pilot(
            snapshot,
            approval,
            tmp_path / "invalid",
            model="fixture:small",
            client=client,
            topic="Unapproved topic",
        )


def test_pilot_keeps_parameter_hook_and_installation_evidence(tmp_path):
    """Verify pilot keeps parameter hook and installation evidence.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    snapshot, _ = snapshot_fixture(tmp_path)
    pages = pilot_evidence(snapshot)
    assert "model: The model used by the agent." in pages[1]["evidence"][0].content
    assert "def before_model(" in pages[2]["evidence"][0].content
    assert len(pages[4]["evidence"]) == 2
    assert "pyproject.toml" in pages[4]["evidence"][1].source_url
    assert 'version = "1.4.6"' in pages[4]["evidence"][1].content


def test_pilot_endpoint_precedence_uses_explicit_url_before_environment(
    tmp_path, monkeypatch
):
    """Apply service defaults without changing an explicit caller-selected endpoint.

    Args:
        tmp_path: Temporary source and output directories.
        monkeypatch: Restored environment override fixture.
    """
    snapshot, approval = snapshot_fixture(tmp_path)
    monkeypatch.setenv("AUTODOCS_OLLAMA_URL", "http://private-ollama:11434")
    for index, (explicit, expected) in enumerate(
        ((None, "private-ollama"), ("http://explicit-ollama:11434", "explicit-ollama"))
    ):
        if explicit is not None:
            monkeypatch.setenv("AUTODOCS_OLLAMA_URL", "file:///invalid-default")
        calls = []
        with model_client() as client:
            client.event_hooks["request"].append(
                lambda request: calls.append(request.url.host)
            )
            result = generate_pilot(
                snapshot,
                approval,
                tmp_path / f"endpoint-{index}",
                model="fixture:small",
                client=client,
                base_url=explicit,
            )
        assert len(result["pages"]) == 5
        assert calls and set(calls) == {expected}
