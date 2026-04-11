from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional

from app.core.config import DEEPSEEK_MODEL_PRO
from app.core.prompts import QUIZ_GENERATION_SYSTEM_PROMPT
from app.services.deepseek import analyze_with_deepseek

# ---------------------------------------------------------------------------
# In-memory question history
# ---------------------------------------------------------------------------
# Keyed by a hash of (context + iso_standard).  Stores up to MAX_HISTORY
# question strings per key so the LLM is told explicitly to avoid them.
MAX_HISTORY = 30

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
    key = _context_key(context, iso_standard)
    seen = list(_question_history[key])  # snapshot before generation

    standard_line = f"ISO Standard: {iso_standard}\n" if iso_standard else ""
    avoid_block = ""
    if seen:
        formatted = "\n".join(f"  {i + 1}. {q}" for i, q in enumerate(seen))
        avoid_block = (
            "\n\nIMPORTANT — The following questions have ALREADY been asked. "
            "Do NOT repeat or closely paraphrase any of them:\n"
            f"{formatted}\n"
        )

    prompt = (
        f"{standard_line}"
        f"Difficulty: {difficulty}\n"
        f"Number of questions: {num_questions}\n\n"
        f"Target ISO Knowledge Area (Topic Anchor):\n{json.dumps(context, indent=2)}\n\n"
        f"{avoid_block}"
        "CRITICAL INSTRUCTIONS — READ CAREFULLY:\n"
        "1. Interpret the input above strictly as a focus area for a professional ISO assessment.\n"
        "2. ABSOLUTELY PROHIBITED: Do not ask questions about the input JSON itself or the 'context' (e.g., NEVER ask 'What industry is mentioned?' or 'Identify the topic').\n"
        "3. PROMPT: Leverage your expertise as a Senior ISO Auditor to generate technical, high-level questions about relevant ISO standards, specific clause requirements, compliance indicators, and audit best practices related to the topics provided.\n"
        "4. Depth: Ensure questions test specialized terminology and practical application of ISO management systems.\n"
        "5. Final check: Before outputting the JSON, verify that EVERY question is substantive and technical. If a question is generic or 'meta', replace it with a technical clause-based question immediately.\n"
        "\nProduce the JSON response now."
    )

    # Budget: ~200 tokens per question is generous for short options + explanation
    max_tokens = min(200 * num_questions + 256, 2048)
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

    # Record the newly generated questions so future calls can avoid them
    _record_questions(key, result.get("questions", []))

    return result
