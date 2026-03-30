import os

BUDGET_CAP = 750000
SIGNAL_THRESHOLD = 7.0
OLLAMA_MODEL = "qwen2.5:3b"
APP_PORT = int(os.environ.get("PORT", 8009))

# Cloud LLM Configuration (Set these in Render/Vercel ENV)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "") # DO NOT HARDCODE KEYS HERE
GROQ_MODEL = "llama-3.3-70b-versatile"
USE_CLOUD_LLM = os.environ.get("USE_CLOUD_LLM", "true").lower() == "true"
