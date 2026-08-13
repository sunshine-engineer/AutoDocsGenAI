



def select_pages(pages: list[CrawlPage], max_pages: int = 50) -> list[CrawlPage]:
    return pages[:max_pages]