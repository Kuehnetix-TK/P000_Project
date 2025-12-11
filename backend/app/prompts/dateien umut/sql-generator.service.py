# server/services/sql_generator_service.py

import json
from server.services.openai_service import chat
from server.prompts.prompt_builder import build_sql_generation_prompt
from server.config.database import get_db
from server.services.validator_service import validate_sql
# + knowledge service usw.


async def generate_sql_and_execute(user_query, clarifications=None):
    """
    1:1 Portierung von generateSQLAndExecute aus Node.js
    """
    if clarifications is None:
        clarifications = {}

    # 1) Schema & Knowledge laden (aktuell Platzhalter — genau wie im JS-Code)
    schema_context = "..."     # TODO: später aus SQLite laden
    knowledge = ""             # TODO: später aus knowledge-base laden

    # 2) SQL-Generierung
    sql_prompt = build_sql_generation_prompt(
        user_query,
        schema_context,
        knowledge,
        clarifications
    )

    # LLM aufrufen (chat() ist async)
    message = await chat([
        {"role": "user", "content": sql_prompt}
    ])

    # JSON aus der LLM-Antwort parsen
    try:
        parsed = json.loads(message["content"])
    except Exception:
        raise Exception("Konnte LLM-Antwort nicht als JSON parsen")

    sql = parsed.get("sql")

    # Sicherheit: nur SELECT erlauben
    validate_sql(sql)

    # 3) SQL ausführen (wie in JS: db.prepare(sql).all())
    db = get_db()
    cursor = db.execute(sql)
    rows = cursor.fetchall()

    # Ergebnis wie in JS zurückgeben
    return {
        "status": "success",
        "sql": sql,
        "results": [dict(row) for row in rows],  # sqlite Row -> dict
        "explanation": parsed.get("explanation"),
        "confidence": parsed.get("confidence")
    }
