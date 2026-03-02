from fastapi import APIRouter

from app.core.config import GEMINI_MODEL
from app.core.models import ChatRequest, ChatResponse, GeneratedDocument, NavigatorRequest
from app.core.prompts import ISO_NAVIGATOR_SYSTEM_PROMPT
from app.core.session import handle_chat
from app.services.navigator import generate_iso_navigator_document

router = APIRouter(prefix="/api/v1/navigator", tags=["ISO Navigator"])


@router.post("/generate", response_model=GeneratedDocument)
async def generate_iso_document(request: NavigatorRequest):
    """
    ISO Navigator: Generate compliant documentation based on organization context.
    Creates policies, SOPs, risk registers, and other required documents.
    """
    return await generate_iso_navigator_document(request)


@router.post("/chat", response_model=ChatResponse)
async def navigator_chat(request: ChatRequest):
    """
    ISO Navigator: Conversational consultation for ISO implementation questions.
    Supports multi-turn memory via session_id. Pass context as JSON for tailored guidance.
    """
    return await handle_chat(
        request=request,
        system_prompt=ISO_NAVIGATOR_SYSTEM_PROMPT,
        sources=[
            f"{request.iso_standard.value} Clauses"
            if request.iso_standard
            else "ISO Standards Database"
        ],
        suggested_followups=[
            "Can you elaborate on the implementation steps?",
            "What evidence would an auditor look for?",
            "How does this integrate with other management systems?",
        ],
        model=GEMINI_MODEL,
        temperature=0.5,
    )
