from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from fastapi import HTTPException

from app.core.client import DeepSeekClient
from app.core.config import DEEPSEEK_MODEL, DEEPSEEK_MODEL_PRO


DEEPSEEK_CALL_TIMEOUT = 120  # seconds — must be less than DEEPSEEK_TIMEOUT_SECONDS in client.py


async def generate_with_deepseek(
    prompt: str,
    system_instruction: str,
    model: str = DEEPSEEK_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Generate free-text content using the DeepSeek API."""
    client = DeepSeekClient.get_async_client()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            timeout=DEEPSEEK_CALL_TIMEOUT,
        )
        return response.choices[0].message.content
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="AI generation timed out. Please try with a shorter request or retry shortly.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DeepSeek API Error: {str(e)}")


async def analyze_with_deepseek(
    prompt: str,
    system_instruction: str,
    response_schema: Dict[str, Any],
    model: str = DEEPSEEK_MODEL_PRO,
    max_tokens: int = 4096,
) -> Dict[str, Any]:
    """Analyze content using the DeepSeek API with structured JSON output."""
    client = DeepSeekClient.get_async_client()
    try:
        schema_str = json.dumps(response_schema, indent=2)
        full_system_instruction = (
            system_instruction
            + "\n\nYou MUST respond with valid JSON only, matching the required schema exactly.\n\nREQUIRED SCHEMA:\n"
            + schema_str
        )
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": full_system_instruction,
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            ),
            timeout=DEEPSEEK_CALL_TIMEOUT,
        )
        return json.loads(response.choices[0].message.content)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="AI analysis timed out. Please try with a shorter document or retry shortly.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DeepSeek API Error: {str(e)}")
