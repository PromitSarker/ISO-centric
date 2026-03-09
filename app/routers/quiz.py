from fastapi import APIRouter

from app.core.models import QuizRequest, QuizResponse
from app.services.quiz import generate_quiz

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz Generator"])


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz_endpoint(request: QuizRequest):
    """
    Quiz Generator — create a multiple-choice quiz from any JSON context.

    **Input:**
    - `context` *(required)*: Any JSON object describing the topic, subject matter,
      or structured content the quiz should be based on.
    - `num_questions`: How many questions to generate (1–20, default 5).
    - `difficulty`: `"easy"`, `"intermediate"` (default), or `"hard"`.

    **Output:**
    - A `quiz_title` and list of questions, each containing:
      - The question text
      - Four answer options (A–D)
      - The correct answer key
      - A brief explanation
    """
    result = await generate_quiz(
        context=request.context,
        num_questions=request.num_questions,
        difficulty=request.difficulty,
    )
    return QuizResponse(**result)
