from pipeline.workflow import run_pipeline

from models.state import PipelineState


def main():

    state = PipelineState(
        package="langchain",
        version="0.3",
    )

    state = run_pipeline(state)

    print()
    for source in state.manifest.sources:
        print(source.title)
        print(source.status)
        print(source.http_status)
        print(source.redirect_url)
        print()
    
    print("Crawl Plan")
        
    for page in state.crawl_plan.pages[:20]:

        print(page.title)

        print(page.url)

        print()
    
    for doc in state.raw_documents:
        
        print(doc.title)
        print(doc.url)
        print(doc.status_code)
        print(doc.framework)
        print()

    # print(state.model_dump())


if __name__ == "__main__":
    main()