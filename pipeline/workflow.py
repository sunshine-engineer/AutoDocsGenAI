from utils.logger import setup_logger

from models.state import PipelineState

from discovery.discover import discover_documentation

from ingestion.downloader import download_documents
from ingestion.parser import parse_documents
from ingestion.cleaner import clean_documents

from indexing.chunker import create_chunks
from indexing.embedder import generate_embeddings
from indexing.vectorstore import index_documents

from retrieval.retriever import retrieve_relevant_chunks

from agents.writer import generate_documentation
from agents.validator import validate_documentation
from agents.reviewer import review_documentation


logger = setup_logger()


def run_pipeline(state: PipelineState) -> PipelineState:

    logger.info("========== PIPELINE STARTED ==========")

    logger.info("Starting Documentation Discovery")
    state = discover_documentation(state)
    logger.info(
    "Validated %d documentation sources.",
    len(state.manifest.sources),
    )
    
    
    state = download_documents(state)
    state = parse_documents(state)
    state = clean_documents(state)
    
    state = create_chunks(state)
    state = generate_embeddings(state)
    state = index_documents(state)
    
    state = retrieve_relevant_chunks(state)
    
    state = generate_documentation(state)
    
    state = validate_documentation(state)
    
    state = review_documentation(state)

    logger.info("========== PIPELINE COMPLETED ==========")

    return state