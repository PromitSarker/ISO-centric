from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import HTTPException
from google.genai import errors as genai_errors
from google.genai import types

from app.core.client import GeminiClient
from app.core.config import GEMINI_MODEL, GEMINI_MODEL_PRO


async def generate_with_gemini(
    prompt: str,
    system_instruction: str,
    model: str = GEMINI_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Generate free-text content using the Gemini API."""
    client = GeminiClient.get_async_client()
    try:
        response = await client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text
    except genai_errors.APIError as e:
        raise HTTPException(
            status_code=e.code if hasattr(e, "code") else 500,
            detail=f"Gemini API Error: {e.message if hasattr(e, 'message') else str(e)}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


async def analyze_with_gemini(
    prompt: str,
    system_instruction: str,
    response_schema: Dict[str, Any],
    model: str = GEMINI_MODEL_PRO,
) -> Dict[str, Any]:
    """Analyze content using the Gemini API with structured JSON output."""
    client = GeminiClient.get_async_client()
    try:
        response = await client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,
                top_p=0.9,
                top_k=20,
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_json_schema=response_schema,
            ),
        )
        return json.loads(response.text)
    except genai_errors.APIError as e:
        raise HTTPException(
            status_code=e.code if hasattr(e, "code") else 500,
            detail=f"Gemini API Error: {e.message if hasattr(e, 'message') else str(e)}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
