// server/services/sql-generator.service.js
import { chat } from './openai.service.js';
import { buildSQLGenerationPrompt /* + andere */ } from '../prompts/prompt-builder.js';
import { getDb } from '../config/database.js';
import { validateSQL } from './validator.service.js';
// + knowledge.service, etc.

export async function generateSQLAndExecute(userQuery, clarifications = {}) {
  // 1) Schema & Knowledge laden (vereinfacht)
  const schemaContext = '...'; // später: aus SQLite + column_meaning_base.json bauen
  const knowledge = '';        // später: aus *_kb.jsonl laden

  // 2) SQL-Generierung
  const sqlPrompt = buildSQLGenerationPrompt(userQuery, schemaContext, knowledge, clarifications);

  const message = await chat([{ role: 'user', content: sqlPrompt }]);

  let parsed;
  try {
    parsed = JSON.parse(message.content);
  } catch (e) {
    throw new Error('Konnte LLM-Antwort nicht als JSON parsen');
  }

  const sql = parsed.sql;
  validateSQL(sql); // nur SELECT, keine gefährlichen Keywords

  // 3) SQL ausführen
  const db = getDb();
  const stmt = db.prepare(sql);
  const rows = stmt.all();

  return {
    status: 'success',
    sql,
    results: rows,
    explanation: parsed.explanation,
    confidence: parsed.confidence ?? null
  };
}
