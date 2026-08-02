

# Repository Structure


    documentation-knowledge-pipeline/
                            │
                            ├── config/
                            │   ├── config.yaml   -- Only configuration
                            │   └── logging.yaml  -- Only configuration
                            │
                            ├── data/
                            │   ├── raw/
                            │   ├── cleaned/
                            │   ├── chunks/
                            │   ├── embeddings/
                            │   └── generated_docs/
                            │
                            ├── discovery/          -- only responsible for Package Official documentation URLs 
                            │   ├── discover.py
                            │   └── validator.py
                            │
                            ├── ingestion/          -- Only responsible for HTML to clean document generation
                            │   ├── downloader.py
                            │   ├── parser.py
                            │   └── cleaner.py
                            │
                            ├── indexing/          -- responsible for Document > chunks > Enbeddings > Vector DB
                            │   ├── chunker.py
                            │   ├── embedder.py
                            │   └── vectorstore.py
                            │
                            ├── retrieval/        -- responsible for Query > relevant chunks
                            │   └── retriever.py
                            │
                            ├── agents/            -- LLM's live here
                            │   ├── writer.py
                            │   ├── validator.py
                            │   └── reviewer.py
                            │
                            ├── prompts/
                            │
                            ├── models/             -- only pydantic models
                            │   ├── state.py
                            │   ├── config.py
                            │   ├── metadata.py
                            │   └── document.py
                            │
                            ├── pipeline/
                            │   └── workflow.py
                            │
                            ├── utils/             Reusable helper functions
                            │   ├── logger.py
                            │   ├── file_utils.py
                            │   └── helpers.py
                            │
                            ├── notebooks/
                            │
                            ├── tests/
                            │
                            ├── main.py
                            │
                            ├── requirements.txt
                            │
                            └── README.md



# Pipeline Architecture

                                            State

                                            ↓

                                            Discovery

                                            ↓

                                            State

                                            ↓

                                            Downloader

                                            ↓

                                            State

                                            ↓

                                            Cleaner

                                            ↓

                                            State

                                            ↓

                                            Chunker

                                            ↓

                                            State

                                            ↓

                                            Retriever

                                            ↓

                                            State

                                            ↓

                                            Writer

                                            ↓

                                            State

                                            ↓

                                            Validator

                                            ↓

                                            Export




# Coding Standards

| Standard      | Rule                              |
| ------------- | --------------------------------- |
| Language      | Python 3.12+                      |
| Formatting    | `black`                           |
| Linting       | `ruff`                            |
| Type Checking | `mypy` (where practical)          |
| Data Models   | Pydantic                          |
| Docstrings    | Google style                      |
| Imports       | Absolute imports                  |
| Configuration | YAML only                         |
| Logging       | `logging` module                  |
| Testing       | `pytest`                          |
| Secrets       | `.env` (never commit credentials) |






# Packages

| Component             | Library                                      | Why                                                                        |
| --------------------- | -------------------------------------------- | -------------------------------------------------------------------------- |
| Workflow / Agents     | **LangGraph**                                | Current standard for stateful agent workflows.                             |
| LLM abstraction       | **LangChain**                                | Mature ecosystem with strong integration support.                          |
| Local LLM             | **Ollama**                                   | Best local inference experience.                                           |
| Embeddings            | **Nomic Embed** (via Ollama)                 | Excellent open-source embedding model.                                     |
| Vector DB             | **ChromaDB**                                 | Simple, local-first, ideal for this project.                               |
| Crawling              | **Crawl4AI**                                 | Better suited to modern documentation sites than basic scraping.           |
| HTML parsing          | **BeautifulSoup4**                           | Still the de facto standard for HTML cleanup.                              |
| Structured output     | **Pydantic v2**                              | Fast, type-safe, and integrates well with LangChain.                       |
| Configuration         | **PyYAML**                                   | Stable and widely used.                                                    |
| Environment variables | **python-dotenv**                            | Standard approach.                                                         |
| Logging               | **Standard `logging`** + optional `colorlog` | Built into Python and production proven.                                   |
| HTTP client           | **httpx**                                    | Modern async/sync HTTP client, preferred over `requests` for new projects. |
| Testing               | **pytest**                                   | Industry standard.                                                         |
| Linting               | **ruff**                                     | Fast, comprehensive, replacing multiple older tools.                       |
| Formatting            | **black**                                    | Still widely adopted.                                                      |
| Type checking         | **mypy**                                     | Good complement to Pydantic and type hints.                                |



## Discovery Flow

                Package Name

                ↓

                PyPI JSON API

                ↓

                Project URLs

                ↓

                Documentation URL

                ↓

                Homepage

                ↓

                GitHub

                ↓

                Release Notes

                ↓

                Build Manifest



