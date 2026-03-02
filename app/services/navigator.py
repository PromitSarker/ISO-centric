from __future__ import annotations

import re
from datetime import datetime

from app.core.config import GEMINI_MODEL, GEMINI_MODEL_PRO
from app.core.models import GeneratedDocument, NavigatorRequest
from app.core.prompts import ISO_NAVIGATOR_SYSTEM_PROMPT
from app.services.gemini import generate_with_gemini


async def generate_iso_navigator_document(request: NavigatorRequest) -> GeneratedDocument:
    """ISO Navigator: Generate compliant ISO documentation."""

    prompt = f"""
ORGANIZATION CONTEXT:
{request.organization_context}

TASK:
Generate a {request.output_type.value} for {request.iso_standard.value}

SPECIFIC REQUIREMENTS:
{request.specific_requirements if request.specific_requirements else "Follow standard ISO requirements for this document type"}

DOCUMENT REQUIREMENTS:
1. Include document control information (version, effective date, owner)
2. Reference specific {request.iso_standard.value} clauses
3. Include purpose, scope, responsibilities, procedures
4. Add measurable objectives and KPIs where applicable
5. Include implementation guidance
6. Use {request.tone} tone in {request.language} language

Generate the complete document in markdown format. At the end, include a JSON section with:
- iso_clauses_referenced: list of clause numbers
- word_count: integer
- confidence_score: float between 0 and 1
"""

    model = GEMINI_MODEL_PRO if len(request.organization_context) > 1000 else GEMINI_MODEL
    content = await generate_with_gemini(
        prompt=prompt,
        system_instruction=ISO_NAVIGATOR_SYSTEM_PROMPT,
        model=model,
        max_tokens=6144,
    )

    clause_matches = re.findall(
        r"(?:Clause|Section|ISO\s*\d+\.\d+)[\s:]*(\d+(?:\.\d+)*)", content, re.IGNORECASE
    )
    iso_clauses = list(set(clause_matches))[:10]

    return GeneratedDocument(
        title=f"{request.output_type.value} - {request.iso_standard.value}",
        content=content,
        metadata={
            "organization_context": request.organization_context[:200] + "...",
            "iso_standard": request.iso_standard.value,
            "output_type": request.output_type.value,
            "tone": request.tone,
            "language": request.language,
        },
        iso_clauses_referenced=iso_clauses or ["4.0", "5.0", "6.0", "7.0", "8.0", "9.0", "10.0"],
        generation_timestamp=datetime.utcnow().isoformat(),
        word_count=len(content.split()),
        confidence_score=0.85,
    )
