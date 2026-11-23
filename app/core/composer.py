from __future__ import annotations

import re

from app.core.retrieval import RetrievedChunk

MAX_CLASS_C_CHARS = 300


class LicenceComposer:
    """Apply licence rules to model-visible context and public citations."""

    def context_blocks(self, chunks: list[RetrievedChunk]) -> str:
        blocks = []
        for idx, ch in enumerate(chunks, start=1):
            blocks.append(
                f'<context id="{idx}" source="{ch.source_id}" '
                f'licence_class="{ch.licence_class}">\n{ch.text}\n</context>'
            )
        return "\n\n".join(blocks)

    def apply_output_policy(
        self,
        answer: str,
        chunks: list[RetrievedChunk],
    ) -> tuple[str, bool]:
        """Return (sanitised_answer, licence_compliant)."""
        compliant = True
        for ch in chunks:
            if ch.licence_class != "C":
                continue
            overlap = _longest_shared_substring(answer, ch.text)
            if len(overlap) > MAX_CLASS_C_CHARS:
                compliant = False
                answer = _cap_class_c_quote(answer, ch)
        return answer, compliant

    def citation_index(self, chunks: list[RetrievedChunk]) -> dict[int, RetrievedChunk]:
        return {i + 1: c for i, c in enumerate(chunks)}


def validate_citations(answer: str, chunk_count: int) -> bool:
    refs = {int(m) for m in re.findall(r"\[(\d+)\]", answer)}
    if not refs:
        return False
    return all(1 <= r <= chunk_count for r in refs)


def _longest_shared_substring(a: str, b: str) -> str:
    a, b = a.lower(), b.lower()
    best = ""
    for i in range(len(a)):
        for j in range(i + 1, len(a) + 1):
            frag = a[i:j]
            if len(frag) > len(best) and frag in b:
                best = frag
    return best


def _cap_class_c_quote(answer: str, ch: RetrievedChunk) -> str:
    notice = (
        f"\n\n(Excerpt only — {ch.title}. Read at source: {ch.source_url}. {ch.attribution_text})"
    )
    return answer + notice
