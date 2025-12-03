# Text2SQL - Projektpräsentation

## Gruppenprojekt: Natürliche Sprache zu SQL mit intelligenter Ambiguitätsauflösung

---

## 1. Projektübersicht

### Was ist Text2SQL?

Ein System, das **natürlichsprachliche Fragen** automatisch in **SQL-Abfragen** übersetzt.

```
Eingabe:  "Zeige mir die reichsten Kunden mit ihrem Vermögen"
Ausgabe:  SELECT customer_id, total_assets, total_liabilities,
          (total_assets - total_liabilities) AS net_worth
          FROM credit_core_record ORDER BY net_worth DESC
```

### Warum ist das wichtig?

- **Business Intelligence** ohne SQL-Kenntnisse
- Schnellere Datenanalyse für nicht-technische Nutzer
- Reduktion von Fehlern bei manuellen Abfragen
- Zeitersparnis für Data Analysts

---

## 2. Verwendetes Dataset: Mini-Interact

### Quelle
- **BIRD-Interact Dataset** (Google Cloud & BIRD Team)
- Lizenz: CC-BY-SA-4.0
- Paper: https://arxiv.org/abs/2510.05318

### Umfang

| Metrik | Wert |
|--------|------|
| Anzahl Datenbanken | 27 Domänen |
| Anzahl Tabellen | 265 |
| Anzahl Aufgaben | 300 BI-Queries |
| Datenbankgröße | 65 MB (zusammengeführt) |

### Domänen (Beispiele)

| Domäne | Beschreibung | Tabellen |
|--------|--------------|----------|
| `alien` | SETI Signalanalyse | 11 |
| `credit` | Kreditwürdigkeitsprüfung | 6 |
| `gaming` | Gaming-Hardware Tests | 8 |
| `crypto` | Krypto-Trading | 10 |
| `museum` | Museumsartefakte | 14 |
| `vaccine` | Impfstoff-Logistik | 7 |
| ... | ... | ... |

---

## 3. Die Herausforderung: Ambiguität

### Was bedeutet Ambiguität?

Natürliche Sprache ist oft **mehrdeutig**. Das gleiche Wort kann verschiedene Bedeutungen haben.

### Beispiel aus dem Dataset

**User Query:**
> "Show me signals with high quality"

**Problem:** Was bedeutet "high quality"?

**Mögliche Interpretationen:**
1. `SNR > 15 dB` (Signal-to-Noise Ratio)
2. `SNQI > 0` (Signal-to-Noise Quality Indicator)
3. `quality_rating = 'high'`

### Ambiguitätstypen im Dataset

```
1. Knowledge-Based Ambiguity
   → Fachbegriffe, die Domänenwissen erfordern
   → Beispiel: "Signal Quality" = SnrRatio - 0.1 * ABS(NoiseFloorDbm)

2. Schema-Linking Ambiguity
   → Welche Spalte ist gemeint?
   → Beispiel: "score" → p.AnomScore oder p.TechSigProb?

3. Non-Critical Ambiguity
   → Sortierung, Limits
   → Beispiel: "top customers" → ORDER BY ... DESC LIMIT 10?
```

---

## 4. Unsere Lösung: Architektur

### Systemübersicht

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│                   (public/index.html)                        │
│         Modern UI mit Vanilla JavaScript                     │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/JSON
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     EXPRESS SERVER                           │
│                    (server/index.js)                         │
├─────────────────────────────────────────────────────────────┤
│  Routes: /api/query, /api/clarify, /api/schema, /api/health │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌─────────────┐ ┌───────────┐ ┌─────────────┐
│  Knowledge  │ │  OpenAI   │ │  Database   │
│  Service    │ │  Service  │ │  Service    │
│             │ │  (GPT-4)  │ │  (SQLite)   │
└─────────────┘ └───────────┘ └─────────────┘
       │              │              │
       ▼              ▼              ▼
┌─────────────┐ ┌───────────┐ ┌─────────────┐
│  *_kb.jsonl │ │  Prompt   │ │ mega_inter- │
│  *_column_  │ │  Builder  │ │ act.sqlite  │
│  meaning.   │ │           │ │ (265 Tab.)  │
│  json       │ │           │ │             │
└─────────────┘ └───────────┘ └─────────────┘
```

### Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Backend | Node.js + Express |
| LLM | OpenAI GPT-4 Turbo |
| Datenbank | SQLite (better-sqlite3) |
| Frontend | Vanilla HTML/CSS/JS |
| Security | Helmet, CORS |

---

## 5. Workflow: So funktioniert es

### Multi-Step LLM Pipeline

```
1. 📝 Query Input
   │   "Show me wealthy customers with their net worth"
   ▼
2. 🔍 Ambiguity Detection
   │   Erkennt: "wealthy", "net worth" sind mehrdeutig
   ▼
3. 📚 Autonomous Research
   │   Durchsucht Knowledge Base nach Definitionen
   │   Findet: net_worth = total_assets - total_liabilities
   ▼
4. ❓ Interactive Clarification (falls nötig)
   │   Fragt Benutzer bei unklaren Begriffen
   ▼
5. 🤖 SQL Generation (Chain-of-Thought)
   │   LLM generiert SQL mit Reasoning
   ▼
6. ✅ SQL Validation
   │   Prüft auf SQL-Injection, nur SELECT erlaubt
   ▼
7. ⚡ Query Execution
   │   Führt SQL gegen SQLite aus
   ▼
8. 🔄 Self-Correction (bei Fehler)
   │   LLM korrigiert automatisch fehlerhafte SQL
   ▼
9. 💬 Explanation Generation
       Erklärt dem User die Ergebnisse
```

---

## 6. Knowledge Base Integration

### Struktur pro Domäne

Jede der 27 Domänen hat:

```
alien/
├── alien.sqlite                    # Die Datenbank
├── alien_schema.txt                # Tabellendefinitionen
├── alien_kb.jsonl                  # Domänenwissen (Formeln etc.)
└── alien_column_meaning_base.json  # Spaltenbedeutungen
```

### Beispiel: Knowledge Base Entry

**Datei:** `alien_kb.jsonl`
```json
{
  "term": "Signal-to-Noise Quality Indicator (SNQI)",
  "definition": "Measures signal quality accounting for noise floor",
  "formula": "s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm)",
  "usage": "Higher SNQI indicates better signal quality"
}
```

### Wie wird es genutzt?

1. **Ambiguitätserkennung:** LLM identifiziert unklare Begriffe
2. **Knowledge Lookup:** System durchsucht relevante KB-Dateien
3. **Context Enrichment:** Gefundene Definitionen werden dem LLM mitgegeben
4. **Formula Application:** Formeln werden direkt in SQL eingebaut

---

## 7. Datenbank-Zusammenführung

### Problem
27 separate SQLite-Dateien → schwer zu verwalten

### Lösung: merge_all_sqlite.py

```python
# Kernlogik des Skripts
for database in all_databases:
    for table in database.tables:
        # Prefix hinzufügen um Kollisionen zu vermeiden
        new_name = f"{db_name}_{table_name}"
        # alien.signals → alien_signals
        # gaming.performance → gaming_performance
```

### Ergebnis

```
mega_interact.sqlite (65 MB)
├── alien_signals
├── alien_observatories
├── alien_telescopes
├── credit_core_record
├── credit_bank_and_transactions
├── gaming_performance
├── gaming_deviceidentity
└── ... (265 Tabellen total)
```

---

## 8. Security Features

### Implementierte Sicherheitsmaßnahmen

| Feature | Implementierung |
|---------|-----------------|
| SQL Injection Prevention | Parameterized Queries |
| Query Validation | Nur SELECT erlaubt |
| Read-Only Mode | SQLite READONLY Flag |
| Input Sanitization | Eingabevalidierung |
| Query Timeout | 30 Sekunden Limit |
| Helmet | HTTP Security Headers |

### Validierungs-Beispiel

```javascript
// validator.service.js
function validateSQL(sql) {
  // Verbotene Keywords
  const forbidden = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER'];

  // Nur SELECT erlaubt
  if (!sql.trim().toUpperCase().startsWith('SELECT')) {
    throw new Error('Only SELECT queries allowed');
  }

  // Check auf verbotene Keywords
  for (const keyword of forbidden) {
    if (sql.toUpperCase().includes(keyword)) {
      throw new Error(`Forbidden keyword: ${keyword}`);
    }
  }
}
```

---

## 9. API Endpoints

### Verfügbare Endpunkte

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/query` | POST | SQL-Query generieren |
| `/api/clarify` | POST | Klärungsfragen beantworten |
| `/api/schema` | GET | Datenbankschema abrufen |
| `/api/knowledge/stats` | GET | Knowledge Base Statistiken |
| `/api/health` | GET | Health Check |

### Beispiel-Request

```bash
curl -X POST http://localhost:3000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me the top 10 wealthy customers",
    "conversationId": "abc123"
  }'
```

### Beispiel-Response (Erfolg)

```json
{
  "status": "success",
  "sql": "SELECT customer_id, total_assets, total_liabilities, (total_assets - total_liabilities) AS net_worth FROM credit_core_record ORDER BY net_worth DESC LIMIT 10",
  "results": [...],
  "explanation": "Diese Abfrage berechnet das Nettovermögen...",
  "confidence": 0.92,
  "metadata": {
    "tablesUsed": ["credit_core_record"],
    "knowledgeUsed": ["net_worth formula"]
  }
}
```

### Beispiel-Response (Klärung nötig)

```json
{
  "status": "needs_clarification",
  "questions": [
    {
      "term": "wealthy",
      "question": "Was bedeutet 'wealthy' für Sie?",
      "suggestions": [
        "Net Worth > 100,000",
        "Total Assets > 500,000",
        "Top 10% by Net Worth"
      ]
    }
  ]
}
```

---

## 10. Projektstruktur

```
mini-interact/
│
├── 📁 server/                      # Backend
│   ├── index.js                    # Express Entry Point
│   ├── 📁 config/
│   │   └── database.js             # SQLite Verbindung
│   ├── 📁 services/
│   │   ├── openai.service.js       # GPT-4 Integration
│   │   ├── knowledge.service.js    # Knowledge Base Loader
│   │   ├── database.service.js     # Query Execution
│   │   ├── validator.service.js    # SQL Safety Checks
│   │   └── sql-generator.service.js# Haupt-SQL-Generator
│   ├── 📁 prompts/
│   │   ├── system-prompts.js       # LLM System Prompts
│   │   └── prompt-builder.js       # Dynamische Prompts
│   ├── 📁 routes/
│   │   └── api.js                  # API Endpoints
│   └── 📁 utils/
│       ├── logger.js               # Winston Logging
│       └── cache.js                # Simple Cache
│
├── 📁 public/                      # Frontend
│   ├── index.html                  # Haupt-UI
│   ├── 📁 css/
│   │   └── styles.css              # Styling
│   └── 📁 js/
│       ├── app.js                  # Frontend Logic
│       └── api-client.js           # Backend Communication
│
├── 📁 [27 Domänen-Ordner]/         # Datenquellen
│   ├── {domain}.sqlite
│   ├── {domain}_kb.jsonl
│   ├── {domain}_column_meaning_base.json
│   └── {domain}_schema.txt
│
├── mega_interact.sqlite            # Zusammengeführte DB (65 MB)
├── mini_interact.jsonl             # Task-Definitionen
├── merge_all_sqlite.py             # DB-Merge-Skript
├── package.json                    # Node Dependencies
├── .env                            # Konfiguration
└── README.md                       # Dokumentation
```

---

## 11. Installation & Start

### Voraussetzungen

- Node.js 18+ (LTS)
- OpenAI API Key
- macOS / Linux / Windows

### Installation

```bash
# 1. In den Projektordner wechseln
cd /Users/kerimkaya/text2sql/mini-interact

# 2. Dependencies installieren
npm install

# 3. .env Datei konfigurieren
# OPENAI_API_KEY=sk-dein-api-key-hier

# 4. Server starten
npm run dev
```

### Zugriff

| URL | Beschreibung |
|-----|--------------|
| http://localhost:3000 | Web-Interface |
| http://localhost:3000/api/health | Health Check |

---

## 12. Demo-Queries

### Einfache Queries

```
"Show me all alien signals with high SNR"

"List the top 10 customers by total assets"

"What gaming devices have the best battery life?"
```

### Queries mit Ambiguität

```
"Show me high quality signals"
→ System fragt: Was bedeutet "high quality"?

"Find wealthy customers"
→ System nutzt Knowledge Base: net_worth = assets - liabilities

"Analyze signal strength across observatories"
→ System erkennt Domäne automatisch (alien)
```

---

## 13. Herausforderungen & Lösungen

### Challenge 1: Datenbank-Kollisionen

**Problem:** Mehrere DBs haben Tabellen mit gleichem Namen (z.B. "users", "products")

**Lösung:** Prefix-System bei merge
```
users → crypto_users, news_users, virtual_users
```

### Challenge 2: Mehrdeutige Begriffe

**Problem:** "Quality" bedeutet in jeder Domäne etwas anderes

**Lösung:** Domänen-spezifische Knowledge Bases + LLM-Reasoning

### Challenge 3: SQL-Sicherheit

**Problem:** User könnte gefährliche SQL-Befehle injizieren

**Lösung:** Whitelist-Ansatz (nur SELECT) + Parameterized Queries

### Challenge 4: LLM Halluzinationen

**Problem:** GPT erfindet manchmal Tabellen/Spalten

**Lösung:** Schema-Kontext im Prompt + Validierung gegen echtes Schema

---

## 14. Ergebnisse & Metriken

### Projektstatistiken

| Metrik | Wert |
|--------|------|
| Unterstützte Domänen | 27 |
| Tabellen in mega_interact.sqlite | 265 |
| Datenbankgröße | 65 MB |
| API Endpoints | 5 |
| Service-Module | 5 |

### Performance (geschätzt)

| Query-Typ | Response Time |
|-----------|---------------|
| Einfache Queries | 3-5 Sekunden |
| Mit Ambiguity Detection | 5-8 Sekunden |
| Mit Self-Correction | 8-12 Sekunden |

---

## 15. Fazit & Ausblick

### Was wir erreicht haben

✅ Vollständige Text2SQL Pipeline mit OpenAI GPT-4
✅ Intelligente Ambiguitätserkennung und -auflösung
✅ 27 Domänen in einer einheitlichen Datenbank
✅ Moderne Web-UI für einfache Bedienung
✅ Sichere SQL-Validierung
✅ Self-Correction bei Fehlern

### Mögliche Erweiterungen

- [ ] Query History & Favoriten
- [ ] Export als CSV/Excel
- [ ] Visualisierungen (Charts)
- [ ] User Authentication
- [ ] Fine-tuned LLM für bessere Accuracy
- [ ] Vector Search für Knowledge Bases
- [ ] Multi-Language Support (DE/EN)

---

## 16. Links & Ressourcen

| Resource | Link |
|----------|------|
| BIRD-Interact Paper | https://arxiv.org/abs/2510.05318 |
| BIRD-Interact GitHub | https://github.com/bird-bench/BIRD-Interact |
| Mini-Interact Dataset | https://huggingface.co/datasets/birdsql/mini-interact |
| OpenAI API Docs | https://platform.openai.com/docs |

---

## Fragen?

### Kontakt

**Projekt-Repository:** `/Users/kerimkaya/text2sql/mini-interact`

**Server starten:** `npm run dev`

**Web-UI:** http://localhost:3000

---

*Erstellt für die Gruppenpräsentation - Text2SQL mit Mini-Interact Dataset*
