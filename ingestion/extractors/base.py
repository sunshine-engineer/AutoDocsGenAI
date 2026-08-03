from abc import ABC, abstractmethod

from bs4 import BeautifulSoup


class BaseExtractor(ABC):

    @abstractmethod
    def extract(
        self,
        soup: BeautifulSoup,
    ) -> BeautifulSoup:
        pass