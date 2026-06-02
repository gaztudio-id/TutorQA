"""Menyusun jawaban tutor — mode benar-benar berbeda + relevansi pertanyaan."""
from __future__ import annotations

import re

_QUESTION_PATTERNS = {
    "why": r"\b(kenapa|mengapa|apa sebab|apa penyebab)\b",
    "how": r"\b(bagaimana|caranya|bagaimana cara)\b",
    "what": r"\b(apa itu|apa yang dimaksud|pengertian|definisi)\b",
    "when": r"\b(kapan)\b",
    "where": r"\b(di mana|dimana)\b",
    "list": r"\b(sebutkan|jenis|macam|daftar|apa saja)\b",
    "myth": r"\b(mitos|mitologi|legenda|kepercayaan)\b",
}

_CONNECTORS = ("Selain itu,", "Tambahan penting,", "Informasi lanjutan,")

_STOP_WORDS = {
    "yang", "dari", "pada", "dalam", "ini", "itu", "dan", "atau", "untuk",
    "dengan", "adalah", "akan", "dapat", "bisa", "juga", "saja", "oleh",
    "agar", "saat", "ketika", "menjadi", "secara", "para", "hal", "nya",
    "sangat", "lebih", "telah", "sudah", "hanya", "semua", "adapun",
    "karena", "sebab", "sebagai", "tentang", "maka", "tetapi", "mengapa",
    "bagaimana", "apakah", "kenapa", "apa", "siapa", "dimana", "kapan",
    "di", "ke", "seperti", "yaitu", "ialah", "merupakan"
}


def classify_question(question: str) -> str:
    q = question.lower()
    for kind, pattern in _QUESTION_PATTERNS.items():
        if re.search(pattern, q):
            return kind
    if re.search(r"\bapa\b", q):
        return "what"
    return "general"


def split_sentences(text: str) -> list[str]:
    # Join lines that don't end in sentence-ending punctuation to preserve PDF sentence flow
    lines = text.split("\n")
    cleaned_lines = []
    current_line = ""
    for line in lines:
        line = line.strip()
        if not line:
            if current_line:
                cleaned_lines.append(current_line)
                current_line = ""
            continue
        if current_line:
            # If current line ends with sentence ending, push it
            if current_line[-1] in ".!?":
                cleaned_lines.append(current_line)
                current_line = line
            else:
                current_line += " " + line
        else:
            current_line = line
    if current_line:
        cleaned_lines.append(current_line)

    joined_text = "\n\n".join(cleaned_lines)
    parts = re.split(r"(?<=[.!?])\s+|\n\n+", joined_text)
    return [p.strip() for p in parts if len(p.strip()) > 15]


def _get_clean_words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\b[a-zA-ZÀ-ü0-9\-]{3,30}\b", text)]


def score_sentence(sentence: str, question: str) -> float:
    s_lower = sentence.lower()
    q_words = _get_clean_words(question)
    s_words = _get_clean_words(sentence)

    if not q_words:
        return 0.0

    # Saring kata stopword untuk mendapatkan kata kunci konseptual
    q_keywords = [w for w in q_words if w not in _STOP_WORDS]
    if not q_keywords:
        q_keywords = q_words # fallback jika semua kata adalah stopword

    s_set = set(s_words)

    # 1. Hitung kecocokan kata kunci konseptual (kandungan kata kunci unik)
    matches = sum(1 for w in q_keywords if w in s_set)
    overlap_score = matches / len(q_keywords)

    # 2. Bonus pencocokan frasa kunci (bigram dari pertanyaan) untuk relevansi semantik tinggi
    phrase_bonus = 0.0
    for i in range(len(q_keywords) - 1):
        bigram = f"{q_keywords[i]} {q_keywords[i+1]}"
        if bigram in s_lower:
            phrase_bonus += 0.25

    # 3. Bonus khusus jika tipe pertanyaan cocok dengan penanda retorika kalimat penjelasan
    q_type = classify_question(question)
    rhetoric_bonus = 0.0
    if q_type == "why" and any(k in s_lower for k in ["karena", "sebab", "oleh karena", "dikarenakan", "alasan", "pentingnya"]):
        rhetoric_bonus += 0.15
    elif q_type == "how" and any(k in s_lower for k in ["cara", "langkah", "proses", "tahap", "metode", "sistem", "alur"]):
        rhetoric_bonus += 0.15
    elif q_type == "what" and any(k in s_lower for k in ["adalah", "merupakan", "yaitu", "ialah", "definisi", "arti"]):
        rhetoric_bonus += 0.15

    # 4. Bonus panjang kalimat sedang (preferensi kalimat penjelas, bukan daftar/frasa pendek)
    length = len(sentence)
    length_bonus = 0.0
    if 40 <= length <= 250:
        length_bonus = 0.1

    return overlap_score + phrase_bonus + rhetoric_bonus + length_bonus


def rank_sentences(context: str, question: str, limit: int = 6) -> list[str]:
    sentences = split_sentences(context)
    if not sentences:
        return []

    scored = sorted(
        ((score_sentence(s, question), s) for s in sentences),
        key=lambda x: x[0],
        reverse=True,
    )

    picked: list[str] = []
    seen: set[str] = set()
    for score, sent in scored:
        if score < 0.12 and picked:
            break
        key = sent.lower()[:50]
        if key in seen:
            continue
        seen.add(key)
        picked.append(sent)
        if len(picked) >= limit:
            break

    return picked


def _normalize(s: str) -> str:
    s = s.strip()
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s


def _merge_span(qa_span: str, sentences: list[str]) -> list[str]:
    if not qa_span:
        return sentences
    span = qa_span.strip()
    for sent in sentences:
        if span.lower() in sent.lower():
            return sentences
    if span[0].islower() or len(span) < 30:
        return sentences
    return [span] + sentences


def _not_found_message(question: str) -> str:
    return (
        f"Maaf, materi yang Anda berikan tidak memuat informasi yang cukup "
        f"untuk menjawab: \"{question}\". "
        f"Coba ajukan pertanyaan lain yang lebih dekat dengan isi teks, "
        f"atau tambahkan paragraf yang relevan ke konteks."
    )


def _build_ringkas(sentences: list[str], question: str) -> str:
    if not sentences:
        return ""
    s = _normalize(sentences[0])
    # Ringkas: maks 1 kalimat pendek
    if len(s) > 160:
        s = s[:157].rsplit(" ", 1)[0] + "..."
    return s


def _extract_list_items(text: str) -> list[str]:
    items: list[str] = []
    if ":" in text:
        after = text.split(":", 1)[1]
        parts = re.split(r",\s+|\s+dan\s+", after)
        for p in parts:
            p = p.strip().rstrip(".")
            if len(p) > 10:
                items.append(_normalize(p))
    return items[:5]


def _build_langkah(sentences: list[str], question: str) -> str:
    steps: list[str] = []

    for sent in sentences[:4]:
        items = _extract_list_items(sent)
        if items:
            steps.extend(items)
        else:
            parts = re.split(r"(?<=[.;])\s+", sent)
            for p in parts:
                p = p.strip()
                if len(p) > 20:
                    steps.append(_normalize(p))

    if not steps:
        steps = [_normalize(s) for s in sentences[:3]]

    # Unik
    unique: list[str] = []
    seen: set[str] = set()
    for step in steps:
        k = step.lower()[:40]
        if k not in seen:
            seen.add(k)
            unique.append(step)

    return "\n".join(f"{i}. {step}" for i, step in enumerate(unique[:5], 1))


def _build_mendalam(sentences: list[str], q_type: str) -> str:
    parts: list[str] = []
    for i, sent in enumerate(sentences[:4]):
        s = _normalize(sent)
        if i == 0:
            parts.append(s)
        else:
            conn = _CONNECTORS[(i - 1) % len(_CONNECTORS)]
            parts.append(f"{conn} {s[0].lower()}{s[1:]}" if s else s)

    if len(sentences) > 4:
        extra = " ".join(_normalize(s) for s in sentences[4:6])
        if extra:
            parts.append(f"Kesimpulan: {extra[:220]}...")

    return "\n\n".join(parts)


def _intro(mode: str, q_type: str) -> str:
    if mode == "ringkas":
        return ""
    if mode == "langkah":
        return "Langkah penjelasan menurut materi:"
    intros = {
        "why": "Penjelasan penyebab menurut materi:",
        "how": "Penjelasan proses menurut materi:",
        "what": "Penjelasan konsep menurut materi:",
        "myth": "Informasi mitos/kepercayaan dalam materi:",
        "list": "Poin-poin dalam materi:",
        "general": "Penjelasan menurut materi:",
    }
    return intros.get(q_type, intros["general"])


def _extract_key_points(sentences: list[str], max_points: int = 4) -> list[str]:
    points: list[str] = []
    for sent in sentences:
        short = sent if len(sent) <= 100 else sent[:97] + "..."
        points.append(short)
        if len(points) >= max_points:
            break
    return points


def compose_tutor_answer(
    question: str,
    context: str,
    qa_span: str,
    *,
    mode: str = "mendalam",
) -> dict:
    q_type = classify_question(question)
    
    # 1. Split context into original sentences
    sentences = split_sentences(context)
    if not sentences:
        return {
            "answer": _not_found_message(question),
            "key_points": [],
            "source_quote": "",
            "question_type": q_type,
            "mode": mode,
        }

    # 2. Temukan indeks kalimat utama (core_idx) yang memuat span jawaban mT5
    core_idx = -1
    if qa_span and qa_span.strip():
        span_clean = qa_span.strip().lower()
        for idx, sent in enumerate(sentences):
            if span_clean in sent.lower() or sent.lower() in span_clean:
                core_idx = idx
                break

    # Jika span tidak ditemukan secara eksplisit, cari kalimat dengan kecocokan tertinggi
    if core_idx == -1:
        scored = [(score_sentence(sent, question), idx) for idx, sent in enumerate(sentences)]
        scored.sort(key=lambda x: -x[0])
        if scored and scored[0][0] >= 0.10:
            core_idx = scored[0][1]
        else:
            core_idx = 0 # fallback ke kalimat pertama jika tidak ada yang cocok

    # Evaluasi kecocokan tertinggi untuk mendeteksi out-of-context
    top_score = score_sentence(sentences[core_idx], question)
    if top_score < 0.10 and not qa_span:
        return {
            "answer": _not_found_message(question),
            "key_points": [],
            "source_quote": "",
            "question_type": q_type,
            "mode": mode,
        }

    # 3. Ambil kalimat tetangga secara KRONOLOGIS berurutan agar jawaban mengalir padu dan lengkap
    picked_indices = []
    if mode == "ringkas":
        # Ringkas: hanya kalimat utama yang padat
        picked_indices = [core_idx]
    elif mode == "langkah":
        # Langkah: kalimat utama ditambah hingga 3 kalimat setelahnya secara berurutan
        picked_indices = [core_idx + i for i in range(4) if core_idx + i < len(sentences)]
    else:
        # Mendalam: 1 kalimat sebelum, kalimat utama, dan hingga 2-3 kalimat setelahnya
        start = max(0, core_idx - 1)
        end = min(len(sentences), core_idx + 3)
        picked_indices = list(range(start, end))

    # Kumpulkan kalimat
    ranked = [sentences[idx] for idx in picked_indices]
    if not ranked:
        ranked = [sentences[core_idx]]

    # 4. Susun jawaban akhir secara kohesif
    if mode == "ringkas":
        body = _normalize(ranked[0])
        # Potong jika terlalu panjang untuk diringkas
        if len(body) > 180:
            body = body[:177] + "..."
        key_points = []
    elif mode == "langkah":
        steps = []
        for sent in ranked:
            items = _extract_list_items(sent)
            if items:
                steps.extend(items)
            else:
                steps.append(_normalize(sent))
        # Pastikan unik
        unique_steps = []
        seen_steps = set()
        for step in steps:
            k = step.lower()[:40]
            if k not in seen_steps:
                seen_steps.add(k)
                unique_steps.append(step)
        body = "\n".join(f"{i}. {step}" for i, step in enumerate(unique_steps[:5], 1))
        key_points = []
    else:
        # Mendalam: Gabungkan kalimat secara kronologis natural dalam satu paragraf utuh
        body = " ".join(_normalize(sent) for sent in ranked)
        key_points = [_normalize(sent) for sent in ranked[:4]]

    intro = _intro(mode, q_type)
    answer = f"{intro}\n\n{body}".strip() if intro else body.strip()

    return {
        "answer": answer,
        "key_points": key_points,
        "source_quote": sentences[core_idx][:180] + ("..." if len(sentences[core_idx]) > 180 else ""),
        "question_type": q_type,
        "mode": mode,
    }
