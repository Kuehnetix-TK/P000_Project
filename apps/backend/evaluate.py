"""
Evaluierungs-Script für BIRD Mini-Interact Benchmark
Vergleicht generierte SQL-Queries mit Ground Truth
"""

import json
import sqlite3
import sys
from typing import Dict, List, Tuple
from anthropic import Anthropic
import os

# ============================================
# KONFIGURATION
# ============================================

DB_PATH = "database/credit.sqlite"
QUESTIONS_PATH = "database/mini_interact.jsonl"
GROUND_TRUTH_PATH = "database/mini_interact_ground_truth.json"  # Von Moodle
OUTPUT_PATH = "evaluation_results.json"

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ============================================
# HILFSFUNKTIONEN
# ============================================

def load_questions() -> List[Dict]:
    """Lädt Fragen aus mini_interact.jsonl"""
    questions = []
    with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if data['instance_id'].startswith('credit_'):
                questions.append(data)
    return questions

def load_ground_truth() -> Dict:
    """Lädt Ground Truth SQL-Queries"""
    with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def execute_sql(sql: str) -> Tuple[List, str]:
    """Führt SQL aus und gibt Ergebnisse zurück"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(sql)
        results = cursor.fetchall()
        
        results_list = [dict(row) for row in results]
        conn.close()
        
        return results_list, None
    except Exception as e:
        return None, str(e)

def normalize_results(results: List[Dict]) -> List[Tuple]:
    """Normalisiert Ergebnisse für Vergleich"""
    if not results:
        return []
    
    # Sortiere nach allen Spalten für konsistenten Vergleich
    normalized = []
    for row in results:
        # Konvertiere zu Tuple (sortierbar und hashbar)
        values = tuple(sorted(row.items()))
        normalized.append(values)
    
    # Sortiere alle Zeilen
    normalized.sort()
    return normalized

def compare_results(pred_results: List, true_results: List) -> bool:
    """Vergleicht zwei Ergebnis-Sets"""
    pred_norm = normalize_results(pred_results)
    true_norm = normalize_results(true_results)
    
    return pred_norm == true_norm

# ============================================
# SQL GENERIERUNG (aus app.py)
# ============================================

def generate_sql(question: str, schema: dict, column_meanings: dict, kb: list) -> str:
    """Generiert SQL für eine Frage"""
    
    # Schema String
    schema_str = "DATABASE SCHEMA:\n"
    for table, info in schema.items():
        schema_str += f"\nTable: {table}\n"
        for col in info['columns']:
            schema_str += f"  - {col['name']} ({col['type']})"
            meaning = column_meanings.get(table, {}).get(col['name'], '')
            if meaning:
                schema_str += f" - {meaning}"
            schema_str += "\n"
    
    # KB String
    kb_str = "\nDOMAIN KNOWLEDGE:\n"
    for item in kb[:3]:
        kb_str += f"- {json.dumps(item, ensure_ascii=False)}\n"
    
    prompt = f"""Du bist ein SQL-Experte. Generiere eine SQLite-Query.

{schema_str}

{kb_str}

REGELN:
1. Nur valides SQLite SQL
2. Nutze exakte Tabellen-/Spaltennamen
3. Gib NUR die SQL-Query zurück
4. KEINE Markdown-Formatierung

FRAGE: {question}

SQL:"""
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    
    sql = message.content[0].text.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    
    return sql

def get_database_schema():
    """Lädt Schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
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

def load_kb():
    """Lädt Knowledge Base"""
    kb = []
    try:
        with open('database/credit_kb.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                kb.append(json.loads(line))
    except FileNotFoundError:
        pass
    return kb

# ============================================
# EVALUATION PIPELINE
# ============================================

def evaluate_single_question(question_data: Dict, ground_truth: Dict, schema: dict, 
                            column_meanings: dict, kb: list) -> Dict:
    """Evaluiert eine einzelne Frage"""
    
    instance_id = question_data['instance_id']
    question = question_data['question']
    
    print(f"\n{'='*60}")
    print(f"Evaluiere: {instance_id}")
    print(f"Frage: {question}")
    
    # 1. SQL generieren
    try:
        pred_sql = generate_sql(question, schema, column_meanings, kb)
        print(f"Generiertes SQL:\n{pred_sql}")
    except Exception as e:
        return {
            "instance_id": instance_id,
            "question": question,
            "status": "generation_error",
            "error": str(e),
            "correct": False
        }
    
    # 2. Ground Truth SQL
    true_sql = ground_truth.get(instance_id, {}).get('sql', None)
    
    if not true_sql:
        return {
            "instance_id": instance_id,
            "question": question,
            "predicted_sql": pred_sql,
            "status": "no_ground_truth",
            "correct": False
        }
    
    print(f"Ground Truth SQL:\n{true_sql}")
    
    # 3. Beide SQLs ausführen
    pred_results, pred_error = execute_sql(pred_sql)
    true_results, true_error = execute_sql(true_sql)
    
    if pred_error:
        return {
            "instance_id": instance_id,
            "question": question,
            "predicted_sql": pred_sql,
            "ground_truth_sql": true_sql,
            "status": "execution_error",
            "error": pred_error,
            "correct": False
        }
    
    if true_error:
        return {
            "instance_id": instance_id,
            "question": question,
            "predicted_sql": pred_sql,
            "ground_truth_sql": true_sql,
            "status": "ground_truth_error",
            "error": true_error,
            "correct": False
        }
    
    # 4. Ergebnisse vergleichen
    is_correct = compare_results(pred_results, true_results)
    
    print(f"Ergebnis: {'✓ KORREKT' if is_correct else '✗ FALSCH'}")
    print(f"Predicted Results: {len(pred_results)} Zeilen")
    print(f"Ground Truth Results: {len(true_results)} Zeilen")
    
    return {
        "instance_id": instance_id,
        "question": question,
        "predicted_sql": pred_sql,
        "ground_truth_sql": true_sql,
        "predicted_results_count": len(pred_results),
        "ground_truth_results_count": len(true_results),
        "status": "success",
        "correct": is_correct
    }

def run_evaluation():
    """Führt komplette Evaluation durch"""
    
    print("="*60)
    print("BIRD MINI-INTERACT EVALUATION")
    print("="*60)
    
    # Daten laden
    print("\n1. Lade Daten...")
    questions = load_questions()
    ground_truth = load_ground_truth()
    schema = get_database_schema()
    column_meanings = load_column_meanings()
    kb = load_kb()
    
    print(f"   - {len(questions)} Fragen geladen")
    print(f"   - {len(ground_truth)} Ground Truth Einträge")
    
    # Evaluiere alle Fragen
    print("\n2. Starte Evaluation...")
    results = []
    
    for question_data in questions:
        result = evaluate_single_question(
            question_data, 
            ground_truth, 
            schema, 
            column_meanings, 
            kb
        )
        results.append(result)
    
    # Statistiken
    print("\n" + "="*60)
    print("ERGEBNISSE")
    print("="*60)
    
    total = len(results)
    correct = sum(1 for r in results if r['correct'])
    accuracy = (correct / total * 100) if total > 0 else 0
    
    print(f"\nGenauigkeit: {correct}/{total} = {accuracy:.1f}%")
    
    # Detaillierte Fehleranalyse
    errors = {
        "generation_error": 0,
        "execution_error": 0,
        "wrong_results": 0
    }
    
    for r in results:
        if not r['correct']:
            if r['status'] == 'generation_error':
                errors['generation_error'] += 1
            elif r['status'] == 'execution_error':
                errors['execution_error'] += 1
            else:
                errors['wrong_results'] += 1
    
    print("\nFehlerverteilung:")
    print(f"  - SQL-Generierung fehlgeschlagen: {errors['generation_error']}")
    print(f"  - SQL-Ausführung fehlgeschlagen: {errors['execution_error']}")
    print(f"  - Falsche Ergebnisse: {errors['wrong_results']}")
    
    # Speichere Ergebnisse
    output = {
        "summary": {
            "total_questions": total,
            "correct": correct,
            "accuracy": accuracy,
            "errors": errors
        },
        "results": results
    }
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nErgebnisse gespeichert in: {OUTPUT_PATH}")
    
    return output

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    
    # Check ob alle Files existieren
    required_files = [DB_PATH, QUESTIONS_PATH, GROUND_TRUTH_PATH]
    missing = [f for f in required_files if not os.path.exists(f)]
    
    if missing:
        print("FEHLER: Folgende Dateien fehlen:")
        for f in missing:
            print(f"  - {f}")
        sys.exit(1)
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("FEHLER: ANTHROPIC_API_KEY Umgebungsvariable nicht gesetzt")
        sys.exit(1)
    
    # Evaluation starten
    run_evaluation()