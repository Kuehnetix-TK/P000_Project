import sqlite3

def list_table_schemas(db_path):
    # Verbindung zur SQLite-Datenbank herstellen
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Alle Tabellennamen ermitteln
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()

    if not tables:
        print("Keine Tabellen gefunden.")
        return

    # Für jede Tabelle das Schema ausgeben
    for (table_name,) in tables:
        print(f"\n=== Schema für Tabelle: {table_name} ===")

        # PRAGMA table_info gibt die Struktur zurück
        cursor.execute(f"PRAGMA table_info('{table_name}');")
        columns = cursor.fetchall()

        if not columns:
            print("Keine Spalten gefunden.")
            continue

        for col in columns:
            cid, name, col_type, notnull, default, pk = col
            print(f"  Spalte: {name}, Typ: {col_type}, NOT NULL: {bool(notnull)}, "
                  f"Default: {default}, PrimaryKey: {bool(pk)}")

    conn.close()


# Beispielaufruf:
# (Pfad zur SQLite-Datei anpassen)
if __name__ == "__main__":
    list_table_schemas("Kuehnetix-TK/P000_Project/mini-interact/credit/credit.sqlite")
