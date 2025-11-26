import sqlite3
import re


class SQLBot:

    def __init__(self, db_path):
        self.db_path = db_path
        self.allowed_commands = ["SELECT", "PRAGMA", "WITH", "EXPLAIN"]

    # -------------------------------------------------------------
    def handle_message(self, message: str) -> str:
        """
        Entscheidet, ob der Text ein SQL-Befehl ist
        und führt ihn ggf. aus.
        """
        message = message.strip()

        # Ist es SQL?
        if self.is_sql(message):
            return self.execute_sql(message)

        # Sonst: natürlicher Chat
        return "Ich bin ein SQL-Assistent. Stelle mir bitte eine SQL-Abfrage."

    # -------------------------------------------------------------
    def is_sql(self, text: str) -> bool:
        """
        Erkennt SQL anhand des ersten Wortes.
        """
        first_word = text.split(" ")[0].upper()
        return first_word in self.allowed_commands

    # -------------------------------------------------------------
    def execute_sql(self, query: str) -> str:
        """
        Führt eine SQL-Abfrage sicher aus.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(query)
            rows = cursor.fetchall()

            # Spaltennamen holen
            columns = [description[0] for description in cursor.description] \
                if cursor.description else []

            conn.close()

            if not rows:
                return "✔ Abfrage erfolgreich, aber keine Daten gefunden."

            # Ausgabe formatieren
            result = ""
            result += " | ".join(columns) + "\n"
            result += "-" * 60 + "\n"
            for row in rows:
                result += " | ".join(str(col) for col in row) + "\n"

            return result

        except Exception as e:
            return f"❌ SQL-Fehler: {e}"

