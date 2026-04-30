from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ISOStandard(str, Enum):
    ISO_9001_2015 = "ISO 9001:2015"
    ISO_27001_2022 = "ISO 27001:2022"
    ISO_14001_2015 = "ISO 14001:2015"
    ISO_45001_2018 = "ISO 45001:2018"
    ISO_22301_2019 = "ISO 22301:2019"
    ISO_50001_2018 = "ISO 50001:2018"


class AuditMaterialType(str, Enum):
    AUDIT_CHARTER = "Audit Charter"
    CHECKLIST = "Audit Checklist"
    QUESTIONNAIRE = "Pre-audit Questionnaire"
    FINDINGS_REPORT = "Non-Conformance Report"
    CORRECTIVE_ACTION = "Corrective Action Plan"


class NavigatorOutputType(str, Enum):
    POLICY = "Policy Document"
    SOP = "Standard Operating Procedure"
    RISK_REGISTER = "Risk Register"
    TRAINING_QUIZ = "Training Quiz"
    PROCEDURE = "Work Procedure"
    MANUAL = "Quality Manual"


class ComplianceStatus(str, Enum):
    CONFORMING = "Conforming"
    MINOR_GAP = "Minor Gap"
    MAJOR_GAP = "Major Gap"
    NON_CONFORMING = "Non-Conforming"


class PriorityLevel(str, Enum):
    HIGH = "High Priority"
    MEDIUM = "Medium Priority"
    LOW = "Low Priority"


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class NavigatorRequest(BaseModel):
    organization_context: str = Field(
        ...,
        description="Organization description (e.g., 'Acme Corp, specializing in digital solutions with 50+ employees...')",
        min_length=10,
        max_length=5000,
    )
    output_type: NavigatorOutputType
    specific_requirements: Optional[str] = Field(None, max_length=2000)
    tone: Optional[str] = Field("professional", description="Document tone (professional, formal, technical)")
    language: Optional[str] = Field("English", description="Output language")


class AuditLensRequest(BaseModel):
    stage: str
    material_type: AuditMaterialType
    previous_audit_findings: Optional[Dict[str, Any]] = Field(None)
    scope_description: Optional[str] = Field(None, max_length=2000)


class BenchmarkRequest(BaseModel):
    document_text: Optional[str] = Field(
        None,
        description="Text content from document. Optional if binary content is processed.",
        max_length=50000,
    )
    improvement_goal: Optional[str] = Field(None, max_length=1000)
    document_type: Optional[str] = Field("Unknown", description="Type of document (Policy, Procedure, Record, etc.)")
    department: Optional[str] = None


class ChatMessage(BaseModel):
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[Dict[str, Any]] = None
    iso_standard: Optional[ISOStandard] = Field(
        None,
        description="Optional ISO standard to focus the conversation on (e.g. ISO 9001:2015).",
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for multi-turn memory. Returned on first call; pass it back to continue the conversation.",
    )


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class GeneratedDocument(BaseModel):
    title: str
    content: str
    metadata: Dict[str, Any]
    iso_clauses_referenced: List[str]
    generation_timestamp: str
    word_count: int
    confidence_score: float = Field(ge=0, le=1)


class AuditMaterial(BaseModel):
    stage: str
    material_type: str
    content: str
    iso_clauses_covered: List[str]
    next_steps: List[str]
    estimated_duration: str
    required_resources: List[str]
    generation_timestamp: str


class ClauseCompliance(BaseModel):
    clause_number: str
    clause_title: str
    status: ComplianceStatus
    compliance_percentage: int = Field(ge=0, le=100)
    evidence_found: str
    gap_description: Optional[str] = None
    recommendation: Optional[str] = None


class IdentifiedGap(BaseModel):
    priority: PriorityLevel
    clause_reference: str
    gap_title: str
    gap_description: str
    risk_level: str
    iso_requirement: str


class Recommendation(BaseModel):
    priority: PriorityLevel
    clause_reference: str
    title: str
    description: str
    benefit_statement: str
    effort_level: str
    estimated_timeline: str


class BenchmarkAnalysisResponse(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    grade: str
    compliance_percentage: int = Field(ge=0, le=100)
    effectiveness_percentage: int = Field(ge=0, le=100)
    document_type_detected: str
    standard_analyzed: str
    clause_compliance: List[ClauseCompliance]
    strengths: List[str]
    identified_gaps: List[IdentifiedGap]
    recommendations: List[Recommendation]
    analysis_timestamp: str
    analysis_id: str
    word_count_analyzed: int
    conversation_id: str


class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    suggested_followups: List[str]
    session_id: str = Field(
        ...,
        description="Pass this back in subsequent requests to continue the conversation.",
    )


# ---------------------------------------------------------------------------
# Quiz Models
# ---------------------------------------------------------------------------

class QuizRequest(BaseModel):
    context: Dict[str, Any] = Field(
        ...,
        description="JSON object containing the topic, subject matter, or any structured content to generate quiz questions from.",
    )
    num_questions: Optional[int] = Field(5, ge=1, le=20, description="Number of questions to generate (1–20).")
    difficulty: Optional[str] = Field(
        "intermediate",
        description="Difficulty level: 'easy', 'intermediate', or 'hard'.",
    )


class QuizQuestion(BaseModel):
    question: str = Field(..., description="The quiz question text.")
    options: Dict[str, str] = Field(
        ...,
        description="Answer options keyed A–D, e.g. {'A': '...', 'B': '...', 'C': '...', 'D': '...'}.",
    )
    correct_answer: str = Field(..., description="The key of the correct option ('A', 'B', 'C', or 'D').")
    explanation: Optional[str] = Field(None, description="Brief explanation of why the answer is correct.")


class QuizResponse(BaseModel):
    quiz_title: str
    iso_standard: Optional[str]
    total_questions: int
    difficulty: str
    questions: List[QuizQuestion]
    generated_at: str


# ---------------------------------------------------------------------------
# Discovery Models (Steps 1 & 2)
# ---------------------------------------------------------------------------

class OrgContextRequest(BaseModel):
    text: Optional[str] = Field(None, description="Raw text describing the organization.")
    url: Optional[str] = Field(None, description="URL of the organization's website to scrape.")


class OrgDescriptionOption(BaseModel):
    what: str = Field(..., description="What the organization does")
    where: str = Field(..., description="Where it operates")
    why: str = Field(..., description="Why it exists (mission/vision)")
    when: str = Field(..., description="When it was established or timeline context")
    whom: str = Field(..., description="Whom it serves (target audience/customers)")


class OrgContextResponse(BaseModel):
    options: List[OrgDescriptionOption]


class IsoSuggestionRequest(BaseModel):
    category: str = Field(..., description="Category or industry (e.g., 'security', 'quality', 'automotive')")


class IsoSuggestionOption(BaseModel):
    standard: str = Field(..., description="ISO standard code (e.g., 'ISO 27001:2022')")
    title: str = Field(..., description="Full title of the standard")
    relevance: str = Field(..., description="Why this standard is relevant to the requested category")


class IsoSuggestionResponse(BaseModel):
    suggestions: List[IsoSuggestionOption]
