import json
import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI   

from config import OPENAI_API_KEY, OPENAI_MODEL, CREDIT_KB_PATH, CREDIT_SCHEMA_PATH, CREDIT_COLUMN_MEANING_PATH
from .database_tool import execute_sql_query
from .prompts.prompts import SYSTEM_PROMPTS
from .prompts.prompt_builder import build_sql_generation_prompt

# Laden der Umgebungsvariablen
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

client = OpenAI(api_key=OPENAI_API_KEY)

# Hilfsfunktion Schema und Knowledge laden
def load_schema_context() -> str:
    try:
        with open(CREDIT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Fehler beim Laden des Schemas: {str(e)}"
    
def load_knowledge_files() -> str:
    try:
        # Laden der KB
        with open(CREDIT_KB_PATH, "r", encoding="utf-8") as kb_file:
            knowledge_base = json.load(kb_file)
        
        # Laden der Spaltenbedeutungen
        with open(CREDIT_COLUMN_MEANING_PATH, "r", encoding="utf-8") as column_file:
            column_meanings = json.load(column_file)
        
        # Kombinieren der Inhalte
        combined_data = {
            "knowledge_base": knowledge_base,
            "column_meanings": column_meanings
        }
        
        # Rückgabe als JSON-String
        return json.dumps(combined_data, indent=2, ensure_ascii=False)
    
    except Exception:
        pass
    return ""



# Hilfsfunktion, um die SYSTEM PROMPTS aufzurufen
def call_stage(stage_key: str, user_input: str) -> Dict[str, Any]:
    system_prompt = SYSTEM_PROMPTS.get(stage_key, "") 
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],)
    
    content = response.choices[0].message.content or ""
    # falls das Model json drum-herum packt
    cleaned = content.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return {
            "stage": stage_key,
            "parse_error": True,
            "raw": content
        }
    
# Pipeline von Text zu SQL und Erklärung 
def run_text_to_sql_pipeline(user_query: str) -> Dict[str, Any]:
        # 0. Schema und Knowledge laden
        schema_context = load_schema_context()
        knowledge = load_knowledge_files()

        # 1. Ambiguity Detection
        amb_input = f"""User Query: {user_query}
        Database Schema: {schema_context}"""
        amb_result = call_stage("AMBIGUITY_DETECTION", amb_input)
        if amb_result.get("parse_error"):
            return {"type": "error", "stage": "ambiguity_detection", "message": "Ambuguity Detection returned invalid JSON.", "debug": amb_result.get("raw")}
        
        if amb_result.get("is_ambiguous", False):
            return {"type": "clarification_needed", "stage": "ambiguity_detection", "reason": amb_result.get("reason"), "questions": amb_result.get("questions", [])}
        
        # 2. Knowledge Search
        relevant_knowledge_string = ""
        if knowledge: knowledge_input = f"""User Query: {user_query}
        knowledge base (JSON list): {knowledge}
        """
        knowledge_result = call_stage("KNOWLEDGE_SEARCH", knowledge_input)
        if not knowledge_result.get("parse_error"):
            relevant_list: List[str] = knowledge_result.get("relevant_knowledge", []) or []
            relevant_knowledge_string = "\n".join(relevant_list)

        # 3. SQL Generation
        clarifications = {}
        sql_prompt = build_sql_generation_prompt(user_query = user_query, schema_context = schema_context, knowledge = relevant_knowledge_string, clarifications = clarifications)
        sql_gen_result = call_stage("SQL_GENERATION", sql_prompt)
        if sql_gen_result.get("parse_error"):
            return {"type": "error", "stage": "sql_generation", "message": "SQL Generation returned invalid JSON.", "debug": sql_gen_result.get("raw")}
        
        sql = sql_gen_result.get("sql")
        confidence = float(sql_gen_result.get("confidence", 0))
        sql_questions = sql_gen_result.get("questions", [])
        if not sql:
            return {"type": "clarfification_needed", "stage": "sql_generation", "reason": "Model could not generate SQL", "questions": sql_questions}
        
        # 4. SQL Execution
        