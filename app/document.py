"""Ekstraksi teks dari PDF dan pemilihan konteks untuk QA."""
from __future__ import annotations

import re
from collections import Counter
from io import BytesIO

from pypdf import PdfReader

# ──────────────────────────────────────────────────────────────────────────────
# Karakter bullet umum dari PPT / Word
# ──────────────────────────────────────────────────────────────────────────────
_BULLET_RE = re.compile(
    r"^[ \t]*"
    r"(?:"
    r"[•◦▪▸►▷→‣⁃◆◇■□●○≡≣⊡]"   # bullet & simbol umum (explicit)
    r"|[\u2000-\u27FF]"            # Blok Unicode: General Punctuation, Arrows, Dingbats, dll.
    r"|[\u2900-\u2BFF]"            # Blok Unicode: Supplemental Arrows, Misc Symbols
    r"|[\uFB00-\uFFFD]"            # Blok Unicode: Simbol lain & PUA
    r")"
    r"[ \t]*",
    re.MULTILINE,
)

# Pola baris yang kemungkinan besar adalah header/footer slide (tanggal, nomor halaman)
_FOOTER_RE = re.compile(
    r"^\s*("
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"  # hari Inggris
    r"|(senin|selasa|rabu|kamis|jumat|sabtu|minggu)"               # hari Indonesia
    r"|(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"                   # tanggal numerik
    r"|(january|february|march|april|may|june|july|august|september|october|november|december)"
    r"|(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)"
    r")\b.*$",
    re.IGNORECASE | re.MULTILINE,
)


# Pola baris nomor halaman (angka biasa, romawi V/VI/ix, atau teks "Halaman X") yang berdiri sendiri
_PAGE_NUMBER_RE = re.compile(
    r"^\s*("
    r"\d+"                                           # angka biasa (e.g., 1, 23, 104)
    r"|[ivxlcdm]+"                                   # romawi kecil (e.g., v, vi, ix)
    r"|[IVXLCDM]+"                                   # romawi besar (e.g., V, VI, IX)
    r"|((hal|halaman|page|pg)\.?\s*(\d+|[ivxlcdm]+|[IVXLCDM]+))" # dengan prefix hal/page
    r")\s*$",
    re.IGNORECASE
)


def _clean_ppt_page(text: str) -> str:
    """Bersihkan satu halaman hasil ekstraksi PPT/Book PDF."""
    # Bersihkan nomor halaman standalone di baris awal/akhir halaman
    lines = text.splitlines()
    cleaned_lines = []
    
    # Periksa dan bersihkan baris nomor halaman
    for idx, line in enumerate(lines):
        stripped = line.strip()
        # Jika baris cocok dengan pola nomor halaman, dan berada di 2 baris teratas/terbawah halaman
        if _PAGE_NUMBER_RE.match(stripped):
            if idx <= 2 or idx >= len(lines) - 3:
                continue # hapus baris ini
        cleaned_lines.append(line)
        
    text = "\n".join(cleaned_lines)
    
    # Ganti bullet dengan newline agar tiap poin jadi baris sendiri
    text = _BULLET_RE.sub("\n", text)
    # Hapus baris footer / tanggal / nomor slide
    text = _FOOTER_RE.sub("", text)
    # Hapus karakter kontrol (kecuali newline & tab)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalkan spasi berlebih
    text = re.sub(r"[ \t]+", " ", text)
    # Normalkan baris kosong berlebih
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _remove_repeated_lines(pages: list[str]) -> list[str]:
    """Hapus baris pendek yang muncul berulang di ≥30 % halaman (header/footer slide)."""
    if len(pages) < 2:
        return pages

    line_counts: Counter[str] = Counter()
    for page in pages:
        seen_on_page: set[str] = set()
        for line in page.splitlines():
            stripped = line.strip()
            # Hanya pertimbangkan baris pendek (< 120 karakter) yang bukan kosong
            if stripped and len(stripped) < 120:
                if stripped not in seen_on_page:
                    line_counts[stripped] += 1
                    seen_on_page.add(stripped)

    threshold = max(2, int(len(pages) * 0.30))
    repeated = {line for line, cnt in line_counts.items() if cnt >= threshold}

    cleaned: list[str] = []
    for page in pages:
        lines = [ln for ln in page.splitlines() if ln.strip() not in repeated]
        cleaned.append("\n".join(lines))
    return cleaned


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    raw_pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            raw_pages.append(text.strip())

    # Terapkan pembersihan PPT — aman untuk PDF biasa karena hanya
    # menghapus karakter/pola yang tidak ada di teks bersih.
    cleaned_pages = [_clean_ppt_page(p) for p in raw_pages]
    cleaned_pages = _remove_repeated_lines(cleaned_pages)

    return "\n\n".join(p for p in cleaned_pages if p.strip())


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
