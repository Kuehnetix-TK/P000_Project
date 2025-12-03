// server/config/database.js
import Database from 'better-sqlite3';

let db = null;

export function getDb() {
  if (!db) {
    // Pfad zu deiner credit.sqlite anpassen
    db = new Database('./mini-interact/credit/credit.sqlite', {
      readonly: true
    });
  }
  return db;
}
