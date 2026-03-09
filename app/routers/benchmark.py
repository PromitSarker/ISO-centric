import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import DEEPSEEK_MODEL_PRO
from app.core.models import (
    BenchmarkAnalysisResponse,
    BenchmarkRequest,
    ChatRequest,
    ChatResponse,
)
from app.core.prompts import BENCHMARK_AI_SYSTEM_PROMPT
from app.core.session import handle_chat
from app.services.benchmark import extract_text_from_file, generate_benchmark_analysis

router = APIRouter(prefix="/api/v1/benchmark", tags=["Benchmark AI"])


@router.post("/analyze-text", response_model=BenchmarkAnalysisResponse)
async def analyze_compliance_text(request: BenchmarkRequest):
    """
    Benchmark AI: Analyze text content for ISO compliance.
    Evaluates against ISO requirements, identifies gaps, and grades the document.
    """
    analysis_id = f"bench_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    result = await generate_benchmark_analysis(
        document_text=request.document_text,
        improvement_goal=request.improvement_goal or "General assessment",
        document_type=request.document_type,
        department=request.department,
        analysis_id=analysis_id,
    )
    return BenchmarkAnalysisResponse(**result)


@router.post("/analyze-file", response_model=BenchmarkAnalysisResponse)
async def analyze_compliance_file(
    file: UploadFile = File(...),
    improvement_goal: Optional[str] = Form(None),
    document_type: str = Form("Unknown"),
    department: Optional[str] = Form(None),
):
    """
    Benchmark AI: Upload and analyze a document file for ISO compliance.
    Supports PDF, Word, TXT, and images (PDF text extraction supported; images converted where possible).
    """
    allowed_extensions = [".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg"]
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )

    content = await file.read()

    mime_mapping = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    mime_type = mime_mapping.get(file_ext)

    document_text = ""
    document_content = None

    if mime_type:
        document_content = content
    else:
        document_text = await extract_text_from_file(file, content)
        document_text = document_text[:128000]
        if len(document_text) < 50:
            raise HTTPException(
                status_code=400,
                detail="Document content too short for meaningful analysis",
            )

    analysis_id = f"bench_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    result = await generate_benchmark_analysis(
        document_text=document_text if document_text else None,
        document_content=document_content,
        mime_type=mime_type,
        improvement_goal=improvement_goal or "General assessment",
        document_type=document_type,
        department=department,
        analysis_id=analysis_id,
    )
    return BenchmarkAnalysisResponse(**result)


@router.post("/chat", response_model=ChatResponse)
async def benchmark_chat(request: ChatRequest):
    """
    Benchmark AI: Chat about analysis results and compliance improvement actions.
    Supports multi-turn memory via session_id. Pass the analysis result as JSON context.
    """
    return await handle_chat(
        request=request,
        system_prompt=BENCHMARK_AI_SYSTEM_PROMPT,
        sources=["ISO Standards"],
        suggested_followups=[
            "How should I prioritize these actions?",
            "What evidence would an auditor look for?",
            "Can you provide a template for this?",
            "How long will implementation take?",
        ],
        model=DEEPSEEK_MODEL_PRO,
        temperature=0.4,
    )
