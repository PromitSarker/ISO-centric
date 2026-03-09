from fastapi import APIRouter

from app.core.config import DEEPSEEK_MODEL
from app.core.models import AuditLensRequest, AuditMaterial, ChatRequest, ChatResponse
from app.core.prompts import AUDIT_LENS_SYSTEM_PROMPT
from app.core.session import handle_chat
from app.services.audit_lens import generate_audit_materials

router = APIRouter(prefix="/api/v1/audit-lens", tags=["Audit Lens"])


@router.post("/generate", response_model=AuditMaterial)
async def generate_audit_materials_endpoint(request: AuditLensRequest):
    """
    Audit Lens: Generate audit materials for a specific audit stage.
    Creates charters, checklists, questionnaires, and reports per ISO 19011.
    """
    return await generate_audit_materials(request)


@router.post("/chat", response_model=ChatResponse)
async def audit_lens_chat(request: ChatRequest):
    """
    Audit Lens: Chat about audit findings, compliance gaps, or regulatory requirements.
    Supports multi-turn memory via session_id. Pass audit findings/context as JSON.
    """
    return await handle_chat(
        request=request,
        system_prompt=AUDIT_LENS_SYSTEM_PROMPT,
        sources=["ISO 19011:2018 Guidelines", "ISO Standards"],
        suggested_followups=[
            "How would an auditor verify this?",
            "Suggest a root cause analysis approach.",
            "What is the standard requirement for this finding?",
            "How long should corrective action take?",
        ],
        model=DEEPSEEK_MODEL,
        temperature=0.4,
    )
