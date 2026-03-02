from __future__ import annotations

import json
import os
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Optional

from fastapi import HTTPException, UploadFile
from google.genai import types

from app.core.client import GeminiClient
from app.core.config import GEMINI_MODEL_PRO
from app.core.prompts import BENCHMARK_AI_SYSTEM_PROMPT


def get_iso_clause_structure(standard: str) -> str:
    """Return the clause structure text for a given ISO standard."""
    structures = {
        "ISO 9001:2015": """
4. Context of the Organization
   4.1 Understanding the organization and its context
   4.2 Understanding the needs and expectations of interested parties
   4.3 Determining the scope of the quality management system
   4.4 Quality management system and its processes

5. Leadership
   5.1 Leadership and commitment
   5.2 Policy
   5.3 Organizational roles, responsibilities and authorities

6. Planning
   6.1 Actions to address risks and opportunities
   6.2 Quality objectives and planning to achieve them
   6.3 Planning of changes

7. Support
   7.1 Resources
   7.2 Competence
   7.3 Awareness
   7.4 Communication
   7.5 Documented information

8. Operation
   8.1 Operational planning and control
   8.2 Requirements for products and services
   8.3 Design and development
   8.4 Control of externally provided processes, products and services
   8.5 Production and service provision
   8.6 Release of products and services
   8.7 Control of nonconforming outputs

9. Performance Evaluation
   9.1 Monitoring, measurement, analysis and evaluation
   9.2 Internal audit
   9.3 Management review

10. Improvement
    10.1 General
    10.2 Nonconformity and corrective action
    10.3 Continual improvement
""",
        "ISO 27001:2022": """
4. Context of the Organization
5. Leadership
6. Planning
7. Support
8. Operation
9. Performance Evaluation
10. Improvement
Annex A: Information Security Controls (93 controls in 4 themes)
""",
        "ISO 14001:2015": """
4. Context of the Organization
5. Leadership
6. Planning
7. Support
8. Operation
9. Performance Evaluation
10. Improvement
""",
        "ISO 45001:2018": """
4. Context of the Organization
5. Leadership and Worker Participation
6. Planning
7. Support
8. Operation
9. Performance Evaluation
10. Improvement
""",
    }
    return structures.get(standard, "Standard clause structure not available")


async def extract_text_from_file(file: UploadFile, content: bytes) -> str:
    """Extract text from uploaded file (text/Word only; PDF/images handled natively by Gemini)."""
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""

    if file_ext in [".txt", ".md"]:
        return content.decode("utf-8", errors="ignore")

    if file_ext in [".doc", ".docx"]:
        try:
            from docx import Document
            doc = Document(BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            return f"[Word extraction failed: {str(e)}]"

    # PDF and images are passed as raw bytes to Gemini
    return ""


async def generate_benchmark_analysis(
    document_text: Optional[str] = None,
    document_content: Optional[bytes] = None,
    mime_type: Optional[str] = None,
    improvement_goal: str = "General assessment",
    target_standard: str = "ISO 9001:2015",
    document_type: str = "Unknown",
    department: Optional[str] = None,
    analysis_id: str = "",
) -> Dict[str, Any]:
    """Generate a complete ISO benchmark analysis using the Gemini API."""

    clause_structure = get_iso_clause_structure(target_standard)

    response_schema = {
        "type": "object",
        "properties": {
            "overall_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "grade": {"type": "string", "enum": ["A", "B+", "B", "C+", "C", "D", "F"]},
            "compliance_percentage": {"type": "integer", "minimum": 0, "maximum": 100},
            "effectiveness_percentage": {"type": "integer", "minimum": 0, "maximum": 100},
            "document_type_detected": {"type": "string"},
            "standard_analyzed": {"type": "string"},
            "clause_compliance": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "clause_number": {"type": "string"},
                        "clause_title": {"type": "string"},
                        "status": {"type": "string", "enum": ["Conforming", "Minor Gap", "Major Gap", "Non-Conforming"]},
                        "compliance_percentage": {"type": "integer", "minimum": 0, "maximum": 100},
                        "evidence_found": {"type": "string"},
                        "gap_description": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["clause_number", "clause_title", "status", "compliance_percentage", "evidence_found"],
                },
            },
            "strengths": {"type": "array", "items": {"type": "string"}},
            "identified_gaps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "priority": {"type": "string", "enum": ["High Priority", "Medium Priority", "Low Priority"]},
                        "clause_reference": {"type": "string"},
                        "gap_title": {"type": "string"},
                        "gap_description": {"type": "string"},
                        "risk_level": {"type": "string", "enum": ["High", "Medium", "Low"]},
                        "iso_requirement": {"type": "string"},
                    },
                    "required": ["priority", "clause_reference", "gap_title", "gap_description", "risk_level", "iso_requirement"],
                },
            },
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "priority": {"type": "string", "enum": ["High Priority", "Medium Priority", "Low Priority"]},
                        "clause_reference": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "benefit_statement": {"type": "string"},
                        "effort_level": {"type": "string", "enum": ["Low", "Medium", "High"]},
                        "estimated_timeline": {"type": "string"},
                    },
                    "required": ["priority", "clause_reference", "title", "description", "benefit_statement", "effort_level", "estimated_timeline"],
                },
            },
            "word_count_analyzed": {"type": "integer"},
            "conversation_id": {"type": "string"},
        },
        "required": [
            "overall_score", "grade", "compliance_percentage", "effectiveness_percentage",
            "document_type_detected", "standard_analyzed", "clause_compliance",
            "strengths", "identified_gaps", "recommendations", "word_count_analyzed", "conversation_id",
        ],
    }

    contents = []

    prompt = f"""
DOCUMENT ANALYSIS REQUEST
=========================

DOCUMENT INFORMATION:
- Type: {document_type}
- Department: {department if department else 'Not specified'}
- Improvement Goal: {improvement_goal}

ISO STANDARD: {target_standard}

CLAUSE STRUCTURE TO EVALUATE:
{clause_structure}

TASK:
Perform comprehensive ISO compliance analysis and return structured JSON matching the schema.
Analyze binary content (PDF/Image) directly if provided; otherwise use the supplied text.

ANALYSIS REQUIREMENTS:
1. OVERALL SCORING — overall_score (0-100), grade, compliance_percentage, effectiveness_percentage
2. CLAUSE-BY-CLAUSE — clause_number, clause_title, status, compliance_percentage, evidence_found, gap_description, recommendation
3. STRENGTHS — 3-5 specific strengths
4. IDENTIFIED GAPS — priority, clause_reference, gap_title, gap_description, risk_level, iso_requirement
5. RECOMMENDATIONS — 4-8 actions with priority, clause_reference, title, description, benefit_statement, effort_level, estimated_timeline
6. METADATA — word_count_analyzed, conversation_id: "{analysis_id}"

RESPOND ONLY WITH VALID JSON MATCHING THE SCHEMA.
"""
    contents.append(prompt)

    if document_text:
        contents.append(f"DOCUMENT CONTENT (TEXT):\n{document_text[:45000]}")

    if document_content and mime_type:
        contents.append(types.Part.from_bytes(data=document_content, mime_type=mime_type))

    client = GeminiClient.get_async_client()
    try:
        response = await client.models.generate_content(
            model=GEMINI_MODEL_PRO,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=BENCHMARK_AI_SYSTEM_PROMPT,
                temperature=0.1,
                top_p=0.9,
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_json_schema=response_schema,
            ),
        )
        result = json.loads(response.text)
        result["standard_analyzed"] = target_standard
        result["analysis_timestamp"] = datetime.utcnow().isoformat()
        result["analysis_id"] = analysis_id
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark analysis failed: {str(e)}")
