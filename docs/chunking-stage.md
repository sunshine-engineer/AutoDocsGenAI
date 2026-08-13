# Chunking Stage

Status: planned next stage; implementation has not started.

## Goal

Transform each cleaned Markdown document into deterministic, traceable chunks
that are ready for embedding and retrieval.

## Boundary

Input: `PipelineState.cleaned_documents`, containing `CleanDocument` objects.

Output: `PipelineState.chunks`, containing `Chunk` objects, plus a JSONL copy at
`data/chunks/{package}/{version}/chunks.jsonl`.

Embedding generation and vector storage are explicitly outside this stage.

## Implementation sequence

1. Split Markdown by headings while preserving the complete heading path.
2. Keep sections within `max_characters` intact.
3. Recursively split oversized sections with `overlap_characters` overlap.
4. Avoid splitting fenced code blocks where possible.
5. Remove empty chunks and retain source URL, title, package, and version.
6. Generate deterministic content hashes and chunk IDs.
7. Save chunks as JSONL and populate `PipelineState.chunks`.

## Required tests

- Nested headings preserve their hierarchy.
- Oversized sections are split within configured limits.
- Fenced code blocks remain balanced.
- Documents without headings are supported.
- Empty documents produce no chunks.
- Identical inputs produce identical IDs and ordering.
- Every chunk contains package, version, page title, and source URL.

## Definition of done

- Chunking is deterministic and idempotent.
- No empty chunks are produced.
- Every chunk can be traced to its source page and section.
- Chunk output is available in state and JSONL.
- The stage runs without Ollama or ChromaDB.
- Unit and integration tests pass.

Embedding generation, vector storage, retrieval, and LLM generation must remain
outside this change so chunk quality can be evaluated independently.
