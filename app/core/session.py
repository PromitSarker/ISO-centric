from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Dict, List

from fastapi import HTTPException

from app.core.client import DeepSeekClient
from app.core.config import DEEPSEEK_MODEL, SESSION_STORE
from app.core.models import ChatRequest, ChatResponse


async def handle_chat(
    request: ChatRequest,
    system_prompt: str,
    sources: List[str],
    suggested_followups: List[str],
    model: str = DEEPSEEK_MODEL,
    temperature: float = 0.5,
) -> ChatResponse:
    """
    Unified chat handler with multi-turn session memory (SESSION_STORE keyed by session_id).
    Uses the OpenAI-compatible DeepSeek API.
    """
    session_id = request.session_id or str(uuid.uuid4())

    # Build system instruction
    system_instruction = system_prompt
    if request.iso_standard:
        system_instruction += f"\n\nFocus on {request.iso_standard.value} requirements."

    # Embed context directly in the system instruction when provided
    if request.context:
        system_instruction += f"\n\nContext (JSON):\n{json.dumps(request.context, indent=2)}"

    # Retrieve or initialise conversation history for this session
    history: List[Dict[str, Any]] = SESSION_STORE.get(session_id, [])

    # Prepend system message (always first, reflecting latest instruction)
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_instruction}]
    messages.extend(history)

    # Append new user message(s) from this request
    for msg in request.messages:
        messages.append({"role": "user", "content": msg.content})

    client = DeepSeekClient.get_async_client()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=2048,
            ),
            timeout=120,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Chat response timed out. Please retry or simplify your question.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat generation failed: {str(e)}")

    assistant_content: str = response.choices[0].message.content

    # Persist the new user turns and the assistant reply to session history
    for msg in request.messages:
        history.append({"role": "user", "content": msg.content})
    history.append({"role": "assistant", "content": assistant_content})
    SESSION_STORE[session_id] = history

    return ChatResponse(
        response=assistant_content,
        sources=sources,
        suggested_followups=suggested_followups,
        session_id=session_id,
    )
