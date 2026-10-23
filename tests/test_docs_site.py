# File: tests/test_docs_site.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for docs site."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.build_docs_site import prepare, read_checked, sha256, verify_publication

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def publication_root(tmp_path):
    """Prepare the publication root test fixture without shared production state.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.

    Returns:
        The controlled fixture result used by this test.
    """
    for name in (
        "website",
        "docs/generated/langchain/1.4.6",
        "docs/ecosystem",
        "docs/quality",
    ):
        shutil.copytree(ROOT / name, tmp_path / name)
    return tmp_path


def test_fresh_checkout_inputs_build_only_selected_approved_articles(publication_root):
    """Verify fresh checkout inputs build only selected approved articles.

    Args:
        publication_root: Test fixture or parameter controlling the publication root
            scenario.
    """
    root = publication_root
    original = root / "docs/generated/langchain/1.4.6/modules/agents/README.md"
    before = sha256(original)
    (original.parent / "unapproved-draft.md").write_text("# Unapproved draft")
    work = prepare(root)
    assert len(list((work / "packages/langchain/1.4.6").rglob("*.md"))) == 6
    assert not list(work.rglob("unapproved-draft.md"))
    rendered = (work / "packages/langchain/1.4.6/modules/agents/README.md").read_text()
    assert "Reviewed by Sunny" in rendered
    assert "Editorial correction" in rendered
    assert sha256(original) == before
    assert "Dependency conflict" in (work / "compatibility.md").read_text()
    assert "langchain-community" in (work / "packages/index.md").read_text()
    assert not (root / "data").exists()


def test_changed_approved_markdown_blocks_publication(publication_root):
    """Verify changed approved markdown blocks publication.

    Args:
        publication_root: Test fixture or parameter controlling the publication root
            scenario.
    """
    path = publication_root / "docs/generated/langchain/1.4.6/guides/installation.md"
    path.write_text(path.read_text() + "\nUnreviewed addition\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        prepare(publication_root)


def test_approval_consistency_is_checked_beyond_file_hash(publication_root):
    """Verify approval consistency is checked beyond file hash.

    Args:
        publication_root: Test fixture or parameter controlling the publication root
            scenario.
    """
    root = publication_root
    path = root / "docs/generated/langchain/1.4.6/approval-record.json"
    approval = json.loads(path.read_text())
    approval["reviews"][0]["decision"] = "rejected"
    path.write_text(json.dumps(approval))
    selection = json.loads((root / "website/publication.json").read_text())
    selection["files"][path.relative_to(root).as_posix()] = sha256(path)
    with pytest.raises(ValueError, match="not matched to final approval"):
        verify_publication(root, selection)


def test_publication_rejects_path_escape(tmp_path):
    """Verify publication rejects path escape.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("not a publication input")
    with pytest.raises(ValueError, match="escapes source root"):
        read_checked(root, "../outside.md", sha256(outside))


def test_rendered_links_resolve_site_root_and_anchor(tmp_path):
    """Verify rendered links resolve site root and anchor.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    from scripts.check_docs_site_browser import check_static_links

    (tmp_path / "index.html").write_text(
        '<h1 id="home">Home</h1><a href="/other/#topic">Other</a>'
    )
    other = tmp_path / "other"
    other.mkdir()
    (other / "index.html").write_text(
        '<h1 id="topic">Topic</h1><a href="../#home">Home</a>'
    )
    assert check_static_links(tmp_path) == 2


def test_rendered_links_reject_missing_anchor(tmp_path):
    """Verify rendered links reject missing anchor.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    from scripts.check_docs_site_browser import check_static_links

    (tmp_path / "index.html").write_text('<a href="#missing">Broken</a>')
    with pytest.raises(ValueError, match="Missing reader anchor"):
        check_static_links(tmp_path)


def test_human_review_placeholders_do_not_publish_model_or_resolution_text(
    publication_root,
):
    """Verify human review placeholders do not publish model or resolution text.

    Args:
        publication_root: Test fixture or parameter controlling the publication root
            scenario.
    """
    path = publication_root / "docs/quality/human-review-queue.json"
    queue = json.loads(path.read_text())
    item = next(item for item in queue["items"] if item["surface"] == "reader")
    item["status"] = "reviewed_not_published"
    item["topic"] = "<script>unsafe()</script>"
    item["resolution"] = "SECRET_UNREVIEWED_DRAFT"
    path.write_text(json.dumps(queue))
    page = (prepare(publication_root) / "learning.md").read_text()
    assert "Human review pending" in page
    assert "SECRET_UNREVIEWED_DRAFT" not in page
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert (
        len(
            list(
                (publication_root / ".site-work/docs/packages/langchain/1.4.6").rglob(
                    "*.md"
                )
            )
        )
        == 6
    )


def test_human_review_queue_cannot_bypass_article_approval(publication_root):
    """Verify human review queue cannot bypass article approval.

    Args:
        publication_root: Test fixture or parameter controlling the publication root
            scenario.
    """
    path = publication_root / "docs/quality/human-review-queue.json"
    queue = json.loads(path.read_text())
    queue["items"][0]["status"] = "approved"
    path.write_text(json.dumps(queue))
    with pytest.raises(ValueError, match="cannot authorize publication"):
        prepare(publication_root)
