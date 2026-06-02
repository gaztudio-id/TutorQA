"""Ekstraksi teks dari PDF dan pemilihan konteks untuk QA."""
from __future__ import annotations

import re
from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def split_into_chunks(text: str, max_chunk: int = 800) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chunk:
            current = f"{current}\n\n{para}".strip() if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) <= max_chunk:
                current = para
            else:
                for i in range(0, len(para), max_chunk):
                    chunks.append(para[i : i + max_chunk])
                current = ""
    if current:
        chunks.append(current)
    return chunks or [text[:max_chunk]]


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"\w+", text) if len(w) > 2}


def select_best_context(question: str, chunks: list[str], max_chars: int = 2000) -> str:
    """Pilih chunk paling relevan dengan pertanyaan (bukan selalu chunk pertama)."""
    if not chunks:
        return ""
    if len(chunks) == 1:
        return chunks[0][:max_chars]

    q_tokens = _tokenize(question)
    q_lower = question.lower()

    scored: list[tuple[float, int, str]] = []
    for i, chunk in enumerate(chunks):
        c_tokens = _tokenize(chunk)
        c_lower = chunk.lower()
        overlap = len(q_tokens & c_tokens) / max(len(q_tokens), 1)

        bonus = 0.0
        if "bulan" in q_lower and "bulan" in c_lower:
            bonus += 0.5
        if "matahari" in q_lower and "matahari" in c_lower:
            bonus += 0.5
        if "mitos" in q_lower and re.search(r"\b(mitos|legenda|percaya)\b", c_lower):
            bonus += 0.5
        if "bulan" in q_lower and "matahari" in c_lower and "bulan" not in c_lower:
            bonus -= 0.3

        scored.append((overlap + bonus, i, chunk))

    scored.sort(key=lambda x: -x[0])

    best_score, best_idx, best_chunk = scored[0]
    if best_score < 0.08:
        # Fallback: gabungkan dua chunk pertama untuk menjaga kelengkapan awal
        combined = chunks[0]
        if len(chunks) > 1:
            combined += "\n\n" + chunks[1]
        return combined[:max_chars]

    selected_indices = [best_idx]
    selected_chunks = [best_chunk]
    total = len(best_chunk)

    # Selalu sertakan chunk berikutnya secara berurutan untuk menjaga kontinuitas bacaan
    next_idx = best_idx + 1
    if next_idx < len(chunks):
        selected_indices.append(next_idx)
        selected_chunks.append(chunks[next_idx])
        total += len(chunks[next_idx])

    # Periksa chunk dengan relevansi tinggi lainnya
    for score, idx, chunk in scored[1:4]:
        if score < 0.08:
            continue
        if total + len(chunk) > max_chars:
            continue
        if idx not in selected_indices:
            selected_indices.append(idx)
            selected_chunks.append(chunk)
            total += len(chunk)

    # Urutkan secara kronologis (berurutan dari indeks aslinya di dokumen) agar teks mengalir wajar
    sorted_chunks = [c for _, c in sorted(zip(selected_indices, selected_chunks), key=lambda x: x[0])]
    return "\n\n".join(sorted_chunks)[:max_chars]
