import os
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
GEMINI_MODEL: str = "gemini-2.0-flash-exp"
GEMINI_MODEL_PRO: str = "gemini-2.0-flash-exp"

# ---------------------------------------------------------------------------
# In-memory session & cache stores
# ---------------------------------------------------------------------------
# session_id -> list of Gemini message dicts (multi-turn history)
SESSION_STORE: Dict[str, List[Dict[str, Any]]] = {}

# session_id -> Gemini cache resource name
CONTEXT_CACHE_STORE: Dict[str, str] = {}
