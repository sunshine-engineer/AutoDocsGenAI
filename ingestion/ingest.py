from models.clean_document import CleanDocument
from models.state import PipelineState

from ingestion.cleaner import clean_markdown
from ingestion.extractor import extract_main_content
# from ingestion.fetcher import fetch_document
from ingestion.normalizer import html_to_markdown
from ingestion.storage import save_document
from config.settings import CrawlConfig

from ingestion.fetchers.selector import get_fetcher


def ingest_documents(
    state: PipelineState,
) -> PipelineState:

    if state.crawl_plan is None:
        return state

    max_pages = CrawlConfig().max_pages
    for page in state.crawl_plan.pages[:max_pages]:

        fetcher = get_fetcher(
            use_browser=True,
        )
        
        raw = fetcher.fetch(
            page.title,
            page.url,
        )

        state.raw_documents.append(raw)

        soup = extract_main_content(
            raw.html,
            raw.framework,
        )

        markdown = html_to_markdown(str(soup))

        markdown = clean_markdown(markdown)

        clean_doc = CleanDocument(
            title=page.title,
            url=page.url,
            markdown=markdown,
        )

        state.cleaned_documents.append(clean_doc)

        output_dir = (
            f"data/cleaned/"
            f"{state.package}/"
            f"{state.version}"
        )
        
        save_document(
            clean_doc,
            output_dir,
        )

    return state