from abc import ABC, abstractmethod

from models.raw_document import RawDocument


class BaseFetcher(ABC):

    @abstractmethod
    def fetch(
        self,
        title: str,
        url: str,
    ) -> RawDocument: ...
