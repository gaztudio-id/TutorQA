"""API FastAPI untuk Sistem QA Belajar Mandiri."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.document import extract_text_from_pdf
from app.inference import answer_from_document, answer_question
from app.suggestions import generate_suggestions

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

AnswerMode = Literal["ringkas", "mendalam", "langkah"]

app = FastAPI(
    title="TutorQA — Sistem Tanya Jawab Belajar Mandiri",
    description="QA interaktif berbasis fine-tuning mT5 untuk pendampingan belajar mandiri siswa",
    version="1.1.0",
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

_documents: dict[str, dict] = {}


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    document_id: str | None = None
    context: str | None = None
    mode: AnswerMode = "mendalam"


class AskResponse(BaseModel):
    answer: str
    key_points: list[str] = []
    source_quote: str = ""
    question_type: str = "general"
    mode: str = "mendalam"
    context_used: str = ""
    document_id: str | None = None


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    char_count: int
    preview: str
    suggestions: list[str] = []


class SuggestRequest(BaseModel):
    document_id: str | None = None
    context: str | None = None


class SuggestResponse(BaseModel):
    suggestions: list[str]


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/fitur", response_class=HTMLResponse)
async def fitur():
    html_path = TEMPLATES_DIR / "fitur.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/panduan", response_class=HTMLResponse)
async def panduan():
    html_path = TEMPLATES_DIR / "panduan-penggunaan.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/belajar", response_class=HTMLResponse)
async def belajar():
    html_path = TEMPLATES_DIR / "belajar.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": "mt5-qa-indonesia"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Hanya file PDF yang didukung.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Ukuran file maksimal 10 MB.")

    try:
        text = extract_text_from_pdf(content)
    except Exception as exc:
        raise HTTPException(400, f"Gagal membaca PDF: {exc}") from exc

    if not text.strip():
        raise HTTPException(400, "PDF tidak berisi teks yang dapat dibaca.")

    doc_id = str(uuid.uuid4())
    preview = text[:300].replace("\n", " ")
    _documents[doc_id] = {
        "filename": file.filename,
        "text": text,
    }

    suggestions = generate_suggestions(text)

    return UploadResponse(
        document_id=doc_id,
        filename=file.filename,
        char_count=len(text),
        preview=preview + ("..." if len(text) > 300 else ""),
        suggestions=suggestions,
    )


@app.post("/api/suggestions", response_model=SuggestResponse)
async def suggest_questions(payload: SuggestRequest):
    text = ""
    if payload.document_id:
        doc = _documents.get(payload.document_id)
        if not doc:
            raise HTTPException(404, "Dokumen tidak ditemukan.")
        text = doc["text"]
    elif payload.context and payload.context.strip():
        text = payload.context.strip()
    else:
        raise HTTPException(400, "Berikan document_id atau context.")

    return SuggestResponse(suggestions=generate_suggestions(text))


@app.post("/api/ask", response_model=AskResponse)
async def ask(payload: AskRequest):
    question = payload.question.strip()
    if not question:
        raise HTTPException(400, "Pertanyaan tidak boleh kosong.")

    mode = payload.mode

    if payload.document_id:
        doc = _documents.get(payload.document_id)
        if not doc:
            raise HTTPException(404, "Dokumen tidak ditemukan. Unggah ulang materi.")
        result = answer_from_document(question, doc["text"], mode=mode)
        return AskResponse(
            answer=result["answer"],
            key_points=result.get("key_points", []),
            source_quote=result.get("source_quote", ""),
            question_type=result.get("question_type", "general"),
            mode=result.get("mode", mode),
            context_used=result.get("context_used", ""),
            document_id=payload.document_id,
        )

    if payload.context and payload.context.strip():
        result = answer_question(question, payload.context.strip(), mode=mode)
        return AskResponse(
            answer=result["answer"],
            key_points=result.get("key_points", []),
            source_quote=result.get("source_quote", ""),
            question_type=result.get("question_type", "general"),
            mode=result.get("mode", mode),
            context_used=payload.context[:400],
        )

    raise HTTPException(
        400,
        "Unggah materi PDF atau berikan konteks teks sebelum bertanya.",
    )


@app.get("/api/documents/{document_id}")
async def get_document_meta(document_id: str):
    doc = _documents.get(document_id)
    if not doc:
        raise HTTPException(404, "Dokumen tidak ditemukan.")
    return {
        "document_id": document_id,
        "filename": doc["filename"],
        "char_count": len(doc["text"]),
        "preview": doc["text"][:400],
    }


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
