"""Inferensi model mT5 QA Indonesia + penyusunan jawaban tutor."""
from __future__ import annotations

from pathlib import Path

import torch
from transformers import MT5ForConditionalGeneration, T5Tokenizer

from app.answer_builder import compose_tutor_answer
from app.document import select_best_context, split_into_chunks

MODEL_DIR = Path(__file__).resolve().parent.parent / "mt5-qa-indonesia"

_model = None
_tokenizer = None


def _load_model():
    global _model, _tokenizer
    if _model is None:
        _tokenizer = T5Tokenizer.from_pretrained(str(MODEL_DIR))
        _model = MT5ForConditionalGeneration.from_pretrained(str(MODEL_DIR))
        _model.eval()
    return _model, _tokenizer


def build_prompt(question: str, context: str) -> str:
    return f"pertanyaan: {question.strip()} konteks: {context.strip()}"


def _extract_span(question: str, context: str) -> str:
    """Ekstrak cuplikan kunci via model QA (tahap 1)."""
    model, tokenizer = _load_model()
    prompt = build_prompt(question, context)
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        max_length=512,
        truncation=True,
    )
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=96,
            num_beams=4,
            early_stopping=True,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()


def answer_question(
    question: str,
    context: str,
    *,
    mode: str = "mendalam",
) -> dict:
    """Jawab pertanyaan dengan pipeline: ekstraksi span → susun jawaban tutor."""
    span = _extract_span(question, context)
    return compose_tutor_answer(question, context, span, mode=mode)


def answer_from_document(
    question: str,
    document_text: str,
    *,
    mode: str = "mendalam",
) -> dict:
    chunks = split_into_chunks(document_text)
    context = select_best_context(question, chunks)
    if not context.strip():
        return {
            "answer": "Tidak ada konteks materi. Unggah dokumen PDF terlebih dahulu.",
            "key_points": [],
            "source_quote": "",
            "context_used": "",
            "chunks_total": 0,
            "question_type": "general",
        }

    result = answer_question(question, context, mode=mode)
    result["context_used"] = context[:400] + ("..." if len(context) > 400 else "")
    result["chunks_total"] = len(chunks)
    return result
