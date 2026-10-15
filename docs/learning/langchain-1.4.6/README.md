# Learn agents through four executable recipes

This teaching collection is separate from the five approved exports. It adds
complete examples and practical explanations without changing their approved bytes.
**Content: authored by Codex; Sunny final approval pending.** Recorded execution
results do not constitute editorial approval.

## Outline

1. Create an agent and inspect its result.
2. Observe the model step with middleware.
3. Retain one conversation and isolate another.
4. Execute a real local tool and inspect an invalid-argument error.
5. Reproduce the environment and inspect verification limits.

| Recipe | What its assertions verify | Status |
| --- | --- | --- |
| [Minimal invocation](01_minimal_agent.md) | Message types and exact fixture reply | See execution record |
| [Middleware](02_middleware.md) | Synchronous hook order and reply | See execution record |
| [Conversation state](03_conversation_state.md) | Same-thread retention, separate-thread isolation, missing-config rejection | See execution record |

| [Local tool call](04_tool_call.md) | Actual Python execution, message routing and invalid-argument rejection | See execution record |

## Environment and execution

From the repository root, use Python 3.12 with uv. All resolved Python dependencies
are pinned in the requirements file, including LangChain 1.4.6, langchain-core
1.6.11 and LangGraph 1.2.15. The execution record identifies the tested Python patch.

```bash
uv venv .venv-learning --python 3.12
uv pip sync --python .venv-learning examples/learning/langchain_1_4_6/requirements.txt
uv run --no-project --python .venv-learning python -m scripts.check_learning_examples
```

The default report is `.site-work/learning-results.json`. To deliberately refresh
the tracked evidence after reviewing changes, pass
`--output docs/learning/langchain-1.4.6/execution.json`. Run without Python's
optimization flag: assertions are part of the checks. Installing dependencies
requires internet access; example execution denies Python socket connections and
DNS in the runner. This guard is not a sandbox for untrusted code.

The examples need no API keys or model downloads. The fake chat model returns
fixed responses. The fourth recipe executes a real local Python tool. Real-provider
quality, model-selected tool use, asynchronous middleware and durable checkpoint
storage remain unverified.

## Status vocabulary

- **Executed:** this exact scenario passed its assertions and expected-output check
  with recorded source/page hashes, dependencies and execution date.
- **Source-reviewed:** explanation checked against a pinned source; execution is
  absent or separately identified. Citation matching alone is not semantic review.
- **Untested:** no execution evidence exists; do not imply runtime correctness.
- **Credentials-required:** deliberately skipped pending provider access; not a pass.

[Execution record](execution.json). These pages remain outside the approved
website publication manifest until their final content is reviewed. The report
hashes identify what was executed; later edits require rerunning the checks.
