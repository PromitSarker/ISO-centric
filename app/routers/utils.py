from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.core.client import GeminiClient
from app.core.config import GEMINI_MODEL
from app.core.models import ISOStandard
from app.services.benchmark import get_iso_clause_structure

router = APIRouter(tags=["Utilities"])


@router.get("/")
async def root():
    """Health check and API info."""
    return {
        "message": "ISO Standards AI Assistant API is running",
        "version": "2.0.0",
        "modules": ["ISO Navigator", "Audit Lens", "Benchmark AI"],
        "gemini_model": GEMINI_MODEL,
        "documentation": "/docs",
    }


@router.get("/api/v1/health")
async def health_check():
    """Detailed health check with Gemini connectivity."""
    try:
        client = GeminiClient.get_client()
        test_response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents="Respond with 'OK' if connection successful",
        )
        gemini_status = "connected" if test_response.text else "error"
    except Exception as e:
        gemini_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "gemini_api": gemini_status,
        "model": GEMINI_MODEL,
    }


@router.get("/api/v1/standards/list")
async def list_supported_standards():
    """List all supported ISO standards."""
    return {
        "standards": [
            {
                "code": std.value,
                "name": std.value,
                "description": _get_standard_description(std),
            }
            for std in ISOStandard
        ]
    }


@router.get("/api/v1/standards/{standard_code}/clauses")
async def get_standard_clauses(standard_code: str):
    """Get clause structure for a specific ISO standard."""
    clauses = get_iso_clause_structure(standard_code)
    if not clauses or clauses == "Standard clause structure not available":
        raise HTTPException(status_code=404, detail="Standard not found")
    return {
        "standard": standard_code,
        "clauses": clauses,
        "total_clauses": len(clauses.split("\n")),
    }


def _get_standard_description(std: ISOStandard) -> str:
    descriptions = {
        ISOStandard.ISO_9001_2015: "Quality Management Systems - Requirements",
        ISOStandard.ISO_27001_2022: "Information Security Management Systems - Requirements",
        ISOStandard.ISO_14001_2015: "Environmental Management Systems - Requirements",
        ISOStandard.ISO_45001_2018: "Occupational Health and Safety Management Systems",
        ISOStandard.ISO_22301_2019: "Business Continuity Management Systems",
        ISOStandard.ISO_50001_2018: "Energy Management Systems",
    }
    return descriptions.get(std, "ISO Management System Standard")
