from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from models.config import EmbeddingConfig
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


def canonical_json(value: object) -> str:
    """Serialize identity input with stable key ordering and no whitespace."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_identity(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def catalog_config_hash(
    *,
    package: str,
    version: str,
    source_pipeline_run_id: str,
    input_snapshot_hash: str,
    config: CatalogIdentityConfig,
) -> str:
    """Hash every versioned input that can alter a catalog proposal."""

    identity = {
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
    return sha256_identity(identity)
