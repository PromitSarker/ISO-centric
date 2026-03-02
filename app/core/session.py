from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from google.genai import types

from app.core.client import GeminiClient
from app.core.config import CONTEXT_CACHE_STORE, GEMINI_MODEL, SESSION_STORE
from app.core.models import ChatRequest, ChatResponse


async def get_or_create_context_cache(
    session_id: str,
    system_instruction: str,
    context: Optional[Dict[str, Any]],
    model: str,
) -> Optional[str]:
    """
    Return an existing Gemini context cache name for a session, or create a new one.
    Falls back gracefully to None if the context is too small or caching is unsupported.
    """
    if session_id in CONTEXT_CACHE_STORE:
        return CONTEXT_CACHE_STORE[session_id]
    if not context:
        return None
    try:
        aio = GeminiClient.get_async_client()
        cache = await aio.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                system_instruction=system_instruction,
                contents=[json.dumps(context, indent=2)],
                ttl="3600s",
            ),
        )
        CONTEXT_CACHE_STORE[session_id] = cache.name
        return cache.name
    except Exception:
        # Graceful fallback: context too small or model does not support caching
        return None


async def handle_chat(
    request: ChatRequest,
    system_prompt: str,
    sources: List[str],
    suggested_followups: List[str],
    model: str = GEMINI_MODEL,
    temperature: float = 0.5,
) -> ChatResponse:
    """
    Unified chat handler with:
    - Multi-turn session memory (SESSION_STORE keyed by session_id)
    - Gemini context caching (CONTEXT_CACHE_STORE) for large JSON contexts
    """
    session_id = request.session_id or str(uuid.uuid4())

    # Build base system instruction
    system_instruction = system_prompt
    if request.iso_standard:
        system_instruction += f"\n\nFocus on {request.iso_standard.value} requirements."

    # Attempt to cache the context with Gemini (created once per session)
    cache_name = await get_or_create_context_cache(
        session_id, system_instruction, request.context, model
    )

    # Fallback: embed context directly in the system instruction if caching failed
    if request.context and not cache_name:
        system_instruction += f"\n\nContext (JSON):\n{json.dumps(request.context, indent=2)}"

    # Retrieve or initialise conversation history for this session
    history: List[Dict[str, Any]] = SESSION_STORE.get(session_id, [])

    # Append new user message(s) from this request
    for msg in request.messages:
        history.append({"role": "user", "parts": [{"text": msg.content}]})

    # Build Gemini config — prefer cached_content when available
    config_kwargs: Dict[str, Any] = {
        "temperature": temperature,
        "max_output_tokens": 2048,
    }
    if cache_name:
        config_kwargs["cached_content"] = cache_name
    else:
        config_kwargs["system_instruction"] = system_instruction

    aio = GeminiClient.get_async_client()
    try:
        response = await aio.models.generate_content(
            model=model,
            contents=history,
            config=types.GenerateContentConfig(**config_kwargs),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat generation failed: {str(e)}")

    # Persist the assistant reply to session history
    history.append({"role": "model", "parts": [{"text": response.text}]})
    SESSION_STORE[session_id] = history

    return ChatResponse(
        response=response.text,
        sources=sources,
        suggested_followups=suggested_followups,
        session_id=session_id,
    )
