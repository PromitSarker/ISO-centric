from fastapi import APIRouter, HTTPException

from app.core.models import (
    IsoSuggestionRequest,
    IsoSuggestionResponse,
    OrgContextRequest,
    OrgContextResponse,
)
from app.services.discovery import generate_org_context, suggest_iso_standards

router = APIRouter(prefix="/api/v1/discovery", tags=["Discovery"])


@router.post("/context-generator", response_model=OrgContextResponse)
async def api_generate_org_context(request: OrgContextRequest):
    """
    Step 1: Organization Context Generator
    Scrapes a URL (or accepts text) and returns 3 structured context mappings 
    (What, Where, Why, When, Whom).
    """
    try:
        return await generate_org_context(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error generating context.")


@router.post("/iso-suggestions", response_model=IsoSuggestionResponse)
async def api_suggest_iso_standards(request: IsoSuggestionRequest):
    """
    Step 2: ISO Standard Suggestion
    Suggests 3-5 relevant ISO standards based on an input category (e.g., security, manufacturing).
    """
    try:
        return await suggest_iso_standards(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error suggesting standards.")
