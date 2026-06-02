"""Generate saran pertanyaan kontekstual dari isi materi."""
from __future__ import annotations

import re

from app.answer_builder import split_sentences

_STOP = {
    "yang", "dari", "pada", "dalam", "ini", "itu", "dan", "atau", "untuk",
    "dengan", "adalah", "akan", "dapat", "bisa", "juga", "saja", "oleh",
    "agar", "saat", "ketika", "menjadi", "secara", "para", "hal", "nya",
    "oleh", "sangat", "lebih", "telah", "sudah", "hanya", "semua", "adapun",
    "karena", "sebab", "oleh", "secara", "sebagai", "tentang", "maka", "tetapi",
}


def is_valid_term(t: str) -> bool:
    """Melakukan penyaringan ketat untuk memblokir istilah jurnal, prodi, dan metadata non-konseptual."""
    t_clean = t.strip()
    if len(t_clean) < 4:
        return False
    t_lower = t_clean.lower()
    
    # Daftar hitam metadata publikasi ilmiah, nama kampus, header halaman
    blacklist = [
        "jurnal", "pendidikan", "teknologi", "vol", "volume", "issn", "e-issn", "halaman", "hal ", 
        "prodi", "studi", "politeknik", "caltex", "riau", "pekanbaru", "tugas akhir", "skripsi", 
        "dosen", "mahasiswa", "abstract", "abstrak", "pendahuluan", "daftar pustaka", "penerbit", 
        "author", "penulis", "editor", "proceedings", "conference", "ta 20", "kelompok", "analisis teks", 
        "tabel", "gambar", "note", "catatan", "proyek", "dikerjakan", "masing-masing", "sistem dari", 
        "hulu", "hilir", "kelompok", "analisis", "pengujian", "dan sensor"
    ]
    for kw in blacklist:
        if kw in t_lower:
            return False
            
    # Singkirkan frasa yang diawali konjungsi mentah
    if t_lower.startswith("dan ") or t_lower.startswith("atau ") or t_lower.startswith("yang ") or t_lower.startswith("dengan ") or t_lower.startswith("berbasis ") or t_lower.startswith("menggunakan "):
        return False
        
    # Singkirkan angka murni, atau yang didominasi angka
    if re.search(r"^\d+$", t_clean) or (len(re.findall(r"\d", t_clean)) / len(t_clean) > 0.25):
        return False
        
    return True


def _clean_term(term: str) -> str:
    """Bersihkan term agar terlihat rapi dan alami sebagai subjek."""
    t = re.sub(r"\s+", " ", term.strip())
    t = re.sub(r"^[,\-\.\s]+|[,\-\.\s]+$", "", t)
    
    # Bersihkan konjungsi ALL CAPS atau Title Case di depan subject
    t = re.sub(r"^(dan|atau|yang|dari|pada|dalam|ini|itu|dengan|berbasis|menggunakan|of|the|with|and|or|by|for)\s+", "", t, flags=re.I)
    t = re.sub(r"^(sebuah|suatu|para|list|antara)\s+", "", t, flags=re.I)
    t = t.strip(" \"'*`()[]{}")
    return t[:55].strip()


def _extract_rich_terms(text: str, limit: int = 10) -> list[str]:
    """Ekstrak kata/istilah teknis penting yang mewakili konteks materi secara cerdas."""
    # Lewati halaman sampul/metadata di awal dokumen panjang untuk mengambil konsep asli
    analysis_text = text
    if len(text) > 2500:
        analysis_text = text[1500:9500]

    terms: list[str] = []
    seen: set[str] = set()

    def add(t: str) -> None:
        t = _clean_term(t)
        if not is_valid_term(t) or t.lower() in _STOP:
            return
        k = t.lower()
        if k not in seen and not any(k in s for s in seen):
            seen.add(k)
            terms.append(t)

    # 1. Istilah kapital gabungan (misal: "Stemming dan Lemmatization", "Stopword Removal")
    for m in re.finditer(r"\b([A-Z][a-zA-Z]+(?:\s+(?:dan|atau|of|the|with)\s+[a-zA-Z]+)?(?:\s+[A-Z][a-zA-Z]+){1,3})\b", analysis_text):
        add(m.group(1))

    # 2. Istilah teknis NLP/Pendidikan/Sistem Cerdas populer yang ada dalam teks
    tech_keywords = [
        r"stemming", r"lemmatization", r"stopword", r"tokenization", r"corpus", 
        r"korpus", r"dataset", r"preprocessing", r"regular expression", r"regex",
        r"fotosintesis", r"gerhana", r"klorofil", r"indera", r"listrik", r"energi",
        r"algoritma", r"klasifikasi", r"akurasi", r"pengujian", r"analisis", r"rfid",
        r"sensor", r"infrared", r"mikrokontroler", r"database", r"pemantauan", r"monitoring",
        r"gizi", r"nutrisi", r"makanan", r"stunting", r"pangan", r"kesehatan", r"sistem cerdas",
        r"deep learning", r"blockchain", r"iot", r"neural network", r"machine learning"
    ]
    for kw in tech_keywords:
        for m in re.finditer(r"\b(" + kw + r"[a-zA-Z]*)\b", analysis_text, re.I):
            add(m.group(1))

    # 3. Definisional patterns ("X adalah Y", "X merupakan Y")
    for m in re.finditer(r"\b([a-zA-ZÀ-ü\s]{3,35})\s+(?:adalah|merupakan|ialah|yaitu|didefinisikan)\b", analysis_text):
        add(m.group(1))

    # 4. Berdasarkan kata benda berulang (frekuensi tinggi)
    words = re.findall(r"\b[a-zA-Z]{5,20}\b", analysis_text)
    freq: dict[str, int] = {}
    for w in words:
        wl = w.lower()
        if wl not in _STOP and len(wl) > 4:
            freq[wl] = freq.get(wl, 0) + 1
            
    for wl, c in sorted(freq.items(), key=lambda x: -x[1]):
        if c >= 2:
            add(wl.capitalize())

    return terms[:limit]


def is_valid_sentence(s: str) -> bool:
    """Melakukan penyaringan ketat untuk mendeteksi kalimat sampah atau tidak berguna."""
    s_clean = s.strip()
    # Kalimat tidak boleh terlalu pendek atau terlalu panjang
    if len(s_clean) < 35 or len(s_clean) > 300:
        return False
        
    # Tolak kalimat dengan karakter pemisah atau simbol berulang (dashes, underscores, dll)
    if re.search(r"[-_=\*\.]{3,}", s_clean) or "--" in s_clean or "__" in s_clean or "==" in s_clean:
        return False
        
    # Tolak jika persentase karakter alfanumerik terlalu rendah (biasanya sampah/tabel/kode)
    word_chars = len(re.findall(r"[a-zA-Z0-9À-ü\s]", s_clean))
    if len(s_clean) > 0 and (word_chars / len(s_clean)) < 0.85:
        return False

    # Tolak baris kode pemrograman dasar
    code_keywords = [
        r"\bdef\b", r"\bclass\b", r"\bimport\b", r"\breturn\b", r"\bconst\b", 
        r"\blet\b", r"\bfunction\b", r"[{}\[\];=\(\)\+\-]{4,}"
    ]
    for kw in code_keywords:
        if re.search(kw, s_clean):
            return False

    # Tolak kalimat bernada instruksi sistem, tugas, metadata, atau tutorial
    system_keywords = [
        "tutorial", "klik", "halaman", "unduh", "download", "link", "website",
        "tabel di atas", "gambar di bawah", "catatan:", "note:", "silakan", "di atas", "di bawah",
        "http", "www", "email", "telepon", "bab berikut", "maksud kalimat", "kelompok", "dikerjakan"
    ]
    s_lower = s_clean.lower()
    if any(kw in s_lower for kw in system_keywords):
        return False
        
    return True


def _questions_from_sentence(sentence: str) -> list[str]:
    """Ubah kalimat materi secara semantis menjadi pertanyaan alami."""
    s = sentence.strip()
    if not is_valid_sentence(s):
        return []

    qs: list[str] = []
    lower = s.lower()

    # 1. Pola definisional klasik ("X adalah Y")
    m = re.search(r"\b([a-zA-ZÀ-ü\s]{3,40}?)\s+(?:adalah|merupakan|ialah|yaitu)\s+(.{15,})", s, re.I)
    if m:
        subj = _clean_term(m.group(1))
        # Pastikan subject bersih dan tidak mengandung kata sampah
        if len(subj) > 3 and not any(w in subj.lower() for w in ["jelaskan", "sebutkan", "tutorial", "klik", "maksud", "kelompok"]):
            qs.append(f"Apa yang dimaksud dengan {subj} menurut materi?")
            if "karena" in lower or "sebab" in lower:
                qs.append(f"Mengapa {subj} penting dalam proses ini?")

    # 2. Perbandingan (misal: "Antara Stemming dan Lemmatization...")
    if "antara" in lower and ("dan" in lower or "vs" in lower) and len(s) > 40:
        match = re.search(r"between\s+([A-Za-z]+)\s+and\s+([A-Za-z]+)|antara\s+([A-Za-z]+)\s+dan\s+([A-Za-z]+)", lower)
        if match:
          t1 = match.group(1) or match.group(3)
          t2 = match.group(2) or match.group(4)
          if len(t1) > 3 and len(t2) > 3 and not any(w in t1.lower() or w in t2.lower() for w in ["kelompok", "maksud"]):
              qs.append(f"Apa perbedaan utama antara {t1.capitalize()} dan {t2.capitalize()}?")
              qs.append(f"Bagaimana cara memilih penggunaan antara {t1.capitalize()} dan {t2.capitalize()}?")

    # 3. Proses / Implementasi / Cara kerja
    if any(k in lower for k in ["tahap", "proses", "langkah", "metode", "cara kerja"]):
        subj = _extract_subject(s)
        if subj and len(subj) > 3 and not any(w in subj.lower() for w in ["kelompok", "maksud", "tuliskan"]):
            qs.append(f"Jelaskan tahapan atau proses {subj.lower()} yang dibahas!")
            qs.append(f"Bagaimana cara kerja {subj.lower()} berdasarkan teks?")

    # 4. Fungsi / Dampak / Pentingnya
    if any(k in lower for k in ["fungsi", "peran", "penting", "dampak", "pengaruh"]):
        subj = _extract_subject(s)
        if subj and len(subj) > 3 and not any(w in subj.lower() for w in ["kelompok", "maksud"]):
            qs.append(f"Apa fungsi utama dari {subj.lower()} menurut materi?")
            qs.append(f"Mengapa {subj.lower()} memiliki peran penting dalam teks?")

    # 5. Kehadiran data/dataset
    if "dataset" in lower or "data" in lower:
        if not "kelompok" in lower:
            qs.append("Bagaimana karakteristik dataset atau data yang digunakan dalam teks?")

    return qs


def _extract_subject(sentence: str) -> str:
    m = re.match(r"^([A-Za-zÀ-ü\s]{3,40}?)\s+(?:adalah|merupakan|terjadi|dapat|memiliki|digunakan)", sentence)
    if m:
        return _clean_term(m.group(1))
    
    # fallback to common technical terms
    m = re.search(r"\b(stemming|lemmatization|stopword|tokenization|dataset|fotosintesis|gerhana|word embedding)\b", sentence, re.I)
    if m:
        return _clean_term(m.group(1))
    return ""


def generate_suggestions(text: str, count: int = 6) -> list[str]:
    text = (text or "").strip()
    if len(text) < 30:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = re.sub(r"\s+", " ", q.strip())
        if len(q) < 15 or len(q) > 130 or q.endswith('""') or q.endswith('""?'):
            return
        q = q.replace('""', '"')
        
        q_lower = q.lower()
        if "--" in q or "__" in q or "==" in q or "..." in q:
            return
        if re.search(r"[-_=\*\.\(\)\[\]\{\}]{2,}", q):
            return
            
        # Tolak mentah-mentah jika mengandung istilah sampah tugas atau kepengurusan kelompok
        junk_keywords = ["maksud kalimat", "kelompok", "dikerjakan oleh", "tutorial", "klik", "halaman", "tabel", "gambar", "note:", "catatan:", "http"]
        if any(kw in q_lower for kw in junk_keywords):
            return

        # Pastikan huruf awal kapital
        q = q[0].upper() + q[1:]
        k = q.lower()
        if k not in seen:
            seen.add(k)
            candidates.append(q)

    # 1. Dapatkan dari Istilah Teknis Penting Terlebih Dahulu (Prioritas Utama untuk Pertanyaan Konseptual Premium)
    terms = _extract_rich_terms(text, limit=12)
    # Bersihkan terms dari simbol atau kurung
    clean_terms = []
    for t in terms:
        t_clean = re.sub(r"[-_=\*\.\(\)\[\]\{\}]", "", t).strip()
        t_lower = t_clean.lower()
        if len(t_clean) > 3 and not any(k in t_lower for k in ["kelompok", "maksud", "kalimat", "tabel", "gambar"]):
            clean_terms.append(t_clean)

    if len(clean_terms) >= 1:
        add(f"Apa yang dimaksud dengan {clean_terms[0]} menurut materi?")
        add(f"Bagaimana cara kerja dan penerapan {clean_terms[0]} yang dijelaskan?")
    if len(clean_terms) >= 2:
        add(f"Apa perbedaan utama konsep antara {clean_terms[0]} dan {clean_terms[1]}?")
        add(f"Jelaskan hubungan konsep antara {clean_terms[0]} dengan {clean_terms[1]}!")
    if len(clean_terms) >= 3:
        add(f"Mengapa {clean_terms[2]} dianggap penting dalam materi tersebut?")
        add(f"Bagaimana peranan {clean_terms[2]} terhadap keseluruhan bahasan?")
    if len(clean_terms) >= 4:
        add(f"Sebutkan klasifikasi atau pembagian dari {clean_terms[3]} yang dibahas!")

    # 2. Dapatkan pertanyaan kontekstual dari kalimat-kalimat berkualitas (lewati metadata awal)
    analysis_text_sents = text[1200:10000] if len(text) > 2000 else text
    sentences = split_sentences(analysis_text_sents)
    valid_sents = [s for s in sentences if is_valid_sentence(s)]
    
    for sent in valid_sents[:10]:
        for q in _questions_from_sentence(sent):
            add(q)

    # 3. Fallback cerdas & natural jika kandidat kurang (tanpa menggunakan template kalimat kaku)
    if len(candidates) < count:
        common_templates = [
            "Apa kesimpulan atau inti sari dari modul yang diunggah?",
            "Bagaimana implementasi metode yang dijelaskan dalam teks?",
            "Sebutkan poin penting atau temuan utama dalam materi tersebut!",
            "Apa tujuan utama dari pengujian atau analisis dalam dokumen?"
        ]
        for t in common_templates:
            add(t)

    # Batasi sesuai jumlah yang diminta
    return candidates[:count]
