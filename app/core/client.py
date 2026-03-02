import asyncio
import os

from fastapi import HTTPException
from google import genai


class GeminiClient:
    """Singleton Gemini client manager."""

    _client = None
    _async_client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=500,
                    detail="GEMINI_API_KEY environment variable not set. Please check your .env file.",
                )
            cls._client = genai.Client(api_key=api_key)
        return cls._client

    @classmethod
    def get_async_client(cls):
        if cls._async_client is None:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=500,
                    detail="GEMINI_API_KEY environment variable not set. Please check your .env file.",
                )
            cls._async_client = genai.Client(api_key=api_key).aio
        return cls._async_client

    @classmethod
    def close(cls):
        if cls._client:
            try:
                cls._client.close()
            except Exception:
                pass
        if cls._async_client:
            try:
                asyncio.run(cls._async_client.aclose())
            except Exception:
                pass
