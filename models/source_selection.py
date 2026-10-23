# File: models/source_selection.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Represent explicit human source confirmation and exact release boundaries."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceSelection(BaseModel):
    """Explicit human attestation; HTTP reachability is a separate concern.

    Attributes:
        package (str): Distribution name used to scope lineage and results.
        version (str): Exact package release; version families are not accepted
            implicitly.
        root_url (str): Confirmed documentation root URL.
        version_evidence_url (str): Version evidence url.
        immutable_revision (str): Immutable revision.
        confirmed_by (str | None): Confirmed by.
        confirmed_at (datetime | None): Confirmed at.
    """

    model_config = ConfigDict(extra="forbid")
    package: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9.+_-]*$")
    root_url: str
    version_evidence_url: str
    immutable_revision: str = Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        """Enforce safe exact-source URLs and paired, timezone-aware human confirmation.

        Returns:
            The same validated source-selection instance.

        Raises:
            ValueError: source URLs must be absolute HTTPS URLs without credentials,
                query, or fragment; immutable revision must not contain control
                characters; source confirmation requires both reviewer and time;
                reviewer must be nonblank and contain no control characters; source
                confirmation time must include a timezone.
        """
        for value in (self.root_url, self.version_evidence_url):
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "source URLs must be absolute HTTPS URLs without credentials, query, or fragment"
                )
        if any(ord(char) < 32 for char in self.immutable_revision):
            raise ValueError("immutable revision must not contain control characters")
        if (self.confirmed_by is None) != (self.confirmed_at is None):
            raise ValueError("source confirmation requires both reviewer and time")
        if self.confirmed_by is not None:
            self.confirmed_by = self.confirmed_by.strip()
            if (
                not self.confirmed_by
                or len(self.confirmed_by) > 200
                or any(ord(char) < 32 for char in self.confirmed_by)
            ):
                raise ValueError(
                    "reviewer must be nonblank and contain no control characters"
                )
            if self.confirmed_at is None or self.confirmed_at.utcoffset() is None:
                raise ValueError("source confirmation time must include a timezone")
        return self

    def require_confirmed(self, package: str, version: str) -> None:
        """Require confirmation matching the requested normalized package and exact
        version.

        Args:
            package: Distribution name used to scope lineage and results.
            version: Exact package release; version families are not accepted
                implicitly.

        Raises:
            ValueError: source selection does not match the requested package and exact
                version; source selection requires explicit human confirmation before
                crawling.
        """
        from services.chunk_importer import normalize_package_name

        if (
            normalize_package_name(self.package) != normalize_package_name(package)
            or self.version != version
        ):
            raise ValueError(
                "source selection does not match the requested package and exact version"
            )
        if self.confirmed_by is None or self.confirmed_at is None:
            raise ValueError(
                "source selection requires explicit human confirmation before crawling"
            )
