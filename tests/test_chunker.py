import json

from config.settings import ChunkingConfig
from indexing.chunker import (
    chunk_document,
    create_chunks,
    split_markdown_sections,
)
from models.clean_document import CleanDocument
from models.state import PipelineState


def test_nested_headings_are_preserved_in_chunk_metadata():
    document = CleanDocument(
        title="Guide",
        url="https://example.com/guide",
        markdown=(
            "# Guide\n\nIntroduction.\n\n"
            "## Install\n\nInstall the package.\n\n"
            "### Linux\n\nRun the Linux command."
        ),
    )

    chunks = chunk_document(
        document,
        package="example",
        version="1.0",
        config=ChunkingConfig(max_characters=200, overlap_characters=20),
    )

    assert [chunk.header_path for chunk in chunks] == [
        ["Guide"],
        ["Guide", "Install"],
        ["Guide", "Install", "Linux"],
    ]
    assert all(chunk.source_url == document.url for chunk in chunks)


def test_heading_like_code_is_not_treated_as_a_section():
    markdown = (
        "# Examples\n\n"
        "```markdown\n# This is code\n## This is also code\n```\n\n"
        "## API\n\nAPI details."
    )

    sections = split_markdown_sections(markdown, ["#", "##", "###"])

    assert [section.header_path for section in sections] == [
        ("Examples",),
        ("Examples", "API"),
    ]
    assert "# This is code" in sections[0].content


def test_oversized_prose_is_bounded_and_deterministic():
    document = CleanDocument(
        title="Long guide",
        url="https://example.com/long-guide",
        markdown="# Guide\n\n" + " ".join(f"word-{index}" for index in range(100)),
    )
    config = ChunkingConfig(max_characters=120, overlap_characters=20)

    first = chunk_document(document, "example", "1.0", config)
    second = chunk_document(document, "example", "1.0", config)

    assert len(first) > 1
    assert all(chunk.character_count <= config.max_characters for chunk in first)
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert [chunk.content for chunk in first] == [chunk.content for chunk in second]


def test_oversized_code_fences_remain_balanced():
    code = "\n".join(f"print({index})" for index in range(30))
    document = CleanDocument(
        title="Examples",
        url="https://example.com/examples",
        markdown=f"# Examples\n\n```python\n{code}\n```",
    )
    config = ChunkingConfig(max_characters=90, overlap_characters=10)

    chunks = chunk_document(document, "example", "1.0", config)
    code_chunks = [chunk for chunk in chunks if "```" in chunk.content]

    assert len(code_chunks) > 1
    assert all(chunk.content.count("```") == 2 for chunk in code_chunks)
    assert all(chunk.character_count <= config.max_characters for chunk in chunks)


def test_document_without_headings_and_empty_document_are_supported():
    plain = CleanDocument(
        title="Plain",
        url="https://example.com/plain",
        markdown="A document without headings.",
    )
    empty = CleanDocument(
        title="Empty",
        url="https://example.com/empty",
        markdown=" \n\n ",
    )
    config = ChunkingConfig(max_characters=100, overlap_characters=10)

    plain_chunks = chunk_document(plain, "example", "1.0", config)
    empty_chunks = chunk_document(empty, "example", "1.0", config)

    assert len(plain_chunks) == 1
    assert plain_chunks[0].header_path == []
    assert empty_chunks == []


def test_create_chunks_replaces_state_and_writes_jsonl(tmp_path):
    document = CleanDocument(
        title="Guide",
        url="https://example.com/guide",
        markdown="# Guide\n\nContent.",
    )
    state = PipelineState(
        package="example",
        version="1.0",
        cleaned_documents=[document, document],
    )
    config = ChunkingConfig(max_characters=100, overlap_characters=10)

    first = create_chunks(state, config=config, output_directory=tmp_path)
    first_ids = [chunk.id for chunk in first.chunks]
    second = create_chunks(state, config=config, output_directory=tmp_path)

    output_path = tmp_path / "example" / "1.0" / "chunks.jsonl"
    records = [json.loads(line) for line in output_path.read_text().splitlines()]

    assert len(first_ids) == 1
    assert [chunk.id for chunk in second.chunks] == first_ids
    assert [record["id"] for record in records] == first_ids
    assert records[0]["header_path"] == ["Guide"]
