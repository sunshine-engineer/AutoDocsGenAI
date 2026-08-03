from pydantic import BaseModel

class CrawlConfig(BaseModel):
    max_pages: int = 10