# LangChain and LangGraph ecosystem documentation

This batch produces a source-derived reference for a bounded ecosystem of 30 packages: 89 exact releases, 8,432 Python modules, and 34,452 class/function/method declarations. Every release wheel matched the SHA-256 in official PyPI metadata. All Python files parsed successfully. These counts include private implementation modules; they are **not** a count of verified public APIs.

The local reference starts at `data/generated_docs/ecosystem-2026-10-15/README.md`. Each version has module pages, source docstrings, signatures, source line numbers, imported-name inventories, licenses and a provenance manifest. The full `report.json` records additions, removals and signature differences. Downloaded source is parsed, never imported by the documentation builder.

The reference is separate from the five approved, model-drafted LangChain pages in `docs/generated/langchain/1.4.6`. This batch has no final human approval and does not claim equivalent editorial review. It is a source reference, not a complete authored tutorial collection. Inherited APIs, dynamic exports, conditional definitions, resolved re-exports and the entire third-party ecosystem remain coverage gaps. Examples copied from upstream docstrings are not automatically executed.

## Executed version checks

Python 3.12.15; fresh isolated environments; exact resolved dependencies are recorded in [evidence](evidence/). The graph tests execute conditional routing, checkpoint persistence within a process, and streaming. Tool tests execute a real local Python tool with fake model inputs.

| LangChain | LangGraph | Prompt chain | Graph/checkpoint/stream | ToolNode inside graph | create_agent | Direct ToolNode.invoke |
| --- | --- | --- | --- | --- | --- | --- |
| 0.3.30 | 0.6.11 | Pass | Pass | Pass | Import unavailable | Pass |
| 1.2.18 | 1.1.10 | Pass | Pass | Pass | Pass | Fails: missing runtime config |
| 1.3.18 | 1.2.15 | Pass | Pass | Pass | Pass | Fails: missing runtime config |
| 1.4.6 | 1.2.15 | Pass | Pass | Pass | Pass | Fails: missing runtime config |

An additional installation check deliberately combines LangChain 1.3.18 with LangGraph 1.1.10: resolution fails because LangChain requires LangGraph >=1.2.11,<1.3.0. This is a dependency incompatibility, not a documentation parser failure. [Resolver evidence](evidence/incompatible-install.log).

Two migration findings are demonstrated: modern `langchain.agents.create_agent` is absent from the tested 0.3 release; direct ToolNode invocation needs adaptation on the tested 1.x graph versions. Executing ToolNode inside a compiled StateGraph passes across all tested pairs. Static declaration changes are review candidates, not independently proven public API breakages.

## Integration checks

[Integration evidence](evidence/integrations.json) records six passing offline checks:

- OpenAI 1.7.2, Anthropic 1.7.6, Groq 1.1.3 and Ollama 1.1.0: construct clients and bind tool schemas. Provider inference is untested.
- Text splitters 1.1.3: execute chunking and check the size bound.
- Qdrant integration 1.1.0: insert documents and retrieve the exact matching document from an in-memory store using deterministic fake embeddings.

Socket connections are blocked throughout these integration checks. There are no real provider calls, paid APIs, production vector servers or external embedding downloads. Other documented integrations have static source coverage only. Multi-version inference tests for every provider are not complete.

## Reproduce

Run from the repository root with Python 3.12 and uv installed. Output and environment directories must be new.

```bash
python -m scripts.ecosystem_docs \
  --release-plan docs/ecosystem/release-plan.json \
  --output data/generated_docs/ecosystem-replay

python -m scripts.ecosystem_matrix \
  --output data/generated_docs/runtime-replay \
  --env-root /tmp/autodocs-matrix-replay
```

The first command checks every wheel hash against PyPI metadata. Compare the resulting hashes against [coverage.json](coverage.json) to confirm an identical source batch. Version selection without `--release-plan` chooses three recent stable major/minor lines for integrations, with explicit core baselines. LangChain has four versions because 1.2.18 provides a compatible partner for LangGraph 1.1.10.

For the integration probe, create another isolated Python 3.12 environment and install [integration-requirements.txt](evidence/integration-requirements.txt), then run:

```bash
python scripts/ecosystem_integrations.py integration-results.json
```

The matrix retains failures in raw reports and exits unsuccessfully if outcomes differ from the captured compatibility expectations. Do not interpret a successful matrix runner exit as every API passing.

## Practical guides and remaining work

Start with the [source-backed usage guide](usage-guide.md). For project closure, demonstrate the current compatible pair and the three proven migration/dependency findings. Further documentation expansion should resolve public exports, add inherited API coverage, curate prose, and execute selected upstream examples with explicit dependency and credential requirements. Final editorial publication requires review; source extraction alone does not provide that approval.

Source catalog: [LangChain upstream](https://github.com/langchain-ai/langchain), [LangGraph upstream](https://github.com/langchain-ai/langgraph), [LangChain release metadata](https://pypi.org/pypi/langchain/1.4.6/json), [LangGraph release metadata](https://pypi.org/pypi/langgraph/1.2.15/json). Full exact package scope and release pins are in [release-plan.json](release-plan.json).

## Validation of the tooling

Local verification: 156 offline tests passed; 42 database/model tests were deselected because this change does not alter those components. Ruff and MyPy passed, and tracked Python formatting matched Black. A locked LangGraph 1.2.15 replay produced an identical complete source manifest. Runtime results above were executed in fresh environments; they are not inferred from the unit-test count. CI also runs the full existing PostgreSQL integration job.
