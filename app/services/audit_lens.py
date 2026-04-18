from __future__ import annotations

import json
import re
from datetime import datetime

from app.core.config import DEEPSEEK_MODEL_PRO
from app.core.models import AuditLensRequest, AuditMaterial
from app.core.prompts import AUDIT_LENS_SYSTEM_PROMPT
from app.services.deepseek import generate_with_deepseek


async def generate_audit_materials(request: AuditLensRequest) -> AuditMaterial:
    """Audit Lens: Generate comprehensive audit materials."""

    prompt = f"""
AUDIT PARAMETERS:
- Stage: {request.stage}
- Material Type: {request.material_type.value}
- Scope: {request.scope_description if request.scope_description else 'Full management system scope'}

PREVIOUS FINDINGS (JSON):
{json.dumps(request.previous_audit_findings, indent=2) if request.previous_audit_findings else 'No previous findings provided'}

TASK:
Generate comprehensive {request.material_type.value} for {request.stage} covering applicable ISO management system standards.

REQUIREMENTS:
1. Follow ISO 19011 auditing guidelines
2. Reference specific ISO clause numbers relevant to the audit stage and material type
3. Include risk-based focus areas
4. Provide clear audit criteria and evidence requirements
5. Include sampling guidance where applicable
6. Consider previous findings in focus areas

Generate the complete audit material in markdown format. At the end, include:
- iso_clauses_covered: list of clause numbers
- next_steps: list of 3-5 actionable next steps
- estimated_duration: time estimate
- required_resources: list of resources needed
"""

    content = await generate_with_deepseek(
        prompt=prompt,
        system_instruction=AUDIT_LENS_SYSTEM_PROMPT,
        model=DEEPSEEK_MODEL_PRO,
        max_tokens=4096,
    )

    clause_matches = re.findall(
        r"(?:Clause|Section|ISO\s*\d+\.\d+)[\s:]*(\d+(?:\.\d+)*)", content, re.IGNORECASE
    )
    iso_clauses = list(set(clause_matches))[:15]

    return AuditMaterial(
        stage=request.stage,
        material_type=request.material_type.value,
        content=content,
        iso_clauses_covered=iso_clauses or ["4.0", "5.0", "6.0", "7.0", "8.0", "9.0", "10.0"],
        next_steps=[
            "Review generated material with audit team lead",
            "Customize based on organizational specifics",
            "Schedule audit activities with auditees",
            "Prepare evidence collection templates",
            "Conduct opening meeting",
        ],
        estimated_duration="2-4 hours preparation, 1-3 days execution",
        required_resources=[
            "Audit team (Lead Auditor + Technical Expert)",
            "Access to documented information",
            "Interview rooms/space",
            "Previous audit reports",
            "Organization process maps",
        ],
        generation_timestamp=datetime.utcnow().isoformat(),
    )
