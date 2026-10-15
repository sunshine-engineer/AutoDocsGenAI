from __future__ import annotations

from dataclasses import dataclass

from models.config import EmbeddingConfig
from models.identity import sha256_identity
from models.topic import TopicKind
from services.chunk_importer import normalize_package_name

CATALOG_IDENTITY_SCHEMA_VERSION = "stage6-catalog-v1"


@dataclass(frozen=True)
class CatalogIdentityConfig:
    """Versioned inputs that can change catalog construction output."""

    embedding: EmbeddingConfig
    namespace_allow_list: tuple[str, ...]
    enabled_topic_kinds: tuple[TopicKind, ...] = tuple(TopicKind)
    extractor_version: str = "b1-reference-curated-v1"
    normalization_version: str = "b2-normalization-paths-v1"
    duplicate_resolution_version: str = "b2-canonical-identity-v1"
    api_evidence_limit: int = 8
    curated_evidence_limit: int = 12
    hybrid_retrieval_enabled: bool = True
    retrieval_candidate_multiplier: int = 2
    schema_version: str = CATALOG_IDENTITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        text_fields = (
            self.schema_version,
            self.extractor_version,
            self.normalization_version,
            self.duplicate_resolution_version,
        )
        if any(not value.strip() for value in text_fields):
            raise ValueError("catalog identity versions must not be blank")
        if not self.namespace_allow_list:
            raise ValueError("namespace_allow_list must not be empty")
        if any(not value.strip() for value in self.namespace_allow_list):
            raise ValueError("namespace_allow_list entries must not be blank")
        if len({value.casefold() for value in self.namespace_allow_list}) != len(
            self.namespace_allow_list
        ):
            raise ValueError("namespace_allow_list must be unique ignoring case")
        if not self.enabled_topic_kinds:
            raise ValueError("enabled_topic_kinds must not be empty")
        if len(set(self.enabled_topic_kinds)) != len(self.enabled_topic_kinds):
            raise ValueError("enabled_topic_kinds must be unique")
        if self.api_evidence_limit <= 0 or self.curated_evidence_limit <= 0:
            raise ValueError("evidence limits must be positive")
        if self.retrieval_candidate_multiplier <= 0:
            raise ValueError("retrieval_candidate_multiplier must be positive")


def catalog_config_snapshot(
    *,
    package: str,
    version: str,
    source_pipeline_run_id: str,
    input_snapshot_hash: str,
    config: CatalogIdentityConfig,
) -> dict[str, object]:
    """Return the canonical, non-secret inputs that determine a catalog."""

    return {
        "schema_version": config.schema_version,
        "package": normalize_package_name(package),
        "package_version": version,
        "source_pipeline_run_id": source_pipeline_run_id,
        "input_snapshot_hash": input_snapshot_hash,
        "extractor_version": config.extractor_version,
        "namespace_allow_list": sorted(
            value.rstrip("/") for value in config.namespace_allow_list
        ),
        "enabled_topic_kinds": sorted(
            topic_kind.value for topic_kind in config.enabled_topic_kinds
        ),
        "normalization_version": config.normalization_version,
        "duplicate_resolution_version": config.duplicate_resolution_version,
        "evidence": {
            "api_limit": config.api_evidence_limit,
            "curated_limit": config.curated_evidence_limit,
        },
        "retrieval": {
            "hybrid_enabled": config.hybrid_retrieval_enabled,
            "candidate_multiplier": config.retrieval_candidate_multiplier,
            "embedding": {
                "provider": config.embedding.provider,
                "model": config.embedding.model,
                "dimension": config.embedding.dimension,
            },
        },
    }


def catalog_config_hash(
    *,
    package: str,
    version: str,
    source_pipeline_run_id: str,
    input_snapshot_hash: str,
    config: CatalogIdentityConfig,
) -> str:
    """Hash every versioned input that can alter a catalog proposal."""

    return sha256_identity(
        catalog_config_snapshot(
            package=package,
            version=version,
            source_pipeline_run_id=source_pipeline_run_id,
            input_snapshot_hash=input_snapshot_hash,
            config=config,
        )
    )


def validate_catalog_config_snapshot(
    config_snapshot: dict[str, object], expected_hash: str
) -> None:
    """Reject a persisted configuration snapshot that does not match its hash."""

    actual_hash = sha256_identity(config_snapshot)
    if actual_hash != expected_hash:
        raise ValueError(
            "catalog configuration snapshot does not reproduce config_hash"
        )


def rehydrate_catalog_config(snapshot: dict[str, object]) -> CatalogIdentityConfig:
    """Accept only the canonical non-secret configuration schema for artifact repair."""
    from typing import Any, cast

    raw = cast(dict[str, Any], snapshot)
    try:
        retrieval = raw["retrieval"]
        embedding = EmbeddingConfig(
            **retrieval["embedding"], cache_directory="/not-used"
        )
        config = CatalogIdentityConfig(
            embedding=embedding,
            namespace_allow_list=tuple(raw["namespace_allow_list"]),
            enabled_topic_kinds=tuple(
                TopicKind(value) for value in raw["enabled_topic_kinds"]
            ),
            extractor_version=raw["extractor_version"],
            normalization_version=raw["normalization_version"],
            duplicate_resolution_version=raw["duplicate_resolution_version"],
            api_evidence_limit=raw["evidence"]["api_limit"],
            curated_evidence_limit=raw["evidence"]["curated_limit"],
            hybrid_retrieval_enabled=retrieval["hybrid_enabled"],
            retrieval_candidate_multiplier=retrieval["candidate_multiplier"],
            schema_version=raw["schema_version"],
        )
        canonical = catalog_config_snapshot(
            package=raw["package"],
            version=raw["package_version"],
            source_pipeline_run_id=raw["source_pipeline_run_id"],
            input_snapshot_hash=raw["input_snapshot_hash"],
            config=config,
        )
        if canonical != snapshot:
            raise ValueError("noncanonical fields")
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            "catalog configuration is not a canonical non-secret snapshot"
        ) from None
    if (
        config.extractor_version != "b1-reference-curated-v1"
        or config.normalization_version != "b2-normalization-paths-v1"
        or config.duplicate_resolution_version != "b2-canonical-identity-v1"
        or config.schema_version != CATALOG_IDENTITY_SCHEMA_VERSION
    ):
        raise ValueError(
            "catalog configuration requires an unavailable historical renderer"
        )
    return config
