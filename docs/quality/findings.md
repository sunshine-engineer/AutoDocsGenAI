# Exploratory model comparison findings

## Outline

1. Recorded outcomes.
2. Agent assessment and limitations.
3. Human follow-up and publication boundary.

## Recorded outcomes

Same focused input and writer contract for both models; one attempt per task.

| Model | Task | Citation gate | Wall seconds | Agent factual / 4 | Agent clarity / 4 | Human editing time |
| --- | --- | --- | --- | --- | --- | --- |
| qwen3:1.7b | create_agent | citation_issues | 140.547 | 4 | 2 | Unmeasured |
| qwen3:1.7b | AgentMiddleware | citation_valid | 101.778 | 4 | 2 | Unmeasured |
| qwen3:4b | create_agent | citation_issues | 183.874 | 2 | 3 | Unmeasured |
| qwen3:4b | AgentMiddleware | citation_valid | 104.405 | 3 | 3 | Unmeasured |

## Assessment

Both models failed citation integrity on create_agent and passed exact quote checks on middleware. The larger model improved some explanation and coverage, but did not remove factual/citation editing needs. There is no justified automatic model switch from this sample.

These scores are a Codex assessment, not an independent human review or a statistical ranking. Factual support, exact quotations, requested coverage and teaching clarity are different dimensions. The compact input omitted full signature context; retain it in the next benchmark before generalizing tools-argument findings.

The model writer generates short grounded claims, not these authored runnable tutorials. No model-generated examples were executed in this comparison.

## Human follow-up

The [review queue](human-review-queue.json) binds each issue to an artifact hash and draft pointer. Keep raw runs immutable; record corrections as new revisions. Human editing time stays unknown until a timed editing session actually happens. Do not infer it from response length or generation time.

The reader displays safe placeholders for the four teaching pages. Pending review does not block serving the five approved articles or running unrelated examples. Queue resolution alone does not publish corrected model text.

Evidence: [raw focused run](comparison-run-02.json), [agent assessment](agent-review.json), [input](benchmark-input.json), [environment](runtime-environment.json), [full-context timeout](comparison-run-01.json).

Future comparisons automatically checkpoint a review handoff. [Recorded deterministic checks](comparison-run-02.review-queue.json) supplement the same central model issues; they do not constitute human approval.
