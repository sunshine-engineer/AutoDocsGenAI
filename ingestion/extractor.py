from bs4 import BeautifulSoup


def extract_main_content(
    html: str,
) -> BeautifulSoup:

    return BeautifulSoup(
        html,
        "html.parser",
    )