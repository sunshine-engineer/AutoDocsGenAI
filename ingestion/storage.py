from pathlib import Path

from models.clean_document import CleanDocument


def save_document(
    document: CleanDocument,
    output_dir: str,
) -> None:

    Path(output_dir).mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = document.title.replace("/", "_").replace("\\", "_")

    path = Path(output_dir) / f"{filename}.md"

    path.write_text(
        document.markdown,
        encoding="utf-8",
    )
