# server/config/database.py
import sqlite3

db = None

def get_db():
    global db
    if db is None:
        # exakt wie in JS: DB nur einmal öffnen, readonly
        db = sqlite3.connect("./mini-interact/credit/credit.sqlite")
        db.row_factory = sqlite3.Row  # damit wir Spalten als Dict bekommen
    return db


# ------------------------------------------------------
# Holt eine Liste aller Tabellen
# ------------------------------------------------------
def get_tables():
    db = get_db()
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """
    rows = db.execute(query).fetchall()
    return [row["name"] for row in rows]


# ------------------------------------------------------
# Holt alle Spalten einer Tabelle (PRAGMA)
# ------------------------------------------------------
def get_columns(table_name):
    db = get_db()
    query = f"PRAGMA table_info({table_name});"
    rows = db.execute(query).fetchall()

    # In JS gibt PRAGMA-Schema folgendes zurück:
    # { cid, name, type, notnull, dflt_value, pk }
    # Wir spiegeln das 1:1:
    return [
        {
            "cid": row["cid"],
            "name": row["name"],
            "type": row["type"],
            "notnull": row["notnull"],
            "dflt_value": row["dflt_value"],
            "pk": row["pk"]
        }
        for row in rows
    ]


# ------------------------------------------------------
# Holt das gesamte Schema (Tabellen + Spalten)
# ------------------------------------------------------
def get_full_schema():
    tables = get_tables()
    schema = []

    for table in tables:
        columns = get_columns(table)
        schema.append({
            "table": table,
            "columns": columns
        })

    return schema


# ------------------------------------------------------
# Formatiert das Schema für GPT
# ------------------------------------------------------
def format_schema_for_prompt(schema):
    output = ""

    for entry in schema:
        output += f"TABLE {entry['table']}\n"
        for col in entry["columns"]:
            output += f"  - {col['name']} ({col['type']})\n"
        output += "\n"

    return output
