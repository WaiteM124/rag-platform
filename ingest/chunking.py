from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import tiktoken

DISPLAY_MATH_START = re.compile(r"(?m)^\$\$|^\\begin\{(equation|align|gather)\*?\}")
DISPLAY_MATH_END = re.compile(r"(?m)^\$\$|^\\end\{(equation|align|gather)\*?\}")
HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    section_path: str
    text: str
    token_count: int
    chunk_hash: str
    chunk_index: int


def _encoder():
    return tiktoken.get_encoding("cl100k_base")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_hash(text: str, section_path: str) -> str:
    return content_hash(f"{section_path}\n{text}")


def _split_blocks(markdown: str) -> list[tuple[str, str]]:
    """Return (section_path, block_text) preserving display-math blocks."""
    lines = markdown.splitlines()
    blocks: list[tuple[str, str]] = []
    section_stack: list[str] = []
    buf: list[str] = []
    in_display_math = False

    def flush(section_path: str) -> None:
        nonlocal buf
        if buf:
            blocks.append((section_path, "\n".join(buf).strip()))
            buf = []

    section_path = "document"
    for line in lines:
        hm = HEADING.match(line)
        if hm and not in_display_math:
            flush(section_path)
            level = len(hm.group(1))
            title = hm.group(2).strip()
            section_stack = section_stack[: level - 1]
            section_stack.append(title)
            section_path = " › ".join(section_stack)
            continue
        if DISPLAY_MATH_START.search(line):
            in_display_math = True
        buf.append(line)
        if in_display_math and DISPLAY_MATH_END.search(line):
            in_display_math = False
            continue
    flush(section_path)
    return [(p, t) for p, t in blocks if t]


def chunk_markdown(
    markdown: str,
    *,
    min_tokens: int = 500,
    max_tokens: int = 900,
    overlap: int = 100,
) -> list[Chunk]:
    enc = _encoder()
    out: list[Chunk] = []
    idx = 0
    for section_path, block in _split_blocks(markdown):
        tokens = enc.encode(block)
        if len(tokens) <= max_tokens:
            text = block.strip()
            if not text:
                continue
            out.append(
                Chunk(
                    section_path=section_path,
                    text=f"[{section_path}]\n{text}",
                    token_count=len(enc.encode(text)) + len(enc.encode(section_path)),
                    chunk_hash=chunk_hash(text, section_path),
                    chunk_index=idx,
                )
            )
            idx += 1
            continue
        start = 0
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            piece = enc.decode(tokens[start:end]).strip()
            if piece:
                prefixed = f"[{section_path}]\n{piece}"
                out.append(
                    Chunk(
                        section_path=section_path,
                        text=prefixed,
                        token_count=len(enc.encode(prefixed)),
                        chunk_hash=chunk_hash(piece, section_path),
                        chunk_index=idx,
                    )
                )
                idx += 1
            if end >= len(tokens):
                break
            start = max(end - overlap, start + min_tokens)
    return out
