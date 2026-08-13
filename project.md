# Documentation Knowledge Pipeline (GenAI Portfolio Project)

## Vision

Build a production-inspired Generative AI system that automatically discovers official documentation, ingests it, retrieves relevant knowledge, validates generated content, and produces structured Markdown learning material.

> Goal: Build a Documentation Knowledge Pipeline, **not** a chatbot.

---

# Objectives

- Use only official documentation as the source of truth.
- Generate high-quality Markdown documentation.
- Minimize hallucinations through retrieval and validation.
- Keep a human-in-the-loop approval workflow.
- Use free/open-source models and tooling.
- Build incrementally and modularly.

---

# User Workflow

1. User enters:
   - Package name
   - Version
2. System discovers official documentation.
3. User confirms or overrides the documentation URL.
4. Documentation is downloaded and cleaned.
5. Documents are chunked and indexed.
6. Relevant chunks are retrieved.
7. Structured Markdown is generated.
8. Validation checks run.
9. User reviews:
   - approve
   - edit
   - regenerate with instructions
10. Approved Markdown is exported.

---

# Non-Negotiable Rules

## Rule 1
Only official documentation is used.

Allowed:
- Official docs
- Official API reference
- Official release notes
- Official examples
- Official GitHub repository (optional)

Not allowed:
- Blogs
- Reddit
- Medium
- Stack Overflow

## Rule 2
Never invent information.

If unsupported:

"Not documented in the official documentation."

## Rule 3
Every section must include traceable source metadata.

## Rule 4
Generate page-by-page or topic-by-topic.

## Rule 5
Human approval required before final output.

---

# High-Level Architecture

User
→ Project Configuration
→ Documentation Discovery
→ User URL Confirmation
→ Downloader
→ HTML Cleaning
→ Structured Documents
→ Chunking
→ Embeddings
→ Vector Database
→ Retrieval
→ Documentation Writer
→ Validation
→ Human Review
→ Markdown Export

---

# Agents

## Discovery Agent
Find official documentation and versioned URLs.

## Ingestion Agent
Download, clean and normalize documentation.

## Indexing Agent
Chunk, embed and store metadata.

## Retrieval Agent
Retrieve only relevant chunks.

## Documentation Writer Agent
Generate structured Markdown only from retrieved evidence.

## Validation Agent
Check citations, formatting, unsupported claims and completeness.

## Human Reviewer
Approve, edit or regenerate.

---

# Markdown Template

- Definition
- Purpose
- When to Use
- Syntax
- Parameters
- Examples
- Best Practices
- Common Mistakes
- Related Components
- References

---

# Technology Stack

| Layer | Choice |
|-------|--------|
| Language | Python |
| Development | Jupyter Notebook initially |
| Orchestration | LangGraph |
| LLM | Qwen 3 (Ollama) |
| Embeddings | Nomic Embed or BGE-small |
| Vector DB | ChromaDB |
| Crawling | Crawl4AI |
| HTML Parsing | BeautifulSoup |
| Validation | Pydantic |

---

# Repository Structure

```text
documentation-pipeline/
├── config/
├── discovery/
├── ingestion/
├── chunking/
├── embeddings/
├── vectorstore/
├── retrieval/
├── agents/
├── prompts/
├── markdown/
├── generated_docs/
├── notebooks/
├── tests/
└── main.py
```

---

# Development Roadmap

1. Project foundation
2. Documentation discovery
3. Ingestion
4. Chunking & indexing
5. Retrieval
6. Structured generation
7. Validation
8. Human review
9. Markdown export

---

# Future Enhancements

- Searchable documentation website
- Multi-version comparisons
- Incremental updates
- Evaluation metrics
- CI/CD pipeline
- Docker deployment

---

# Project Philosophy

This project demonstrates:

- Retrieval-Augmented Generation (RAG)
- Agentic workflows
- Structured outputs
- Human-in-the-loop AI
- Hallucination mitigation
- Production-oriented GenAI engineering

The focus is on building a reliable documentation knowledge pipeline rather than a generic chatbot.
