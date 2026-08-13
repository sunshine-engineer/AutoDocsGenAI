# Stage 5 embedding and vector-indexing prototype

Status: prototype implemented, indexed, and retrieval-tuned against reusable
PostgreSQL.

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
7. A broad semantic candidate pool is reranked with bounded API identifier and
   heading/title signals; stored embeddings do not change.

## Retrieval evaluation

The checked-in `retrieval/evaluation_cases/langchain-0.3.json` suite contains
six representative API and natural-language queries. Run it with:

```bash
python -m scripts.evaluate_retrieval langchain 0.3 --limit 5
```

The evaluator reports Hit Rate@5, mean reciprocal rank (MRR), and each query's
first relevant rank for both cosine-only and hybrid retrieval. On the reusable
1,533-chunk LangChain 0.3 index, both modes achieved 100% Hit Rate@5; hybrid
reranking improved MRR from 0.917 to 1.000 by moving the exact
`SummarizationMiddleware` class from rank 2 to rank 1.

## Deferred optimization

- model quality evaluation and model replacement;
- dynamic vector dimensions through separate tables or schema versions;
- adaptive batch sizing and parallel embedding workers;
- model pre-baking into a custom image instead of first-run volume download;
- larger human-reviewed evaluation sets and learned reranking;
- PostgreSQL full-text search for richer lexical recall.

## Validation evidence

- model downloaded into the Docker `model_cache` volume;
- measured cache size: 65 MB;
- real model output: 384 dimensions;
- Stage 5 migration applied to a disposable PostgreSQL database;
- two chunks embedded and stored; repeat indexing reused both;
- an installation query ranked the installation chunk first;
- stored vector dimension and cosine HNSW index verified;
- disposable database removed after validation;
- reusable database migrated to `0002_stage5_embeddings`;
- all 1,533 current LangChain 0.3 chunks indexed with zero duplicate
  chunk/model pairs;
- repeat indexing reused all 1,533 embeddings;
- six-query retrieval evaluation achieved 100% Hit Rate@5 and 1.000 tuned MRR.
