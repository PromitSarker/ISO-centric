import json
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.core.config import DEEPSEEK_MODEL
from app.core.models import ChatRequest, ChatResponse
from app.core.prompts import GENERAL_CHAT_SYSTEM_PROMPT
from app.core.session import handle_chat
from app.services.benchmark import extract_text_from_file

router = APIRouter(prefix="/api/v1", tags=["General Chat"])


@router.post("/chat", response_model=ChatResponse)
async def general_chat(
    messages: str = Form(..., description="JSON string of messages list"),
    context: str = Form("{}", description="JSON string of context"),
    iso_standard: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    General ISO AI Chat — not tied to any specific module.
    Ask anything about ISO standards, compliance, auditing, or best practices.
    Supports multi-turn memory via session_id. Optionally pass any JSON as context or an uploaded file.
    """
    try:
        parsed_messages = json.loads(messages)
        parsed_context = json.loads(context) if context else {}
        
        request = ChatRequest(
            messages=parsed_messages,
            context=parsed_context,
            iso_standard=iso_standard,
            session_id=session_id
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in messages or context")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if file:
        content = await file.read()
        try:
            file_text = await extract_text_from_file(file, content)
            if not request.context:
                request.context = {}
            request.context["uploaded_file_name"] = file.filename
            request.context["uploaded_file_text"] = file_text
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")

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
        model=DEEPSEEK_MODEL,
        temperature=0.5,
    )
