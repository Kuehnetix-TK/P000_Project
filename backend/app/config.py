import os 
from dotenv import load_dotenv
from pathlib import Path

# hier verbinden wir die Dateien

# env laden
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama-3.1")

# Credit Datensatz Pfade
MINI_INTERACT_DIR = BASE_DIR / "mini_interact/credit"
DB_PATH = MINI_INTERACT_DIR / "credit.sqlite"
CREDIT_COLUMN_MEANING_PATH = MINI_INTERACT_DIR / "credit_column_meaning_base.json"
CREDIT_KB_PATH = MINI_INTERACT_DIR / "credit_kb.json"
CREDIT_SCHEMA_PATH = MINI_INTERACT_DIR / "credit_schema.text"

# hier werden weitere Datenbank-Pfade definiert

