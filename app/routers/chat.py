from fastapi import APIRouter

from app.core.config import GEMINI_MODEL
from app.core.models import ChatRequest, ChatResponse
from app.core.prompts import GENERAL_CHAT_SYSTEM_PROMPT
from app.core.session import handle_chat

router = APIRouter(prefix="/api/v1", tags=["General Chat"])


@router.post("/chat", response_model=ChatResponse)
async def general_chat(request: ChatRequest):
    """
    General ISO AI Chat — not tied to any specific module.
    Ask anything about ISO standards, compliance, auditing, or best practices.
    Supports multi-turn memory via session_id. Optionally pass any JSON as context.
    """
    return await handle_chat(
        request=request,
        system_prompt=GENERAL_CHAT_SYSTEM_PROMPT,
        sources=["ISO Standards Knowledge Base"],
        suggested_followups=[
            "Can you give me a practical example?",
            "What are the common non-conformances in this area?",
            "How does this apply to a small organisation?",
            "What documentation is required?",
        ],
        model=GEMINI_MODEL,
        temperature=0.5,
    )
