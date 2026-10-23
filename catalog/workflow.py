# File: catalog/workflow.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Lock catalog rows and enforce explicit submit, approve and reject transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from catalog.artifacts import (
    ArtifactResult,
    load_catalog_view,
    verify_artifacts,
    write_artifacts,
)
from catalog.repository import CatalogPersistenceError
from database.models import DocumentationVersionRecord, TopicCatalogRecord, TopicRecord

DEFAULT_ARTIFACT_ROOT = Path("data/catalogs")
TRANSITIONS = {
    ("draft", "submit"): "awaiting_approval",
    ("awaiting_approval", "approve"): "approved",
    ("draft", "reject"): "rejected",
    ("awaiting_approval", "reject"): "rejected",
}


@dataclass(frozen=True)
class ReviewResult:
    """Catalog review outcome with refreshed artifact state.

    Attributes:
        catalog_id (str): Persisted catalog UUID or its string representation.
        previous_status (str): Previous status.
        status (str): Status.
        topic_count (int): Topic count.
        reviewer (str | None): Human reviewer identifier supplied by the operator.
        approved_at (str | None): Approved at.
        feedback (str | None): Human review feedback; required for rejection where
            applicable.
        no_op (bool): No op.
        artifacts (ArtifactResult): Artifacts.
    """

    catalog_id: str
    previous_status: str
    status: str
    topic_count: int
    reviewer: str | None
    approved_at: str | None
    feedback: str | None
    no_op: bool
    artifacts: ArtifactResult


def lock_catalog(session: Session, catalog_id: UUID | str) -> TopicCatalogRecord:
    """Lock a catalog and its documentation version for consistent review transitions.

    Args:
        session: Caller-owned SQLAlchemy session; the caller controls commit/rollback.
        catalog_id: Persisted catalog UUID or its string representation.

    Returns:
        Locked catalog record ready for the caller review transaction.

    Raises:
        CatalogPersistenceError: catalog does not exist; catalog no longer exists.
    """
    identifier = UUID(str(catalog_id))
    version_id = session.scalar(
        select(TopicCatalogRecord.documentation_version_id).where(
            TopicCatalogRecord.id == identifier
        )
    )
    if version_id is None:
        raise CatalogPersistenceError("catalog does not exist")
    # Match build lock order, serializing competing approvals for a version.
    session.execute(
        select(DocumentationVersionRecord.id)
        .where(DocumentationVersionRecord.id == version_id)
        .with_for_update()
    )
    catalog = session.scalar(
        select(TopicCatalogRecord)
        .where(TopicCatalogRecord.id == identifier)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if catalog is None:
        raise CatalogPersistenceError("catalog no longer exists")
    return catalog


def inspect_catalog(
    session_factory: sessionmaker[Session],
    catalog_id: UUID | str,
    *,
    root: Path = DEFAULT_ARTIFACT_ROOT,
    repair: bool = False,
) -> tuple[dict[str, Any], ArtifactResult | None]:
    """Load canonical catalog state and optionally repair missing artifact files.

    Args:
        session_factory: SQLAlchemy session factory used for transactional work.
        catalog_id: Persisted catalog UUID or its string representation.
        root: Root directory delimiting artifact or publication access.
        repair: Whether canonical artifacts may be regenerated from stored lineage.

    Returns:
        Canonical catalog view and optional repair outcome.
    """
    with session_factory.begin() as session:
        lock_catalog(session, catalog_id)
        view = load_catalog_view(session, catalog_id)
        artifacts = write_artifacts(view, root) if repair else None
    return view, artifacts


def review_text(
    value: str | None, name: str, limit: int, *, required: bool
) -> str | None:
    """Validate bounded reviewer or feedback text and normalize optional blanks.

    Args:
        value: Value to normalize or validate under this function contract.
        name: Field, distribution or check name for this operation.
        limit: Maximum requested records or text size, as used by this operation.
        required: Whether blank input must be rejected.

    Returns:
        Normalized text, or None for an optional blank value.
    """
    cleaned = value.strip() if value is not None else ""
    if required and not cleaned:
        raise CatalogPersistenceError(f"{name} is required")
    if len(cleaned) > limit or any(
        ord(char) < 32 or ord(char) == 127 for char in cleaned
    ):
        raise CatalogPersistenceError(
            f"{name} must be at most {limit} characters without control characters"
        )
    return cleaned or None


def review_catalog(
    session_factory: sessionmaker[Session],
    catalog_id: UUID | str,
    decision: str,
    *,
    reviewer: str | None = None,
    feedback: str | None = None,
    root: Path = DEFAULT_ARTIFACT_ROOT,
) -> ReviewResult:
    """Apply an atomic submit, approve or reject transition and refresh artifacts.

    Args:
        session_factory: SQLAlchemy session factory used for transactional work.
        catalog_id: Persisted catalog UUID or its string representation.
        decision: Explicit review transition, restricted by the workflow.
        reviewer: Human reviewer identifier supplied by the operator.
        feedback: Human review feedback; required for rejection where applicable.
        root: Root directory delimiting artifact or publication access.

    Returns:
        Review transition result and artifact-write outcome.

    Raises:
        CatalogPersistenceError: decision must be submit, approve, or reject; reviewer
            is only accepted for approval; feedback is only accepted for rejection;
            catalog has blocking evidence or hierarchy findings; catalog and topic
            review states disagree; review conflicts with an existing approved catalog
            or database constraint.
    """
    if decision not in {"submit", "approve", "reject"}:
        raise CatalogPersistenceError("decision must be submit, approve, or reject")
    reviewer = review_text(reviewer, "reviewer", 200, required=decision == "approve")
    feedback = review_text(feedback, "feedback", 4000, required=decision == "reject")
    if reviewer is not None and decision != "approve":
        raise CatalogPersistenceError("reviewer is only accepted for approval")
    if feedback is not None and decision != "reject":
        raise CatalogPersistenceError("feedback is only accepted for rejection")
    try:
        with session_factory.begin() as session:
            catalog = lock_catalog(session, catalog_id)
            previous = catalog.status
            topics = list(
                session.scalars(
                    select(TopicRecord).where(TopicRecord.catalog_id == catalog.id)
                )
            )
            no_op = (
                previous == "approved"
                and decision == "approve"
                and catalog.approved_by == reviewer
            ) or (
                previous == "rejected"
                and decision == "reject"
                and catalog.review_feedback == feedback
            )
            if not no_op:
                target = TRANSITIONS.get((previous, decision))
                if target is None:
                    raise CatalogPersistenceError(
                        f"cannot {decision} a {previous} catalog"
                    )
                view = load_catalog_view(session, catalog.id)
                if decision in {"submit", "approve"}:
                    if view["coverage"]["blocking_issue_count"] or not topics:
                        raise CatalogPersistenceError(
                            "catalog has blocking evidence or hierarchy findings"
                        )
                    verify_artifacts(view, root)
                catalog.status = target
                if decision == "approve":
                    catalog.approved_by = reviewer
                    catalog.approved_at = datetime.now(UTC)
                    for topic in topics:
                        topic.status = "approved"
                elif decision == "reject":
                    catalog.review_feedback = feedback
                    for topic in topics:
                        topic.status = "rejected"
                session.flush()
            expected_topic_status = (
                "approved"
                if catalog.status == "approved"
                else "rejected" if catalog.status == "rejected" else "proposed"
            )
            if any(topic.status != expected_topic_status for topic in topics):
                raise CatalogPersistenceError(
                    "catalog and topic review states disagree"
                )
            status = catalog.status
            approved_by = catalog.approved_by
            approved_at = (
                catalog.approved_at.isoformat() if catalog.approved_at else None
            )
            review_feedback = catalog.review_feedback
            count = len(topics)
    except IntegrityError:
        raise CatalogPersistenceError(
            "review conflicts with an existing approved catalog or database constraint"
        ) from None
    # The review transaction is committed before any artifact write. A fresh lock
    # serializes repair with subsequent decisions so older states cannot overwrite newer ones.
    _, artifacts = inspect_catalog(session_factory, catalog_id, root=root, repair=True)
    assert artifacts is not None
    return ReviewResult(
        str(catalog_id),
        previous,
        status,
        count,
        approved_by,
        approved_at,
        review_feedback,
        no_op,
        artifacts,
    )
