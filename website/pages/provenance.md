<!--
File: website/pages/provenance.md
Purpose: Sources & review policy.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->
# Sources & review policy

## What “Approved” means here

The five LangChain 1.4.6 articles were exported by the reviewed-page workflow after Sunny explicitly approved their exact page revisions. They are editorial corrections of real Docker Ollama drafts. Source quotations and technical claims were checked against the pinned release.

The source commit is `84ba23c414eca6bf6f6ebd1394a3006378113540` in the [official LangChain repository](https://github.com/langchain-ai/langchain/tree/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1).

The reader adds navigation and a review banner to the immutable export's Markdown. It does not revise the approved technical prose. The publication allowlist pins SHA-256 hashes of the export files; a changed, missing or mismatched approval stops the build. This checks recorded approval consistency, not a cryptographic signature or an independent reviewer identity verification.

[Publication allowlist](evidence/publication.json) · [Export manifest](evidence/build-manifest.json) · [Human approval record](evidence/approval-record.json)

## Source inventory is a different status

The ecosystem batch parsed hash-verified PyPI wheels for 30 packages and 89 releases. Its module/signature/docstring inventory is not an exhaustive public API assessment, an authored tutorial collection or proof that copied examples execute. Catalog entries without approved articles are visibly marked and do not link to unpublished article pages. Search can find their package/version inventory entries.

## What the tests prove

Offline runtime contracts exercise selected chains, graph state/checkpoints/streaming, and local tools. Some integration checks only construct clients and bind tool schemas. They do not verify hosted provider inference, cloud deployment, semantic retrieval quality or every upstream example.

See the [compatibility report](compatibility.md) for working combinations and demonstrated migration failures.

## Learning drafts awaiting review

[Learning placeholders](learning.md) identify four new teaching pages awaiting
human review. Their fixed-response examples have execution records, including a
real local tool call; this does not establish provider reasoning or tool selection.
Unresolved explanations and model-comparison drafts are not published here.
Queue resolutions alone never grant final publication approval.

## Publication boundary

This is a read-only static reader. Visiting a page does not run a model, modify a database, create jobs, or approve drafts. Source confirmation, outline review and final-page review remain operator workflows outside the website.

[Project code and license](https://github.com/sunshine-engineer/AutoDocsGenAI)
