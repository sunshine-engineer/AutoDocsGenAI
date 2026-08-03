# Documentation Knowledge Pipeline

A production-inspired Generative AI system that discovers official package documentation, ingests and cleans source content, retrieves relevant evidence, validates generated material, and produces structured Markdown documentation.

> This project is a work in progress, but it is designed as a reliable documentation knowledge pipeline rather than a general-purpose chatbot.

---

## Overview

This repository explores how to build an end-to-end GenAI system for technical documentation. The goal is to create a workflow that can move from raw documentation pages to polished, evidence-backed learning material.

The project focuses on reliability, traceability, and grounded generation rather than casual conversational AI.

---

## Why This Project Exists

Many AI systems generate content confidently without sufficient grounding. This project addresses that by combining:

- retrieval-augmented generation,
- source-backed writing,
- modular agent workflows,
- and validation checkpoints.

The emphasis is on building a trustworthy documentation pipeline for real-world use cases.

---

## Core Objectives

- Use only official documentation as the source of truth.
- Reduce hallucinations by grounding generation in retrieved evidence.
- Preserve traceability with metadata, citations, and source references.
- Generate structured content in a reusable Markdown format.
- Keep the workflow modular, extensible, and suitable for experimentation.
- Build a strong portfolio project that demonstrates GenAI engineering practices.

---

## Core Principles

1. Official sources only
   - Allowed sources include official docs, API references, release notes, official examples, and official repositories.

2. Zero invention
   - If the information is not present in the source material, the system should clearly indicate that it is not documented.

3. Evidence-based output
   - Generated sections should be connected to retrieved chunks and source metadata.

4. Topic-scoped generation
   - Content is generated for specific topics or pages rather than large unstructured document sets.

5. Human review
   - Final output should be validated and reviewed before export.

---

## System Architecture

The project is organized as a pipeline that moves from source discovery to final documentation generation.

```text
User Input
   ↓
Package Discovery
   ↓
Documentation URL Validation
   ↓
Downloader / Ingestion
   ↓
HTML Cleaning and Normalization
   ↓
Chunking and Indexing
   ↓
Embedding and Vector Storage
   ↓
Retrieval
   ↓
Documentation Generation
   ↓
Validation
   ↓
Review / Approval
   ↓
Markdown Export
```

## Current Workflow

The current workflow follows these stages:

1. Accept a package name and version.
2. Discover official documentation sources.
3. Build a crawl plan for relevant pages.
4. Download and ingest the documentation.
5. Clean and normalize the HTML content.
6. Create chunks and generate embeddings.
7. Store the content in a vector index.
8. Retrieve relevant evidence for a topic.
9. Generate structured Markdown content.
10. Validate the output and prepare it for review.

---

## Main Components

### Discovery
Responsible for identifying official documentation URLs and validating them.

### Ingestion
Handles downloading, parsing, and cleaning source content from documentation sites.

### Indexing
Processes cleaned documents into chunks, embeddings, and searchable indexes.

### Retrieval
Finds the most relevant chunks for a given topic or question.

### Agents
The project includes dedicated agent modules for:

- writing documentation,
- validating content,
- and reviewing output.

### Pipeline
The workflow orchestration layer ties all the stages together into a single end-to-end process.

---

## Current Status

This repository is in active development. The project structure and pipeline flow are in place, and several core modules have been scaffolded or partially implemented. Some of the agent stages are still placeholders, which makes this a strong WIP foundation for continued development.

### What is already present
- Pipeline state model
- Documentation discovery flow
- Ingestion and cleaning modules
- Chunking and indexing structure
- Retrieval module skeleton
- Writer, validator, and reviewer agent modules
- Main entry point

### What is still being built
- Full generation logic
- Strong validation rules
- Production-quality review flow
- More robust retrieval and grounding behavior

---

## Tech Stack

### Core Language
- Python

### Data and Validation
- Pydantic
- PyYAML
- python-dotenv

### HTTP and Parsing
- httpx
- BeautifulSoup4
- markdownify
- Playwright

### Development and Quality
- pytest
- black
- ruff
- colorlog

---

## Repository Structure

```text
auto_doc_pipeline/
├── agents/
├── cleaning/
├── config/
├── data/
├── discovery/
├── ingestion/
├── indexing/
├── models/
├── pipeline/
├── planner/
├── prompts/
├── retrieval/
├── services/
├── storage/
├── tests/
├── utils/
├── main.py
├── requirements.txt
└── README_1.md

```

