# Zugriff auf die Datenbank
import sqlite3
import pandas as pd
from app.server.config import DB_PATH 

def execute_sql_query(query: str) -> str:
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)

        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"]
        upper_query = query.upper() # Umwandlung in Großbuchstaben zur Überprüfung
        if any(word in upper_query for word in forbidden):
            return "Fehler: Nur SELECT-Abfragen sind erlaubt."
        
        df = pd.read_sql_query(query, conn)
        if df.empty:
            return "Die Abfrage lieferte keine Ergebnisse."
       
    except Exception as e:
            return f"Fehler bei der Abfrage: {str(e)}"
    finally:
        if conn is not None: 
            conn.close() 