import os
from dotenv import load_dotenv
from pathlib import Path

# hier verbinden wir die Dateien

# env laden
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

# bevorzugt OpenAI-Variablen, faellt aber auf Llama/OpenRouter zurueck
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLAMA_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or os.getenv("LLAMA_MODEL") or "gpt-4o"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

# wenn nur ein Llama/OpenRouter-Key vorhanden ist, Standard-Base-URL setzen
if not OPENAI_BASE_URL and os.getenv("LLAMA_API_KEY"):
    OPENAI_BASE_URL = os.getenv("LLAMA_BASE_URL") or "https://openrouter.ai/api/v1"

LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama-3.1")

# Credit Datensatz Pfade
MINI_INTERACT_DIR = BASE_DIR / "mini_interact/credit"
DB_PATH = MINI_INTERACT_DIR / "credit.sqlite"
CREDIT_COLUMN_MEANING_PATH = MINI_INTERACT_DIR / "credit_column_meaning_base.json"
CREDIT_KB_PATH = MINI_INTERACT_DIR / "credit_kb.json"
CREDIT_SCHEMA_PATH = MINI_INTERACT_DIR / "credit_schema.text"

# hier werden weitere Datenbank-Pfade definiert
