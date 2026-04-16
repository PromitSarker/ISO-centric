import json
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.models import QuizResponse
from app.services.benchmark import extract_text_from_file
from app.services.quiz import generate_quiz

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


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz_endpoint(
    context: str = Form("{}", description="JSON string of context data"),
    num_questions: int = Form(5, description="How many questions to generate (1–20)"),
    difficulty: str = Form("intermediate", description="easy, intermediate, or hard"),
    files: Optional[List[UploadFile]] = File(None),
):
    """
    Quiz Generator — create a multiple-choice quiz from any JSON context.

    **Input:**
    - `context` *(optional)*: JSON string describing the topic, subject matter,
      or structured content the quiz should be based on.
    - `num_questions`: How many questions to generate (1–20, default 5).
    - `difficulty`: `"easy"`, `"intermediate"` (default), or `"hard"`.
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
        uploaded_files_data = []
        for file in files:
            content = await file.read()
            try:
                file_text = await extract_text_from_file(file, content)
                uploaded_files_data.append({
                    "file_name": file.filename,
                    "file_text": file_text
                })
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Failed to process file {file.filename}: {str(exc)}") from exc
        
        parsed_context["uploaded_files"] = uploaded_files_data

    result = await generate_quiz(
        context=parsed_context,
        num_questions=num_questions,
        difficulty=difficulty,
    )
    return QuizResponse(**result)
