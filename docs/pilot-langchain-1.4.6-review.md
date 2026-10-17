# LangChain 1.4.6: source and five-page pilot for human review

Status: source and outline explicitly approved by Sunny in chat on 2026-10-15.
Approval is limited to review-only drafts; final content and database migration
remain unapproved. The local source/outline approval artifact records this decision.

## Outline

1. Exact source identity and integrity evidence.
2. Five proposed pages and the source supporting each one.
3. Deliberately limited first writing run and acceptance gates.

## Exact source

- Package release: `langchain==1.4.6`, selected from current official PyPI metadata.
- Official release: https://github.com/langchain-ai/langchain/releases/tag/langchain==1.4.6
- Tag resolves to commit `84ba23c414eca6bf6f6ebd1394a3006378113540`.
- Source root: https://github.com/langchain-ai/langchain/tree/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1
- The package is in `libs/langchain_v1`, not the `libs/langchain` legacy package.
- Its pinned `pyproject.toml` declares version `1.4.6`.
- Five official files were downloaded and SHA-256 checked locally. The snapshot
  manifest is under ignored `data/source_snapshots/langchain/1.4.6/COMMIT/snapshot.json`.
- Live documentation links may be provided as further reading, but are not used
  as patch-version evidence for this pilot. Source text comes from the commit.

## Proposed pages

| Kind | Page | Evidence at the pinned commit | Limits |
| --- | --- | --- | --- |
| Module | `langchain.agents` | `langchain/agents/__init__.py` module docstring and exports | Explain entrypoint and exports only; do not invent module behavior |
| Function | `create_agent` | `langchain/agents/factory.py`, implementation at lines 892–1925, signature and docstring | Select the implementation rather than three overload stubs; include only evidenced parameters |
| Class | `AgentMiddleware` | `langchain/agents/middleware/types.py`, lines 385–823, class and method docstrings | Keep methods on this page; do not invent lifecycle guarantees |
| Concept | LangChain agents and LangGraph | Package `README.md`, “What is this?” | Short overview; broader runtime details require more evidence |
| Guide | Installation | Package `README.md`, “Quick Install”, and `pyproject.toml` | Document the source command and declared constraints; no invented provider setup |

All paths above are relative to `libs/langchain_v1/`. Proposed output paths are
`modules/agents/README.md`, `modules/agents/functions/create-agent.md`,
`modules/agents/classes/agent-middleware.md`, `concepts/agent-architecture.md`,
and `guides/installation.md`.

## First writing run

Use local Docker Ollama with a small Qwen3 model and bounded structured JSON.
Every statement must identify its evidence chunk and an exact quotation.
Unknown chunks, wrong package/version, unmatched quotations, malformed outputs,
and insufficient evidence fail validation or produce abstention.

An exact quotation proves citation integrity, not semantic support. Human
support review remains mandatory. No draft is final or exportable merely
because deterministic citation checks pass.

The first actual source-backed generation run requires explicit human approval
of this source and outline. That approval does not approve any generated page,
merge a PR, or authorize migration of the reusable database. Synthetic model
smoke tests can run independently of real-source approval.
