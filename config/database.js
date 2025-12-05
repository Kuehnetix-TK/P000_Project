// server/config/database.js
import Database from "better-sqlite3";

let db = null;

export function getDb() {
  if (!db) {
    db = new Database("./mini-interact/credit/credit.sqlite", {
      readonly: true
    });
  }
  return db;
}

/**
 * Holt eine Liste aller Tabellen in der SQLite-Datenbank.
 */
export function getTables() {
  const db = getDb();
  const rows = db.prepare(`
    SELECT name 
    FROM sqlite_master 
    WHERE type='table' AND name NOT LIKE 'sqlite_%';
  `).all();

  return rows.map(r => r.name);
}

/**
 * Holt alle Spalten einer Tabelle.
 */
export function getColumns(tableName) {
  const db = getDb();
  return db.prepare(`PRAGMA table_info(${tableName});`).all();
}

/**
 * Holt das gesamte Schema (Tabellen + Spalten).
 */
export function getFullSchema() {
  const tables = getTables();
  const schema = [];

  for (const table of tables) {
    const columns = getColumns(table);
    schema.push({ table, columns });
  }

  return schema;
}

/**
 * Formatiert das Schema so, wie GPT es am besten versteht.
 */
export function formatSchemaForPrompt(schema) {
  let output = "";

  for (const entry of schema) {
    output += `TABLE ${entry.table}\n`;
    for (const col of entry.columns) {
      output += `  - ${col.name} (${col.type})\n`;
    }
    output += "\n";
  }

  return output;
}
