import asyncio
import json
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.models import QuizResponse
from app.services.benchmark import extract_text_from_file
from app.services.quiz import generate_quiz, generate_quiz_stream

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz Generator"])


def _parse_context(raw_context: str) -> dict:
    if not raw_context or not raw_context.strip():
        return {}
    try:
        parsed = json.loads(raw_context)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON in context") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="context must be a JSON object")
    return parsed


async def _extract_uploaded_file(file: UploadFile) -> dict:
    content = await file.read()
    try:
        file_text = await extract_text_from_file(file, content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to process file {file.filename}: {str(exc)}") from exc
    return {
        "file_name": file.filename,
        "file_text": file_text,
    }


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz_endpoint(
    context: str = Form("{}", description="JSON string of context data"),
    num_questions: int = Form(5, ge=1, le=30, description="How many questions to generate (1-30)"),
    difficulty: str = Form("intermediate", description="easy, intermediate, or hard"),
    files: Optional[List[UploadFile]] = File(None),
):
    """
    Quiz Generator — create a multiple-choice quiz from any JSON context.

    **Input:**
    - `context` *(optional)*: JSON string describing the topic, subject matter,
      or structured content the quiz should be based on.
    - `num_questions`: How many questions to generate (1–30, default 5).
    - `difficulty`: `"easy"`, `"intermediate"`, or `"hard"` (default: `"intermediate"`).
    - `files`: Optional file uploads to generate the quiz from.

    **Output:**
    - A `quiz_title` and list of questions, each containing:
      - The question text
      - Four answer options (A–D)
      - The correct answer key
      - A brief explanation
    """
    parsed_context = _parse_context(context)

    if files:
        uploaded_files_data = await asyncio.gather(*[_extract_uploaded_file(file) for file in files])
        parsed_context["uploaded_files"] = uploaded_files_data

    result = await generate_quiz(
        context=parsed_context,
        num_questions=num_questions,
        difficulty=difficulty,
    )
    return QuizResponse(**result)


@router.post("/generate/stream")
async def generate_quiz_stream_endpoint(
    context: str = Form("{}", description="JSON string of context data"),
    num_questions: int = Form(5, ge=1, le=30, description="How many questions to generate (1-30)"),
    difficulty: str = Form("intermediate", description="easy, intermediate, or hard"),
    files: Optional[List[UploadFile]] = File(None),
):
    """
    Quiz Generator Stream — identical to `/generate` but streams the raw JSON string output as it generates.
    This allows the client to provide immediate feedback and visual progression for the user.
    """
    parsed_context = _parse_context(context)

    if files:
        uploaded_files_data = await asyncio.gather(*[_extract_uploaded_file(file) for file in files])
        parsed_context["uploaded_files"] = uploaded_files_data

    # Return stream directly. Format is text/event-stream or application/x-ndjson depending on how the frontend prefers it.
    # We output raw partial JSON text. 
    return StreamingResponse(
        generate_quiz_stream(
            context=parsed_context,
            num_questions=num_questions,
            difficulty=difficulty,
        ),
        media_type="text/plain",
    )
