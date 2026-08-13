# Stage 5 embedding and vector-indexing prototype

Status: prototype implemented and validated against disposable PostgreSQL.

## Frozen prototype model

- provider: FastEmbed using CPU-only ONNX Runtime;
- model: `BAAI/bge-small-en-v1.5`;
- model size: approximately 67 MB;
- dimension: 384;
- input limit: 512 tokens;
- license: MIT;
- cache: Docker named volume mounted at `/models`.

The model is deliberately small for a 16 GB RAM laptop without a GPU. Model
identity and dimension are stored in `embedding_versions`, so a later optimized
model can coexist during re-indexing instead of silently mixing vectors.

## Prototype behavior

1. Stage 4 persists current chunks and immutable source-document revisions.
2. The indexer selects only current chunks for one package and version.
3. Existing `(chunk, embedding version)` rows are reused.
4. Missing chunks are embedded in batches of 16 and stored as `vector(384)`.
5. An HNSW cosine index supports filtered similarity search.
6. Retrieval filters package, version, current revision, provider, model, and
   dimension before returning source metadata and scores.

## Deferred optimization

- model quality evaluation and model replacement;
- dynamic vector dimensions through separate tables or schema versions;
- adaptive batch sizing and parallel embedding workers;
- model pre-baking into a custom image instead of first-run volume download;
- index tuning, recall measurement, hybrid search, and reranking.

## Validation evidence

- model downloaded into the Docker `model_cache` volume;
- measured cache size: 65 MB;
- real model output: 384 dimensions;
- Stage 5 migration applied to a disposable PostgreSQL database;
- two chunks embedded and stored; repeat indexing reused both;
- an installation query ranked the installation chunk first;
- stored vector dimension and cosine HNSW index verified;
- disposable database removed after validation;
- persistent development database intentionally remains at Stage 4 until review.
