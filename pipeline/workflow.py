from pathlib import Path

from agents.reviewer import review_documentation
from agents.validator import validate_documentation
from agents.writer import generate_documentation
from discovery.discover import discover_documentation
from indexing.chunker import create_chunks
from indexing.embedder import generate_embeddings
from indexing.vectorstore import index_documents
from ingestion.ingest import ingest_documents
from models.state import PipelineState
from planner.planner import build_crawl_plan
from retrieval.retriever import retrieve_relevant_chunks
from services.chunk_importer import persist_pipeline_state
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.progress import ProgressReporter

logger = setup_logger()


def run_pipeline(
    state: PipelineState,
    reporter: ProgressReporter | None = None,
) -> PipelineState:
    """Run the pipeline and report completed, implemented stages."""

    progress = reporter or ProgressReporter()
    config = load_config()
    logger.info("========== PIPELINE STARTED ==========")

    logger.info("Starting Documentation Discovery")
    state = discover_documentation(state)
    if state.manifest is None:
        raise RuntimeError("Discovery completed without a documentation manifest")
    logger.info(
        "Validated %d documentation sources.",
        len(state.manifest.sources),
    )
    progress.completed(
        "Official documentation discovery",
        {
            "sources_found": len(state.manifest.sources),
            "sources_verified": sum(
                source.status == "verified" for source in state.manifest.sources
            ),
        },
    )

    logger.info("Building Crawl Plan")
    state = build_crawl_plan(state)
    if state.crawl_plan is None:
        raise RuntimeError("Crawl planning completed without a crawl plan")
    logger.info(
        "Discovered %d pages.",
        len(state.crawl_plan.pages),
    )
    progress.completed(
        "Crawl planning",
        {
            "pages_planned": len(state.crawl_plan.pages),
            "root_url": state.crawl_plan.root_url,
        },
    )

    logger.info("Starting Document Ingestion")
    state = ingest_documents(state)
    logger.info(
        "Downloaded %d documents.",
        len(state.cleaned_documents),
    )
    cleaned_directory = (
        Path(config.data.cleaned_directory) / state.package / state.version
    )
    progress.completed(
        "Download, extraction, and Markdown normalization",
        {
            "documents_downloaded": len(state.raw_documents),
            "documents_cleaned": len(state.cleaned_documents),
        },
        artifact=cleaned_directory,
    )

    state = create_chunks(state)
    chunks_path = (
        Path(config.data.chunks_directory)
        / state.package
        / state.version
        / "chunks.jsonl"
    )
    progress.completed(
        "Markdown chunking",
        {
            "chunks_created": len(state.chunks),
            "source_documents": len(state.cleaned_documents),
        },
        artifact=chunks_path,
    )

    import_result = persist_pipeline_state(state)
    progress.completed(
        "PostgreSQL lineage persistence",
        import_result.to_dict(),
    )

    progress.next_stage("Embedding generation and vector indexing")

    # The stages below are placeholders. Do not report them as completed until
    # they produce real artifacts and meet their acceptance criteria.
    state = generate_embeddings(state)
    state = index_documents(state)
    state = retrieve_relevant_chunks(state)
    state = generate_documentation(state)
    state = validate_documentation(state)
    state = review_documentation(state)

    logger.info("========== CURRENT IMPLEMENTATION COMPLETED ==========")
    return state
