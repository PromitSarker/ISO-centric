from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional

from app.core.config import DEEPSEEK_MODEL_PRO
from app.core.prompts import QUIZ_GENERATION_SYSTEM_PROMPT
from app.services.deepseek import analyze_with_deepseek, analyze_stream_with_deepseek

# ---------------------------------------------------------------------------
# In-memory question history
# ---------------------------------------------------------------------------
# Keyed by a hash of (context + iso_standard).  Stores up to MAX_HISTORY
# question strings per key so the LLM is told explicitly to avoid them.
MAX_HISTORY = 30
MAX_QUIZ_QUESTIONS = 30
MAX_AVOID_QUESTIONS_IN_PROMPT = 12
MAX_AVOID_QUESTION_CHARS = 160
MAX_PROMPT_CONTEXT_CHARS = 8000

_question_history: Dict[str, Deque[str]] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))


def _context_key(context: Dict[str, Any], iso_standard: Optional[str]) -> str:
    """Stable hash that identifies a particular context+standard combination."""
    raw = json.dumps({"ctx": context, "std": iso_standard}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _record_questions(key: str, questions: list[Dict[str, Any]]) -> None:
    """Persist the question texts from a completed quiz into the history."""
    for q in questions:
        text = q.get("question", "").strip()
        if text:
            _question_history[key].append(text)


def _trim_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}..."


def _compact_context_for_prompt(context: Dict[str, Any]) -> str:
    serialized = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(serialized) <= MAX_PROMPT_CONTEXT_CHARS:
        return serialized
    return f"{serialized[:MAX_PROMPT_CONTEXT_CHARS]}...[TRUNCATED]"


def _normalize_difficulty(difficulty: str) -> str:
    value = (difficulty or "intermediate").strip().lower()
    return value if value in {"easy", "intermediate", "hard"} else "intermediate"

QUIZ_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "quiz_title": {"type": "string"},
        "iso_standard": {"type": ["string", "null"]},
        "total_questions": {"type": "integer"},
        "difficulty": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "object",
                        "properties": {
                            "A": {"type": "string"},
                            "B": {"type": "string"},
                            "C": {"type": "string"},
                            "D": {"type": "string"},
                        },
                        "required": ["A", "B", "C", "D"],
                    },
                    "correct_answer": {"type": "string", "enum": ["A", "B", "C", "D"]},
                    "explanation": {"type": "string"},
                },
                "required": ["question", "options", "correct_answer", "explanation"],
            },
        },
        "generated_at": {"type": "string"},
    },
    "required": ["quiz_title", "questions", "total_questions", "difficulty"],
}


async def generate_quiz(
    context: Dict[str, Any],
    num_questions: int = 5,
    iso_standard: Optional[str] = None,
    difficulty: str = "intermediate",
) -> Dict[str, Any]:
    """Generate a multiple-choice quiz from the provided context JSON. This context can be module names, in which subject you have to generate quiz for the ISO learners.

    Previously seen questions (up to the last MAX_HISTORY) are injected into
    the prompt so the model actively avoids repeating them.
    """
    num_questions = max(1, min(num_questions, MAX_QUIZ_QUESTIONS))
    difficulty = _normalize_difficulty(difficulty)

    key = _context_key(context, iso_standard)
    seen = list(_question_history[key])[-MAX_AVOID_QUESTIONS_IN_PROMPT:]
    context_payload = _compact_context_for_prompt(context)

    standard_line = f"ISO Standard: {iso_standard}\n" if iso_standard else ""
    avoid_block = ""
    if seen:
        formatted = "\n".join(
            f"  {i + 1}. {_trim_text(q, MAX_AVOID_QUESTION_CHARS)}" for i, q in enumerate(seen)
        )
        avoid_block = (
            "\n\nIMPORTANT — The following questions have ALREADY been asked. "
            "Do NOT repeat or closely paraphrase any of them:\n"
            f"{formatted}\n"
        )

    prompt = (
        f"{standard_line}"
        f"Difficulty: {difficulty}\n"
        f"Number of questions: {num_questions}\n"
        "Return exactly the requested number of questions.\n\n"
        f"Target ISO Knowledge Area (Topic Anchor):\n{context_payload}\n"
        f"{avoid_block}"
        "Constraints:\n"
        "1. Ask only advanced ISO clause-application questions.\n"
        "2. Never ask generic or meta questions about the provided JSON/context.\n"
        "3. Keep each option concise but technically plausible.\n"
        "4. Output must be valid JSON matching the required schema exactly."
    )

    # Budget tuned for short-format MCQs while supporting up to 30 questions.
    max_tokens = 8192  # Give it the maximum output tokens the API allows to prevent cutoff
    result = await analyze_with_deepseek(
        prompt=prompt,
        system_instruction=QUIZ_GENERATION_SYSTEM_PROMPT,
        response_schema=QUIZ_RESPONSE_SCHEMA,
        model=DEEPSEEK_MODEL_PRO,
        max_tokens=max_tokens,
    )

    # Ensure generated_at is always present
    result.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    result.setdefault("iso_standard", iso_standard)
    result.setdefault("difficulty", difficulty)
    result.setdefault("total_questions", len(result.get("questions", [])))

    # Record the newly generated questions so future calls can avoid them
    _record_questions(key, result.get("questions", []))

    return result


async def generate_quiz_stream(
    context: Dict[str, Any],
    num_questions: int = 5,
    iso_standard: Optional[str] = None,
    difficulty: str = "intermediate",
):
    """Produces a stream of partial JSON text as the LLM generates the quiz."""
    num_questions = max(1, min(num_questions, MAX_QUIZ_QUESTIONS))
    difficulty = _normalize_difficulty(difficulty)

    key = _context_key(context, iso_standard)
    seen = list(_question_history[key])[-MAX_AVOID_QUESTIONS_IN_PROMPT:]
    context_payload = _compact_context_for_prompt(context)

    standard_line = f"ISO Standard: {iso_standard}\n" if iso_standard else ""
    avoid_block = ""
    if seen:
        formatted = "\n".join(
            f"  {i + 1}. {_trim_text(q, MAX_AVOID_QUESTION_CHARS)}" for i, q in enumerate(seen)
        )
        avoid_block = (
            "\n\nIMPORTANT — The following questions have ALREADY been asked. "
            "Do NOT repeat or closely paraphrase any of them:\n"
            f"{formatted}\n"
        )

    prompt = (
        f"{standard_line}"
        f"Difficulty: {difficulty}\n"
        f"Number of questions: {num_questions}\n"
        "Return exactly the requested number of questions.\n\n"
        f"Target ISO Knowledge Area (Topic Anchor):\n{context_payload}\n"
        f"{avoid_block}"
        "Constraints:\n"
        "1. Ask only advanced ISO clause-application questions.\n"
        "2. Never ask generic or meta questions about the provided JSON/context.\n"
        "3. Keep each option concise but technically plausible.\n"
        "4. Output must be valid JSON matching the required schema exactly."
    )

    max_tokens = 8192  # Streaming also needs maximum allowance to prevent cutoff

    # We yield chunks back. Question caching cannot easily happen on partial chunks here
    # without implementing a partial-JSON parser. It could be left to the complete response sync route,
    # or implemented via a frontend callback if needed. For now, streaming bypasses local caching.
    async for chunk in analyze_stream_with_deepseek(
        prompt=prompt,
        system_instruction=QUIZ_GENERATION_SYSTEM_PROMPT,
        response_schema=QUIZ_RESPONSE_SCHEMA,
        model=DEEPSEEK_MODEL_PRO,
        max_tokens=max_tokens,
    ):
        yield chunk
