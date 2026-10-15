# Documentation quality and model comparison

## Outline

1. Acceptance criteria for a useful page.
2. Reproducible comparison inputs and execution.
3. Independent factual and clarity review.
4. Measured editing time and model selection.

## Page acceptance criteria

A teaching page needs a concrete task, when/why guidance, prerequisites, a
complete executable file, exact dependencies, expected output, meaningful
assertions, a failure case or troubleshooting advice, and explicit limits.
Link claims to a pinned source in one source-mapping section rather than
interrupting every sentence with repeated quotations. Preserve the underlying
evidence and keep unsupported claims out of the page.

[Three authored recipes](../learning/langchain-1.4.6/README.md) implement this
format. They are review drafts outside the approved reader publication manifest.
Original approved exports remain unchanged.

## Reproduce the writer comparison

`benchmark-input.json` contains the original pilot's create_agent and
AgentMiddleware evidence, extracted from hash-verified official LangChain 1.4.6
source at commit `84ba23c414eca6bf6f6ebd1394a3006378113540`. The focused input
retains task-relevant excerpts, with the original extraction preserved in
`benchmark-input-full.json`. Upstream text is
covered by the accompanying MIT license. No model output is used as source.

Run against Docker Ollama with both models installed:

```bash
uv run --frozen python -m scripts.compare_doc_models --models qwen3:1.7b qwen3:4b --output docs/quality/comparison-run-01.json
```

The runner uses the existing production pilot writer's identical prompt/schema
and generation options for each model, records the model digest, input/contract
hashes, raw structured drafts, failures, citation issues, latency and tokens.
It allows one attempt per model/topic and writes results after each attempt.
A new run requires a new output path; do not overwrite raw evidence.
The runner unloads each tested model after each attempt. Run serially on an idle
local Ollama instance: concurrent jobs or other loaded models confound timing.

This measures the current grounded writer, which produces concise claims rather
than full tutorials or runnable examples. It does not compare the authored
teaching pages, validate generated code, or prove performance at ecosystem scale.
The recorded container limits and Ollama version are in
[runtime-environment.json](runtime-environment.json). A two-topic single-run comparison is exploratory. Repeat in reversed model order
and across more tasks before choosing a default on small score differences.
Wall time includes model loading when needed; the initial model may already be
loaded. Record hardware and normalize load state before extrapolating cost.

## Review each output independently

Do not turn citation validity into a factual accuracy score. Exact matching
only shows that a quotation occurs in the evidence. A reviewer must inspect the
claim, supporting context, omitted qualifications and version boundaries.

| Score | Factual accuracy | Clarity for the intended reader |
| --- | --- | --- |
| 0 | Central claim contradicted or invented | Unusable or misleading explanation |
| 1 | Multiple material unsupported claims | Major rewriting required |
| 2 | Partly supported; material qualification missing | Understandable with substantial clarification |
| 3 | Claims supported; minor imprecision | Clear with minor editing |
| 4 | Every claim supported with correct scope | Direct, precise, terminology explained for the task |

Accuracy and clarity stay separate. Abstention and failed generation are
reported as such; do not score an empty response as perfect accuracy. Missing
requested sections affect task coverage even if individual claims are accurate.
Blind model names when possible, use the same reviewer/instructions and keep
reviewer identity, date, rationale and quoted issue locations in a separate
review record. Human scores in raw runs remain null until recorded review.

## Measure editing effort

Start a timer when the editor opens a draft; stop when it meets the same
acceptance criteria. Record active editing seconds, factual corrections,
clarity changes, final revision hash and editor identity. Exclude unrelated
interruptions and distinguish editing from review time. Unknown time stays null,
not zero. Do not estimate editing time from token count or retrospective memory.

Prefer a model only after supported claims, useful coverage and low correction
effort are demonstrated. A faster incorrect draft is not a successful result.
Any edited output must become a new attributed revision and receive explicit
final approval before replacing an approved published page.


## Recorded experiments

- `comparison-run-01.json`: full-context trial; the first qwen3:1.7b request
  timed out after 240 seconds. The remaining trials were interrupted rather than
  repeatedly spending the same budget. An absent completion timestamp denotes
  the incomplete run. Its input hash identifies `benchmark-input-full.json`.
- The focused comparison uses `benchmark-input.json` for both models. Results
  from different input hashes must not be pooled into a model ranking.

The first report's original limits string says cold loads; initial load state
was not explicitly normalized. Treat all timings as exploratory wall time,
including loading when needed, rather than controlled cold-load benchmarks.


## Human-in-the-loop queue

[Findings](findings.md) summarize the completed exploratory comparison.
[human-review-queue.json](human-review-queue.json) tracks outstanding model issues
and the three teaching-page reviews with artifact hashes and exact draft pointers.
The reader shows placeholders for teaching pages; model drafts and resolution
notes are never rendered by this queue. Pending issues do not block unrelated work.

For each issue, Sunny can request revisions or provide a final decision later.
Record reviewer, timestamp, the reviewed artifact hash, decision and rationale
in a separate resolution record, then attach that record to the issue. If the
artifact hash has changed, review the new revision rather than reusing a stale
approval. A reviewed issue may move to `reviewed_not_published`; it still cannot
publish prose. Revised articles must use the existing explicit final approval,
export and publication-manifest workflow before replacing approved pages.

Human factual/clarity scores and editing time are intentionally unfilled in raw
benchmark reports. [agent-review.json](agent-review.json) is an attributed Codex
assessment, not a Sunny review or final content approval.
