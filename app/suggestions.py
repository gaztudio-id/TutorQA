"""Generate saran pertanyaan kontekstual dari isi materi.

Alur kerja:
1. Deteksi domain bidang ilmu (teknologi / sains / kesehatan / matematika / sosial / umum)
2. Ekstrak istilah teknis/konsep kunci dari teks secara adaptif
3. Generate pertanyaan dari template sesuai domain + istilah yang ditemukan
4. Tambah pertanyaan kontekstual dari kalimat-kalimat berkualitas dalam materi
5. Fallback umum jika kandidat kurang
"""
from __future__ import annotations

import re
from collections import Counter

from app.answer_builder import split_sentences

# ──────────────────────────────────────────────────────────────────────────────
# Stop words Bahasa Indonesia & Inggris dasar
# ──────────────────────────────────────────────────────────────────────────────
_STOP: set[str] = {
    "yang", "dari", "pada", "dalam", "ini", "itu", "dan", "atau", "untuk",
    "dengan", "adalah", "akan", "dapat", "bisa", "juga", "saja", "oleh",
    "agar", "saat", "ketika", "menjadi", "secara", "para", "hal", "nya",
    "sangat", "lebih", "telah", "sudah", "hanya", "semua", "adapun",
    "karena", "sebab", "sebagai", "tentang", "maka", "tetapi", "jika",
    "namun", "serta", "yaitu", "yakni", "bahwa", "supaya", "setelah",
    "sebelum", "ketika", "meski", "walaupun",
}

# ──────────────────────────────────────────────────────────────────────────────
# Metadata / junk blacklist — baris yang bukan konsep ilmiah
# ──────────────────────────────────────────────────────────────────────────────
_BLACKLIST: set[str] = {
    "jurnal", "pendidikan", "vol", "volume", "issn", "halaman", "hal",
    "prodi", "politeknik", "caltex", "riau", "pekanbaru", "tugas akhir",
    "skripsi", "dosen", "mahasiswa", "abstract", "abstrak", "pendahuluan",
    "daftar pustaka", "penerbit", "author", "penulis", "proceedings",
    "conference", "kelompok", "tabel", "gambar", "note", "catatan",
    "proyek", "dikerjakan", "teknologi",  # terlalu generic
    "prakata", "kata pengantar", "pengantar", "daftar isi", "daftar gambar",
    "daftar tabel", "bab", "kesimpulan", "saran", "ucapan terima kasih",
}

# Kata yang tidak boleh mengawali sebuah term
_CONJ_PREFIX = re.compile(
    r"^(dan|atau|yang|dari|pada|dalam|ini|itu|dengan|berbasis|menggunakan"
    r"|of|the|with|and|or|by|for|sebuah|suatu|para|list|antara)\s+",
    re.IGNORECASE,
)

# ──────────────────────────────────────────────────────────────────────────────
# Sinyal keyword per domain untuk deteksi otomatis
# ──────────────────────────────────────────────────────────────────────────────
_DOMAIN_SIGNALS: dict[str, list[str]] = {
    "teknologi": [
        "algoritma", "neural network", "deep learning", "machine learning",
        "database", "iot", "blockchain", "preprocessing", "dataset",
        "klasifikasi", "model", "akurasi", "training", "tokenization",
        "stemming", "nlp", "sensor", "mikrokontroler", "jaringan saraf",
        "backpropagation", "epoch", "layer", "relu", "gradient", "optimizer",
        "convolutional", "recurrent", "lstm", "transformer", "inference",
        "overfitting", "underfitting", "regularisasi", "fungsi aktivasi",
        "jaringan syaraf", "kecerdasan buatan", "computer vision",
    ],
    "sains": [
        "fotosintesis", "sel", "mitokondria", "atom", "molekul", "reaksi kimia",
        "energi", "listrik", "gravitasi", "klorofil", "gerhana", "planet",
        "organisme", "ekosistem", "dna", "gen", "kromosom", "evolusi",
        "gelombang", "magnet", "suhu", "tekanan", "cahaya", "oksigen",
        "karbon dioksida", "fotosintesis", "respirasi", "metamorfosis",
    ],
    "kesehatan": [
        "gizi", "nutrisi", "kalori", "protein", "karbohidrat", "lemak",
        "vitamin", "mineral", "stunting", "obesitas", "penyakit", "virus",
        "bakteri", "imun", "vaksin", "obat", "terapi", "diagnosa",
        "kesehatan", "medis", "klinis", "patologi", "farmasi",
    ],
    "matematika": [
        "persamaan", "fungsi", "integral", "turunan", "matriks", "vektor",
        "probabilitas", "statistik", "geometri", "trigonometri", "logaritma",
        "limit", "barisan", "deret", "kombinatorika", "bilangan", "himpunan",
        "grafik", "koordinat",
    ],
    "sosial": [
        "sejarah", "budaya", "masyarakat", "ekonomi", "politik", "hukum",
        "geografi", "demografi", "pemerintah", "negara", "perang", "kerajaan",
        "revolusi", "kolonial", "nasionalisme", "globalisasi", "sosiologi",
        "antropologi", "ideologi", "konflik", "diplomasi",
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# Template pertanyaan per domain
# Placeholder: {term} = satu istilah, {term0}/{term1} = dua istilah berbeda
# ──────────────────────────────────────────────────────────────────────────────
_DOMAIN_TEMPLATES: dict[str, list[str]] = {
    "teknologi": [
        "Apa yang dimaksud dengan {term} menurut materi?",
        "Bagaimana cara kerja {term} dalam konteks sistem yang dijelaskan?",
        "Apa keunggulan dan kelemahan dari {term} berdasarkan materi?",
        "Bagaimana proses atau tahapan {term} berlangsung?",
        "Apa perbedaan antara {term0} dan {term1} dari sisi teknis?",
        "Mengapa {term} menjadi komponen penting dalam arsitektur yang dibahas?",
        "Bagaimana {term} diimplementasikan dalam contoh atau studi kasus yang ada?",
        "Jelaskan peran {term} terhadap performa keseluruhan sistem!",
    ],
    "sains": [
        "Apa yang dimaksud dengan {term} menurut materi?",
        "Bagaimana proses {term} terjadi secara alami?",
        "Apa yang menyebabkan {term} dapat berlangsung?",
        "Jelaskan mekanisme {term} berdasarkan penjelasan dalam materi!",
        "Apa hubungan antara {term0} dan {term1} dalam materi?",
        "Mengapa {term} penting bagi keberlangsungan proses yang dijelaskan?",
        "Apa dampak jika {term} tidak berjalan sebagaimana mestinya?",
        "Bagaimana {term} berpengaruh terhadap sistem yang dibahas?",
    ],
    "kesehatan": [
        "Apa yang dimaksud dengan {term} menurut materi?",
        "Apa peran {term} bagi kesehatan tubuh menurut penjelasan?",
        "Bagaimana kekurangan {term} berdampak pada kondisi kesehatan?",
        "Jelaskan hubungan antara {term0} dan {term1} dalam konteks kesehatan!",
        "Apa gejala atau dampak dari masalah yang berkaitan dengan {term}?",
        "Bagaimana cara mencegah kondisi yang berhubungan dengan {term}?",
        "Sebutkan sumber alami atau cara memenuhi kebutuhan {term}!",
    ],
    "matematika": [
        "Apa yang dimaksud dengan konsep {term} dalam materi?",
        "Bagaimana cara menerapkan {term} pada soal atau kasus yang diberikan?",
        "Apa syarat yang harus dipenuhi dalam penggunaan {term}?",
        "Jelaskan perbedaan antara {term0} dan {term1}!",
        "Bagaimana {term} berhubungan dengan konsep lain yang dibahas?",
        "Apa langkah-langkah penyelesaian menggunakan metode {term}?",
    ],
    "sosial": [
        "Apa yang dimaksud dengan {term} menurut materi?",
        "Apa faktor penyebab terjadinya {term} menurut penjelasan?",
        "Bagaimana {term} mempengaruhi kehidupan masyarakat yang dijelaskan?",
        "Jelaskan hubungan antara {term0} dan {term1} dalam konteks yang dibahas!",
        "Apa dampak dari {term} terhadap perkembangan yang dibicarakan?",
        "Mengapa {term} menjadi titik balik penting dalam materi?",
        "Bagaimana peran {term} dalam membentuk kondisi yang ada saat ini?",
    ],
    "umum": [
        "Apa yang dimaksud dengan {term} menurut materi?",
        "Bagaimana {term} berperan dalam konteks yang dibahas?",
        "Jelaskan konsep {term} beserta contoh penerapannya!",
        "Apa perbedaan antara {term0} dan {term1}?",
        "Mengapa {term} dianggap penting dalam materi ini?",
        "Bagaimana cara kerja atau mekanisme dari {term}?",
        "Apa manfaat nyata dari pemahaman tentang {term}?",
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# Fungsi internal
# ──────────────────────────────────────────────────────────────────────────────

def _clean_term(term: str) -> str:
    """Bersihkan term agar terlihat rapi dan alami sebagai subjek kalimat."""
    t = re.sub(r"\s+", " ", term.strip())
    t = re.sub(r"^[,\-\.\s]+|[,\-\.\s]+$", "", t)
    t = _CONJ_PREFIX.sub("", t)
    t = t.strip(" \"'*`()[]{}≡•→▸")
    return t[:60].strip()


def _is_valid_term(t: str) -> bool:
    """Kembalikan True jika term adalah konsep ilmiah/pendidikan yang valid."""
    t_clean = t.strip()
    if len(t_clean) < 4:
        return False
    t_lower = t_clean.lower()
    if any(kw in t_lower for kw in _BLACKLIST):
        return False
    if _CONJ_PREFIX.match(t_lower):
        return False
    # Tolak jika didominasi angka (>30%)
    digits = len(re.findall(r"\d", t_clean))
    if re.match(r"^\d+$", t_clean) or digits / len(t_clean) > 0.3:
        return False
    return True


def _is_valid_sentence(s: str) -> bool:
    """Kembalikan True jika kalimat layak dijadikan sumber pertanyaan."""
    s = s.strip()
    if len(s) < 35 or len(s) > 300:
        return False
    if re.search(r"[-_=\*\.]{3,}", s) or "--" in s or "__" in s:
        return False
    alphanum = len(re.findall(r"[a-zA-Z0-9À-ü\s]", s))
    if len(s) > 0 and (alphanum / len(s)) < 0.85:
        return False
    code_pats = [r"\bdef\b", r"\bclass\b", r"\bimport\b", r"\breturn\b", r"[{}\[\];=\(\)]{4,}"]
    if any(re.search(p, s) for p in code_pats):
        return False
    system_kw = [
        "tutorial", "klik", "unduh", "download", "http", "www",
        "tabel di atas", "gambar di bawah", "catatan:", "note:",
        "silakan", "bab berikut", "kelompok", "dikerjakan",
    ]
    s_lower = s.lower()
    return not any(kw in s_lower for kw in system_kw)


def _detect_domain(text: str) -> str:
    """Deteksi domain/bidang ilmu dari teks secara otomatis."""
    text_lower = text.lower()
    scores: dict[str, int] = {domain: 0 for domain in _DOMAIN_SIGNALS}
    for domain, signals in _DOMAIN_SIGNALS.items():
        for signal in signals:
            if signal in text_lower:
                scores[domain] += 1
    best = max(scores, key=lambda d: scores[d])
    # Butuh minimal 2 sinyal agar domain dianggap terdeteksi
    return best if scores[best] >= 2 else "umum"


def _extract_terms(text: str, limit: int = 12) -> list[str]:
    """Ekstrak istilah teknis/konsep penting dari teks secara adaptif."""
    # Lewati area header/metadata di awal dokumen panjang
    analysis = text[1500:9500] if len(text) > 2500 else text

    terms: list[str] = []
    seen: set[str] = set()

    def add(t: str) -> None:
        t = _clean_term(t)
        if not _is_valid_term(t):
            return
        t_low = t.lower()
        if t_low in _STOP or t_low in seen:
            return
        # Hindari duplikat substring (e.g. "Learning" sudah ada saat "Deep Learning" masuk)
        if any(t_low in s or s in t_low for s in seen):
            return
        seen.add(t_low)
        terms.append(t)

    # 1. Frasa kapital multi-kata (e.g. "Deep Learning", "Neural Network", "Loss Function")
    for m in re.finditer(
        r"\b([A-Z][a-zA-Z]+(?:\s+(?:dan|atau|of|the|with|and)?\s*[A-Z][a-zA-Z]+){0,3})\b",
        analysis,
    ):
        add(m.group(1))

    # 2. Pola definisional: "X adalah/merupakan/ialah Y"
    for m in re.finditer(
        r"\b([a-zA-ZÀ-ü][a-zA-ZÀ-ü\s]{2,35}?)\s+"
        r"(?:adalah|merupakan|ialah|yaitu|didefinisikan sebagai)\b",
        analysis,
    ):
        add(m.group(1))

    # 3. Kata benda frekuensi tinggi (≥2 kemunculan, ≥5 karakter)
    words = re.findall(r"\b[a-zA-ZÀ-ü]{5,25}\b", analysis)
    freq: Counter[str] = Counter(w.lower() for w in words if w.lower() not in _STOP)
    for word, count in freq.most_common(40):
        if count >= 2:
            add(word.capitalize())

    return terms[:limit]


def _questions_from_sentence(sentence: str) -> list[str]:
    """Ubah satu kalimat materi menjadi pertanyaan kontekstual alami."""
    s = sentence.strip()
    if not _is_valid_sentence(s):
        return []

    qs: list[str] = []
    lower = s.lower()

    # Pola definisional: "X adalah Y"
    m = re.search(
        r"\b([a-zA-ZÀ-ü\s]{3,40}?)\s+(?:adalah|merupakan|ialah|yaitu)\s+(.{15,})",
        s, re.I,
    )
    if m:
        subj = _clean_term(m.group(1))
        if len(subj) > 3 and _is_valid_term(subj):
            qs.append(f"Apa yang dimaksud dengan {subj} menurut materi?")
            if any(k in lower for k in ["karena", "sebab", "sehingga"]):
                qs.append(f"Mengapa {subj} penting dalam konteks yang dibahas?")

    # Perbandingan: "antara X dan Y"
    m2 = re.search(r"antara\s+([A-Za-zÀ-ü]+)\s+dan\s+([A-Za-zÀ-ü]+)", lower)
    if m2:
        t1 = m2.group(1).capitalize()
        t2 = m2.group(2).capitalize()
        if len(t1) > 3 and len(t2) > 3 and _is_valid_term(t1):
            qs.append(f"Apa perbedaan utama antara {t1} dan {t2}?")

    # Proses/tahapan
    if any(k in lower for k in ["tahap", "proses", "langkah", "cara kerja", "metode"]):
        m3 = re.match(
            r"^([A-Za-zÀ-ü\s]{3,35}?)\s+(?:adalah|merupakan|dapat|memiliki|digunakan)", s
        )
        if m3:
            subj = _clean_term(m3.group(1))
            if subj and _is_valid_term(subj):
                qs.append(f"Jelaskan tahapan atau proses {subj.lower()} yang dibahas!")

    # Fungsi/manfaat/dampak
    if any(k in lower for k in ["fungsi", "peran", "dampak", "pengaruh", "manfaat"]):
        m4 = re.match(
            r"^([A-Za-zÀ-ü\s]{3,35}?)\s+(?:adalah|merupakan|memiliki|berperan|berfungsi)", s
        )
        if m4:
            subj = _clean_term(m4.group(1))
            if subj and _is_valid_term(subj):
                qs.append(f"Apa fungsi atau manfaat dari {subj.lower()} menurut materi?")

    return qs


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def generate_suggestions(text: str, count: int = 6) -> list[str]:
    """Generate saran pertanyaan yang relevan dan kontekstual dari isi materi."""
    text = (text or "").strip()
    if len(text) < 30:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    _JUNK = {
        "kelompok", "dikerjakan oleh", "tutorial", "klik", "halaman",
        "tabel", "gambar", "note:", "catatan:", "http", "maksud kalimat",
    }

    def add(q: str) -> None:
        q = re.sub(r"\s+", " ", q.strip())
        if len(q) < 15 or len(q) > 150:
            return
        q_lower = q.lower()
        if any(kw in q_lower for kw in _JUNK):
            return
        if re.search(r"[-_=\*\.]{2,}", q):
            return
        q = q[0].upper() + q[1:]
        if q_lower not in seen:
            seen.add(q_lower)
            candidates.append(q)

    # ── Langkah 1: Deteksi domain bidang ilmu ─────────────────────────────────
    domain = _detect_domain(text)
    templates = _DOMAIN_TEMPLATES.get(domain, _DOMAIN_TEMPLATES["umum"])

    # ── Langkah 2: Ekstrak istilah kunci dari materi ──────────────────────────
    terms = _extract_terms(text, limit=12)
    clean_terms = [t for t in terms if _is_valid_term(t) and len(t) > 3]

    # ── Langkah 3: Buat pertanyaan dari template domain + istilah ─────────────
    for tmpl in templates:
        if "{term0}" in tmpl and "{term1}" in tmpl:
            if len(clean_terms) >= 2:
                add(tmpl.format(term0=clean_terms[0], term1=clean_terms[1]))
        elif "{term}" in tmpl:
            for term in clean_terms[:5]:
                add(tmpl.format(term=term))
                if len(candidates) >= count * 2:
                    break
        if len(candidates) >= count * 2:
            break

    # ── Langkah 4: Pertanyaan kontekstual dari kalimat dalam materi ───────────
    sample_text = text[1200:10000] if len(text) > 2000 else text
    for sent in split_sentences(sample_text)[:15]:
        for q in _questions_from_sentence(sent):
            add(q)

    # ── Langkah 5: Fallback jika kandidat masih kurang ───────────────────────
    if len(candidates) < count:
        for fb in [
            "Apa kesimpulan atau inti dari materi yang diunggah?",
            "Bagaimana implementasi konsep utama yang dijelaskan dalam teks?",
            "Sebutkan poin-poin penting atau temuan utama dalam materi!",
        ]:
            add(fb)

    return candidates[:count]
