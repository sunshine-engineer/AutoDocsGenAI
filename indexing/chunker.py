from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from config.settings import ChunkingConfig
from indexing.chunk_storage import write_chunks_jsonl
from models.chunk import Chunk
from models.clean_document import CleanDocument
from models.state import PipelineState
from utils.config_loader import load_config

HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE_PATTERN = re.compile(r"^[ \t]*(`{3,}|~{3,})")


@dataclass(frozen=True)
class MarkdownSection:
    """A Markdown section and the heading hierarchy that owns it."""

    header_path: tuple[str, ...]
    content: str


def create_chunks(
    state: PipelineState,
    config: ChunkingConfig | None = None,
    output_directory: str | Path | None = None,
) -> PipelineState:
    """Create deterministic chunks and persist them as JSONL.

    Existing chunks are replaced so repeated pipeline runs are idempotent.
    Configuration and output paths can be injected for tests; normal pipeline
    calls use ``config/config.yaml``.
    """

    application_config = None
    if config is None or output_directory is None:
        application_config = load_config()

    if config is None:
        assert application_config is not None
        config = application_config.chunking
    if output_directory is None:
        assert application_config is not None
        output_directory = application_config.data.chunks_directory

    chunking_config = config
    chunk_root = Path(output_directory)

    chunks_by_id: dict[str, Chunk] = {}
    for document in state.cleaned_documents:
        for chunk in chunk_document(
            document=document,
            package=state.package,
            version=state.version,
            config=chunking_config,
        ):
            chunks_by_id.setdefault(chunk.id, chunk)

    state.chunks = list(chunks_by_id.values())
    output_path = chunk_root / state.package / state.version / "chunks.jsonl"
    write_chunks_jsonl(state.chunks, output_path)
    return state


def chunk_document(
    document: CleanDocument,
    package: str,
    version: str,
    config: ChunkingConfig,
) -> list[Chunk]:
    """Split one cleaned document into traceable chunks."""

    chunks: list[Chunk] = []
    chunk_index = 0

    for section in split_markdown_sections(document.markdown, config.headers):
        section_chunks = split_section_content(
            section.content,
            max_characters=config.max_characters,
            overlap_characters=config.overlap_characters,
        )

        for content in section_chunks:
            normalized_content = content.strip()
            if not normalized_content:
                continue

            content_hash = hashlib.sha256(
                normalized_content.encode("utf-8")
            ).hexdigest()
            chunk_id = _build_chunk_id(
                package=package,
                version=version,
                source_url=document.url,
                header_path=section.header_path,
                chunk_index=chunk_index,
                content_hash=content_hash,
            )
            chunks.append(
                Chunk(
                    id=chunk_id,
                    content=normalized_content,
                    package=package,
                    version=version,
                    source_url=document.url,
                    page_title=document.title,
                    header_path=list(section.header_path),
                    chunk_index=chunk_index,
                    content_hash=content_hash,
                    character_count=len(normalized_content),
                )
            )
            chunk_index += 1

    return chunks


def split_markdown_sections(
    markdown: str,
    headers: list[str],
) -> list[MarkdownSection]:
    """Split Markdown on configured ATX headings outside fenced code blocks."""

    heading_levels = {len(marker) for marker in headers}
    sections: list[MarkdownSection] = []
    heading_path: dict[int, str] = {}
    current_path: tuple[str, ...] = ()
    current_lines: list[str] = []
    active_fence: tuple[str, int] | None = None

    def flush_section() -> None:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append(MarkdownSection(current_path, content))

    for line in markdown.splitlines():
        heading_match = HEADING_PATTERN.match(line) if active_fence is None else None
        if heading_match and len(heading_match.group(1)) in heading_levels:
            flush_section()
            current_lines = [line.rstrip()]

            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            heading_path = {
                path_level: path_title
                for path_level, path_title in heading_path.items()
                if path_level < level
            }
            heading_path[level] = title
            current_path = tuple(
                heading_path[path_level] for path_level in sorted(heading_path)
            )
            continue

        current_lines.append(line.rstrip())
        active_fence = _updated_fence_state(line, active_fence)

    flush_section()
    return sections


def split_section_content(
    content: str,
    max_characters: int,
    overlap_characters: int,
) -> list[str]:
    """Split a section at Markdown block boundaries with bounded overlap."""

    blocks = _markdown_blocks(content)
    chunks: list[str] = []
    current = ""

    for block, is_fenced in blocks:
        block_parts = (
            _split_fenced_block(block, max_characters)
            if is_fenced and len(block) > max_characters
            else (
                _split_plain_text(block, max_characters, overlap_characters)
                if len(block) > max_characters
                else [block]
            )
        )

        for part in block_parts:
            candidate = _join_blocks(current, part)
            if current and len(candidate) > max_characters:
                chunks.append(current)
                overlap = _safe_overlap_tail(current, overlap_characters)
                candidate = _join_blocks(overlap, part)
                current = candidate if len(candidate) <= max_characters else part
            else:
                current = candidate

    if current.strip():
        chunks.append(current)

    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _markdown_blocks(content: str) -> list[tuple[str, bool]]:
    """Return paragraph/code-fence blocks without breaking fenced code."""

    blocks: list[tuple[str, bool]] = []
    current_lines: list[str] = []
    active_fence: tuple[str, int] | None = None
    block_is_fenced = False

    def flush() -> None:
        nonlocal current_lines, block_is_fenced
        block = "\n".join(current_lines).strip()
        if block:
            blocks.append((block, block_is_fenced))
        current_lines = []
        block_is_fenced = False

    for line in content.splitlines():
        fence_before = active_fence
        fence_after = _updated_fence_state(line, active_fence)

        if fence_before is None and fence_after is not None:
            flush()
            block_is_fenced = True

        current_lines.append(line.rstrip())
        active_fence = fence_after

        if (
            fence_before is not None
            and fence_after is None
            or active_fence is None
            and not line.strip()
        ):
            flush()

    flush()
    return blocks


def _split_plain_text(text: str, limit: int, overlap: int) -> list[str]:
    """Split oversized prose at natural boundaries."""

    parts: list[str] = []
    start = 0

    while start < len(text):
        target = min(start + limit, len(text))
        end = target
        if target < len(text):
            search_floor = start + max(1, limit // 2)
            for separator in ("\n\n", "\n", " "):
                boundary = text.rfind(separator, search_floor, target + 1)
                if boundary != -1:
                    end = boundary + (len(separator) if separator != " " else 0)
                    break

        part = text[start:end].strip()
        if part:
            parts.append(part)
        if end >= len(text):
            break

        next_start = max(end - overlap, start + 1)
        while next_start < end and not text[next_start].isspace():
            next_start += 1
        start = min(end, next_start)

    return parts


def _split_fenced_block(block: str, limit: int) -> list[str]:
    """Split an oversized code fence while keeping every part balanced."""

    lines = block.splitlines()
    if len(lines) < 2:
        return [block]

    opener = lines[0]
    fence_match = FENCE_PATTERN.match(opener)
    if fence_match is None:
        return _split_plain_text(block, limit, 0)

    fence = fence_match.group(1)
    closer = fence[0] * len(fence)
    inner_lines = lines[1:-1] if _is_closing_fence(lines[-1], fence) else lines[1:]
    wrapper_size = len(opener) + len(closer) + 2
    inner_limit = limit - wrapper_size
    if inner_limit <= 0:
        return [block]

    inner = "\n".join(inner_lines)
    inner_parts = _split_plain_text(inner, inner_limit, 0) or [""]
    return [f"{opener}\n{part}\n{closer}" for part in inner_parts]


def _updated_fence_state(
    line: str,
    active_fence: tuple[str, int] | None,
) -> tuple[str, int] | None:
    match = FENCE_PATTERN.match(line)
    if match is None:
        return active_fence

    marker = match.group(1)
    if active_fence is None:
        return marker[0], len(marker)
    if marker[0] == active_fence[0] and len(marker) >= active_fence[1]:
        return None
    return active_fence


def _is_closing_fence(line: str, opener: str) -> bool:
    match = FENCE_PATTERN.match(line)
    return bool(
        match and match.group(1)[0] == opener[0] and len(match.group(1)) >= len(opener)
    )


def _safe_overlap_tail(content: str, overlap: int) -> str:
    if overlap <= 0 or "```" in content or "~~~" in content:
        return ""

    tail = content[-overlap:]
    first_space = tail.find(" ")
    if first_space != -1:
        tail = tail[first_space + 1 :]
    return tail.strip()


def _join_blocks(left: str, right: str) -> str:
    if not left:
        return right.strip()
    return f"{left.rstrip()}\n\n{right.lstrip()}"


def _build_chunk_id(
    package: str,
    version: str,
    source_url: str,
    header_path: tuple[str, ...],
    chunk_index: int,
    content_hash: str,
) -> str:
    identity = "\0".join(
        (
            package,
            version,
            source_url,
            "/".join(header_path),
            str(chunk_index),
            content_hash,
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()
