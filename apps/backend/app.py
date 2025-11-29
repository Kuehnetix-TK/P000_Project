from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
import json
import re
from anthropic import Anthropic
from typing import List, Dict, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class QueryRequest(BaseModel):
    question: str
    conversation_history: Optional[List[Dict]] = []

class QueryResponse(BaseModel):
    sql: str
    result: str
    tableData: list
    confidence: Optional[str] = None

# ============================================
# SCHEMA UND KONTEXT LADEN
# ============================================

def get_database_schema(db_path: str = 'database/credit.sqlite'):
    """Lädt detailliertes Schema mit Fremdschlüsseln"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema = {}
    for table in tables:
        table_name = table[0]
        
        # Spalten-Info
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        # Fremdschlüssel-Info
        cursor.execute(f"PRAGMA foreign_key_list({table_name});")
        foreign_keys = cursor.fetchall()
        
        schema[table_name] = {
            "columns": [{"name": col[1], "type": col[2], "pk": col[5]} for col in columns],
            "foreign_keys": [{"from": fk[3], "to_table": fk[2], "to_column": fk[4]} for fk in foreign_keys]
        }
    
    conn.close()
    return schema

def load_column_meanings():
    """Lädt Column Meanings"""
    try:
        with open('database/credit_column_meaning_base.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def load_knowledge_base():
    """Lädt Knowledge Base"""
    kb = []
    try:
        with open('database/credit_kb.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                kb.append(json.loads(line))
    except FileNotFoundError:
        pass
    return kb

def get_sample_rows(table_name: str, limit: int = 3):
    """Holt Beispielzeilen aus einer Tabelle"""
    try:
        conn = sqlite3.connect('database/credit.sqlite')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        results = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in results]
    except Exception:
        return []

# ============================================
# FEW-SHOT BEISPIELE
# ============================================

FEW_SHOT_EXAMPLES = [
    {
        "question": "Wie viele Kunden gibt es insgesamt?",
        "sql": "SELECT COUNT(*) as total_customers FROM client;",
        "explanation": "Einfache Aggregation mit COUNT(*)"
    },
    {
        "question": "Zeige mir die Top 5 Kunden mit den höchsten Transaktionssummen",
        "sql": """SELECT c.client_id, SUM(t.amount) as total_amount 
FROM client c 
JOIN trans t ON c.client_id = t.client_id 
GROUP BY c.client_id 
ORDER BY total_amount DESC 
LIMIT 5;""",
        "explanation": "JOIN zwischen client und trans, GROUP BY und ORDER BY"
    },
    {
        "question": "Welche Konten haben einen negativen Saldo?",
        "sql": "SELECT account_id, balance FROM account WHERE balance < 0;",
        "explanation": "Einfacher Filter mit WHERE-Klausel"
    }
]

# ============================================
# PROMPT ENGINEERING - OPTIMIERT
# ============================================

def create_enhanced_text2sql_prompt(question: str, schema: dict, column_meanings: dict, kb: list, conversation_history: list = []):
    """
    Erstellt einen optimierten Prompt mit:
    - Detailliertem Schema
    - Sample Rows (wichtig für Kontext!)
    - Few-Shot Examples
    - Domain Knowledge
    - Conversation History
    """
    
    # 1. SCHEMA MIT SAMPLE ROWS
    schema_str = "# DATABASE SCHEMA MIT BEISPIELDATEN\n\n"
    for table, info in schema.items():
        schema_str += f"## Tabelle: {table}\n"
        schema_str += "Spalten:\n"
        for col in info['columns']:
            col_name = col['name']
            col_type = col['type']
            pk_marker = " [PRIMARY KEY]" if col['pk'] else ""
            meaning = column_meanings.get(table, {}).get(col_name, '')
            
            schema_str += f"  - {col_name} ({col_type}){pk_marker}"
            if meaning:
                schema_str += f" - Bedeutung: {meaning}"
            schema_str += "\n"
        
        # Fremdschlüssel
        if info['foreign_keys']:
            schema_str += "Fremdschlüssel:\n"
            for fk in info['foreign_keys']:
                schema_str += f"  - {fk['from']} → {fk['to_table']}.{fk['to_column']}\n"
        
        # WICHTIG: Sample Rows hinzufügen!
        sample_rows = get_sample_rows(table, limit=2)
        if sample_rows:
            schema_str += "\nBeispieldaten:\n"
            for i, row in enumerate(sample_rows, 1):
                schema_str += f"  Zeile {i}: {json.dumps(row, ensure_ascii=False)}\n"
        
        schema_str += "\n"
    
    # 2. DOMAIN KNOWLEDGE
    kb_str = "# DOMAIN KNOWLEDGE\n\n"
    for item in kb[:3]:
        kb_str += f"- {json.dumps(item, ensure_ascii=False)}\n"
    
    # 3. FEW-SHOT EXAMPLES
    examples_str = "# BEISPIELE FÜR SQL-GENERIERUNG\n\n"
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        examples_str += f"Beispiel {i}:\n"
        examples_str += f"Frage: {example['question']}\n"
        examples_str += f"SQL: {example['sql']}\n"
        examples_str += f"Erklärung: {example['explanation']}\n\n"
    
    # 4. CONVERSATION HISTORY (optional)
    history_str = ""
    if conversation_history:
        history_str = "# GESPRÄCHSVERLAUF\n\n"
        for msg in conversation_history[-3:]:  # Nur letzte 3
            history_str += f"User: {msg.get('user', '')}\n"
            history_str += f"SQL: {msg.get('sql', '')}\n\n"
    
    # 5. HAUPTPROMPT
    prompt = f"""Du bist ein Experte für SQLite-Datenbanken und SQL-Generierung. 
Deine Aufgabe ist es, natürlichsprachige Fragen in präzise SQL-Queries zu übersetzen.

{schema_str}

{kb_str}

{examples_str}

{history_str}

# WICHTIGE REGELN
1. Generiere nur valides SQLite SQL (Version 3.x)
2. Nutze die EXAKTEN Tabellen- und Spaltennamen aus dem Schema
3. Achte auf die Beispieldaten und Column Meanings für semantisches Verständnis
4. Verwende JOINs korrekt gemäß der Fremdschlüssel-Beziehungen
5. Gib NUR die SQL-Query zurück, KEINE Erklärungen oder Markdown
6. Bei Aggregationen: Nutze GROUP BY korrekt
7. Für "Top N" oder "Erste N": Verwende LIMIT
8. Bei Zeitangaben: Beachte das Format in den Beispieldaten
9. KEINE ```sql``` Markdown-Blöcke!

# AKTUELLE FRAGE
{question}

# SQL-QUERY (nur die Query, nichts anderes):"""
    
    return prompt

# ============================================
# SQL VALIDIERUNG
# ============================================

def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validiert SQL-Query auf häufige Fehler
    Returns: (is_valid, error_message)
    """
    sql_lower = sql.lower().strip()
    
    # Check 1: Ist es überhaupt SQL?
    if not any(keyword in sql_lower for keyword in ['select', 'insert', 'update', 'delete']):
        return False, "Keine gültige SQL-Query erkannt"
    
    # Check 2: Nur SELECT erlauben (Sicherheit!)
    if not sql_lower.startswith('select'):
        return False, "Nur SELECT-Queries sind erlaubt"
    
    # Check 3: Gefährliche Befehle blockieren
    dangerous = ['drop', 'truncate', 'alter', 'create', 'grant', 'revoke']
    if any(cmd in sql_lower for cmd in dangerous):
        return False, "Gefährliche SQL-Befehle sind nicht erlaubt"
    
    # Check 4: Syntax-Test mit SQLite
    try:
        conn = sqlite3.connect('database/credit.sqlite')
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
        conn.close()
        return True, ""
    except sqlite3.Error as e:
        return False, f"SQL-Syntax-Fehler: {str(e)}"

# ============================================
# SQL GENERIERUNG MIT RETRY-LOGIK
# ============================================

def generate_sql_with_retry(question: str, conversation_history: list = [], max_retries: int = 3):
    """Generiert SQL mit automatischer Fehlerkorrektur"""
    schema = get_database_schema()
    column_meanings = load_column_meanings()
    kb = load_knowledge_base()
    
    for attempt in range(max_retries):
        try:
            # Prompt erstellen
            if attempt == 0:
                prompt = create_enhanced_text2sql_prompt(question, schema, column_meanings, kb, conversation_history)
            else:
                # Bei Retry: Feedback hinzufügen
                prompt = f"""{prompt}

FEHLER BEI VORHERIGEM VERSUCH: {last_error}

Bitte korrigiere die SQL-Query und vermeide diesen Fehler. Gib NUR die korrigierte SQL-Query zurück."""
            
            # Claude API Call
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                temperature=0,  # Deterministisch für SQL
                messages=[{"role": "user", "content": prompt}]
            )
            
            sql = message.content[0].text.strip()
            
            # Markdown entfernen
            sql = re.sub(r'```sql\s*\n?', '', sql)
            sql = re.sub(r'```\s*\n?', '', sql)
            sql = sql.strip()
            
            # Validierung
            is_valid, error = validate_sql(sql)
            
            if is_valid:
                return sql, None
            else:
                last_error = error
                if attempt == max_retries - 1:
                    return sql, error
        
        except Exception as e:
            last_error = str(e)
            if attempt == max_retries - 1:
                raise Exception(f"SQL-Generierung fehlgeschlagen nach {max_retries} Versuchen: {str(e)}")
    
    return None, "Maximale Anzahl an Versuchen erreicht"

# ============================================
# SQL AUSFÜHRUNG
# ============================================

def execute_sql(sql_query: str):
    """Führt SQL aus mit Fehlerbehandlung"""
    try:
        conn = sqlite3.connect('database/credit.sqlite')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        results_list = [dict(row) for row in results]
        
        conn.close()
        return results_list, None
    except Exception as e:
        return None, f"SQL Execution Error: {str(e)}"

# ============================================
# NATÜRLICHE ANTWORT GENERIEREN
# ============================================

def generate_natural_language_response(question: str, sql: str, results: list):
    """Generiert verständliche Antwort"""
    
    if not results:
        results_summary = "Die Abfrage hat keine Ergebnisse zurückgegeben."
    else:
        results_summary = f"Die Abfrage hat {len(results)} Zeilen zurückgegeben."
        if len(results) <= 5:
            results_summary += f"\n\nAlle Ergebnisse:\n{json.dumps(results, ensure_ascii=False, indent=2)}"
        else:
            results_summary += f"\n\nErste 3 Zeilen:\n{json.dumps(results[:3], ensure_ascii=False, indent=2)}"
            results_summary += f"\n\nLetzte Zeile:\n{json.dumps(results[-1], ensure_ascii=False, indent=2)}"
    
    prompt = f"""Basierend auf der Frage und den SQL-Ergebnissen, gib eine natürlichsprachige Antwort auf Deutsch.

FRAGE: {question}

SQL: {sql}

ERGEBNISSE: 
{results_summary}

ANFORDERUNGEN:
1. Gib eine klare, präzise Antwort auf Deutsch (2-4 Sätze)
2. Erwähne die wichtigsten Zahlen und Fakten
3. Wenn keine Ergebnisse: Erkläre das freundlich
4. Sei präzise aber verständlich
5. Keine technischen SQL-Details in der Antwort

ANTWORT:"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        temperature=0.7,  # Etwas kreativer für natürliche Sprache
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text.strip()

# ============================================
# HAUPTENDPUNKT
# ============================================

@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Hauptendpunkt mit vollständiger Pipeline"""
    
    try:
        # 1. SQL generieren mit Retry
        sql, error = generate_sql_with_retry(
            request.question, 
            request.conversation_history
        )
        
        if error:
            raise HTTPException(status_code=400, detail=f"SQL-Generierung fehlgeschlagen: {error}")
        
        # 2. SQL ausführen
        results, exec_error = execute_sql(sql)
        
        if exec_error:
            raise HTTPException(status_code=400, detail=exec_error)
        
        # 3. Natürliche Antwort generieren
        natural_response = generate_natural_language_response(
            request.question, 
            sql, 
            results
        )
        
        # 4. Confidence berechnen (einfache Heuristik)
        confidence = "hoch" if results and len(results) > 0 else "mittel"
        
        return QueryResponse(
            sql=sql,
            result=natural_response,
            tableData=results[:50],  # Max 50 Zeilen
            confidence=confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unerwarteter Fehler: {str(e)}")

@app.get("/health")
async def health_check():
    """Health Check"""
    return {
        "status": "healthy",
        "model": "claude-sonnet-4-20250514",
        "database": "credit.sqlite"
    }

@app.get("/schema")
async def get_schema():
    """Schema-Endpunkt für Debugging"""
    try:
        schema = get_database_schema()
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)