# Source-backed usage guide

## Choose a compatible installation

For the current tested pair, create an isolated Python 3.12 environment and install `langchain==1.4.6` and `langgraph==1.2.15`. Reuse `evidence/current-requirements.txt` for the complete resolved dependency set. Do not combine independently selected versions merely because both are recent. The recorded 1.3.18/1.1.10 resolver failure demonstrates why.

## Compose a chain

`ChatPromptTemplate.from_messages` constructs a prompt; the runnable `|` operator composes it with a model and `StrOutputParser`. The offline probe uses `FakeListChatModel`, so this demonstrates orchestration without proving hosted inference. See the runnable chain implementation in `scripts/ecosystem_probe.py` and module references for `langchain_core.prompts.chat`, `langchain_core.runnables.base`, and `langchain_core.output_parsers.string` in the local generated core reference.

## Build a stateful graph

Define a TypedDict state, construct `StateGraph`, register a node with `add_node`, and connect it with `add_edge`/`add_conditional_edges`. Compile with `InMemorySaver`, pass a configurable `thread_id`, invoke the graph, then inspect `get_state` or consume `stream`. The executed test checks the final value and saved state. In-memory checkpoints do not demonstrate persistence across process restarts. Source modules: `langgraph.graph.state` in the graph wheel and `langgraph.checkpoint.memory` in the separately versioned checkpoint wheel.

## Execute a tool

Use `langchain_core.tools.tool` to derive the tool schema. Register a `ToolNode` inside a compiled `StateGraph(MessagesState)` and send an AIMessage with an explicit tool call. The example executes integer addition and checks the resulting ToolMessage content. This graph-based invocation passes across all tested pairs; the older direct node invocation fails on the tested newer releases. Source: `langgraph.prebuilt.tool_node` in the prebuilt distribution. These packages share a Python namespace but have separate distribution versions.

## Construct an agent

`langchain.agents.create_agent` constructs the modern agent graph in the tested 1.x versions. With `tools=[]` and a fake model, the test checks one returned answer. It does not prove a hosted model's tool selection. The tested 0.3.30 release cannot import this API; inspect that release's agent references before adapting legacy code. Source: `langchain.agents.factory` in 1.x. Broader agent behavior, middleware combinations and provider-specific tool calling need separate executable examples.

## Select integrations and retrieval

Integration packages are versioned separately. The offline integration probe verifies tool-schema binding for four chat integrations and a local text splitter. The Qdrant example uses a deterministic fake embedding and an in-memory vector store, then checks exact-text nearest-neighbor retrieval. This verifies local adapter behavior; it does not measure semantic retrieval quality or server operations. Source references include `langchain_openai`, `langchain_anthropic`, `langchain_groq`, `langchain_ollama`, `langchain_text_splitters`, and `langchain_qdrant`, each under its pinned distribution directory.

Use `docs/ecosystem/evidence/*.json` for executed outcomes and `data/generated_docs/ecosystem-2026-10-15/report.json` for source changes. A renamed internal declaration, signature change, passing schema binding, and successful provider inference are different kinds of evidence.

## Complete executable teaching recipes

The [four LangChain 1.4.6 recipes](../learning/langchain-1.4.6/README.md)
provide exact dependencies, complete code, expected output and assertions for
invocation, synchronous middleware, conversation isolation and a real local tool.
The tool example also checks invalid integer arguments without running the tool.
Model responses are scripted: these examples do not verify provider reasoning or
tool selection. Their explanations remain pending final Sunny review; the website
shows placeholders until reviewed publication is explicitly approved.
