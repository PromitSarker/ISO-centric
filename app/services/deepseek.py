from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import HTTPException

from app.core.client import DeepSeekClient
from app.core.config import DEEPSEEK_MODEL, DEEPSEEK_MODEL_PRO


async def generate_with_deepseek(
    prompt: str,
    system_instruction: str,
    model: str = DEEPSEEK_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 8192,
) -> str:
    """Generate free-text content using the DeepSeek API."""
    client = DeepSeekClient.get_async_client()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DeepSeek API Error: {str(e)}")


async def analyze_with_deepseek(
    prompt: str,
    system_instruction: str,
    response_schema: Dict[str, Any],
    model: str = DEEPSEEK_MODEL_PRO,
    max_tokens: int = 8192,
) -> Dict[str, Any]:
    """Analyze content using the DeepSeek API with structured JSON output."""
    client = DeepSeekClient.get_async_client()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_instruction + "\n\nYou MUST respond with valid JSON only, matching the required schema exactly.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DeepSeek API Error: {str(e)}")
