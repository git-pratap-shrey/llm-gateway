# ── Fallback priority ──────────────────────────────────────────────────────────
PRIORITY_1       = "ollama_cloud"
PRIORITY_1_MODEL = "gemma4:cloud"

PRIORITY_2       = "openrouter"
PRIORITY_2_MODEL = "google/gemma-4-31b-it:free"

PRIORITY_3       = "gemini"
PRIORITY_3_MODEL = "gemma-4-31b-it"

MAX_RETRIES = 3


# ── Provider base URLs ─────────────────────────────────────────────────────────
OLLAMA_CLOUD_BASE_URL  = "https://ollama.com/v1"
OLLAMA_LOCAL_BASE_URL  = "http://localhost:11434/v1"   # not yet active
GEMINI_BASE_URL        = "https://generativelanguage.googleapis.com/v1beta/openai/"
OPENROUTER_BASE_URL    = "https://openrouter.ai/api/v1"


# ── Environment variable names ─────────────────────────────────────────────────
OLLAMA_API_KEY_ENV    = "OLLAMA_API_KEY"
GEMINI_API_KEY_ENV    = "GEMINI_API_KEY"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"