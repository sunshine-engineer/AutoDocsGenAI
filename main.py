from models.state import PipelineState
from pipeline.workflow import run_pipeline


def main() -> None:
    state = PipelineState(
        package="langchain",
        version="0.3",
    )

    state = run_pipeline(state)

    manifest = state.manifest
    if manifest is None:
        raise RuntimeError("Pipeline completed without a documentation manifest")

    crawl_plan = state.crawl_plan
    if crawl_plan is None:
        raise RuntimeError("Pipeline completed without a crawl plan")

    print()

    for source in manifest.sources:
        print(source.title)
        print(source.status)
        print(source.http_status)
        print(source.redirect_url)
        print()

    print("Crawl Plan")

    for page in crawl_plan.pages[:20]:
        print(page.title)
        print(page.url)
        print()

    for doc in state.raw_documents:
        print(doc.title)
        print(doc.url)
        print(doc.status_code)
        print(doc.framework)
        print()


if __name__ == "__main__":
    main()
