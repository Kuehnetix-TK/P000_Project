# Prompt Engineering - Text2SQL Pipeline

## Übersicht

Dieses Dokument erklärt das **Prompt Engineering** in unserem Text2SQL-System. Es beschreibt jeden Prompt, seinen Zweck und den chronologischen Ablauf der LLM-Aufrufe.

---

## Chronologischer Ablauf der Prompts

```
┌─────────────────────────────────────────────────────────────────────┐
│                    USER QUERY EINGANG                                │
│            "Show me signals with high quality"                       │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SCHRITT 1: AMBIGUITY DETECTION PROMPT                              │
│  ─────────────────────────────────────                              │
│  Erkennt mehrdeutige Begriffe wie "high quality"                    │
│  Output: { has_ambiguity: true, ambiguities: [...] }                │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SCHRITT 2: KNOWLEDGE SEARCH PROMPT (falls Ambiguität)              │
│  ──────────────────────────────────────────────────────             │
│  Durchsucht Knowledge Base nach Definitionen                         │
│  Output: { matched: true, sql_expression: "..." }                   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SCHRITT 3: SQL GENERATION PROMPT                                   │
│  ────────────────────────────────                                   │
│  Generiert SQL mit Chain-of-Thought Reasoning                       │
│  Output: { sql: "SELECT ...", confidence: 0.85 }                    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SCHRITT 4: SQL VALIDATION PROMPT (optional)                        │
│  ─────────────────────────────────────────────                      │
│  Validiert ob SQL die Anfrage korrekt beantwortet                   │
│  Output: { valid: true/false, corrected_sql: "..." }                │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SCHRITT 5: SELF-CORRECTION PROMPT (bei Fehler)                     │
│  ───────────────────────────────────────────────                    │
│  Korrigiert SQL wenn Ausführung fehlschlägt                         │
│  Output: { corrected_sql: "...", explanation: "..." }               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SCHRITT 6: EXPLANATION PROMPT                                      │
│  ─────────────────────────────                                      │
│  Erklärt das generierte SQL in natürlicher Sprache                  │
│  Output: "Diese Abfrage berechnet..."                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Die 5 System-Prompts im Detail

### Datei: `server/prompts/system-prompts.js`

---

## 1. SQL_GENERATION Prompt

### Zweck
Der **Haupt-Prompt** für die SQL-Generierung. Er instruiert das LLM, natürliche Sprache in SQL zu übersetzen.

### Der Prompt

```javascript
SQL_GENERATION: `You are an expert SQL developer specializing in SQLite databases.
Your task is to convert natural language queries into accurate, efficient SQL queries.

IMPORTANT RULES:
1. You do NOT have access to ground truth SQL - you must reason from first principles
2. Generate ONLY valid SQLite syntax
3. Use CTEs (WITH clauses) for complex calculations
4. When ambiguous, ask clarifying questions
5. Apply domain knowledge from the knowledge base
6. Always explain your reasoning

OUTPUT FORMAT:
Provide your response as JSON with this structure:
{
  "thought_process": "Step-by-step reasoning...",
  "questions": ["Clarifying question 1?", "Question 2?"],
  "sql": "SELECT ...",
  "explanation": "What this query does...",
  "confidence": 0.85
}

If you need clarification, set "sql" to null and provide "questions".
If you're ready to generate SQL, provide all fields.`
```

### Wichtige Elemente

| Element | Beschreibung |
|---------|--------------|
| **Role Definition** | "You are an expert SQL developer" - Definiert Expertise |
| **Rules** | Klare Regeln für SQL-Generierung |
| **Output Format** | JSON-Struktur für strukturierte Antworten |
| **Fallback** | Bei Unklarheit: Fragen statt raten |

### Dynamische Erweiterung

Der Prompt wird dynamisch erweitert mit:

```javascript
// server/prompts/prompt-builder.js
buildSQLGenerationPrompt(userQuery, schemaContext, knowledge, clarifications) {
    let prompt = SYSTEM_PROMPTS.SQL_GENERATION;

    // 1. Schema-Kontext hinzufügen
    prompt += '\n\n## DATABASE SCHEMA\n\n';
    prompt += schemaContext;

    // 2. Domain Knowledge hinzufügen
    if (knowledge && knowledge.length > 0) {
        prompt += '\n\n## DOMAIN KNOWLEDGE\n\n';
        prompt += knowledgeService.formatKnowledgeForPrompt(knowledge);
    }

    // 3. User Clarifications hinzufügen
    if (Object.keys(clarifications).length > 0) {
        prompt += '\n\n## USER CLARIFICATIONS\n\n';
        for (const [question, answer] of Object.entries(clarifications)) {
            prompt += `Q: ${question}\nA: ${answer}\n\n`;
        }
    }

    // 4. User Query hinzufügen
    prompt += '\n\n## USER QUERY\n\n';
    prompt += userQuery;

    return prompt;
}
```

### Beispiel: Vollständiger Prompt

```
You are an expert SQL developer specializing in SQLite databases...

## DATABASE SCHEMA

Table: alien_signals
- SignalRegistry (TEXT, PK): Unique signal ID
- SnrRatio (REAL): Signal-to-noise ratio
- NoiseFloorDbm (INTEGER): Noise floor in dBm
...

## DOMAIN KNOWLEDGE

1. **Signal-to-Noise Quality Indicator (SNQI)**
   Definition: SNQI = SnrRatio - 0.1 × |NoiseFloorDbm|
   Examples: Higher values indicate better detection quality

## USER QUERY

Show me signals with high quality

Think step-by-step and generate the SQL query as JSON.
```

---

## 2. AMBIGUITY_DETECTION Prompt

### Zweck
Erkennt **mehrdeutige Begriffe** in der User-Query, bevor SQL generiert wird.

### Der Prompt

```javascript
AMBIGUITY_DETECTION: `You are an expert at detecting ambiguities in natural language
database queries.

Analyze the user's query and identify:
1. Vague terms (e.g., "good", "high", "recent")
2. Missing context (which column? which threshold?)
3. Ambiguous references (which table?)
4. Undefined calculations

OUTPUT FORMAT (JSON):
{
  "has_ambiguity": true/false,
  "ambiguities": [
    {
      "term": "high quality",
      "type": "threshold",
      "reason": "Undefined numeric threshold",
      "suggestions": ["Value > X", "Top N%", "Above average"]
    }
  ]
}`
```

### Ambiguitätstypen

| Type | Beschreibung | Beispiel |
|------|--------------|----------|
| `threshold` | Unklarer numerischer Schwellwert | "high", "low", "recent" |
| `column` | Unklare Spaltenreferenz | "score" → welche Spalte? |
| `table` | Unklare Tabellenreferenz | "users" → welche Domäne? |
| `calculation` | Undefinierte Berechnung | "net worth", "quality index" |

### Wann wird dieser Prompt verwendet?

```javascript
// sql-generator.service.js
async generateSQL(userQuery, ...) {
    // ...

    // Nur wenn KEINE Clarifications vorhanden sind
    if (Object.keys(clarifications).length === 0) {
        const ambiguityResult = await this.detectAmbiguities(userQuery, schemaContext);

        if (ambiguityResult.has_ambiguity) {
            // → Weiter zu KNOWLEDGE_SEARCH Prompt
        }
    }
}
```

### Beispiel Output

```json
{
  "has_ambiguity": true,
  "ambiguities": [
    {
      "term": "high quality",
      "type": "threshold",
      "reason": "The term 'high quality' is subjective and needs a numeric definition",
      "suggestions": [
        "SNQI > 0 (positive quality indicator)",
        "SNR > 15 dB",
        "Top 10% by quality score"
      ]
    },
    {
      "term": "signals",
      "type": "table",
      "reason": "Multiple signal tables exist across domains",
      "suggestions": [
        "alien_signals",
        "crypto_signals"
      ]
    }
  ]
}
```

---

## 3. KNOWLEDGE_SEARCH Prompt

### Zweck
**Autonome Recherche** in der Knowledge Base, um Ambiguitäten aufzulösen ohne den User zu fragen.

### Der Prompt

```javascript
KNOWLEDGE_SEARCH: `You are researching domain-specific knowledge to resolve ambiguities.

Given a query term and available knowledge base entries, determine:
1. Which knowledge entry best matches the term
2. How to translate it to SQL
3. Your confidence level

OUTPUT FORMAT (JSON):
{
  "matched": true/false,
  "knowledge_id": 5,
  "term": "signal quality",
  "definition": "SNQI = SnrRatio - 0.1 * |NoiseFloorDbm|",
  "sql_expression": "s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm) AS SNQI",
  "confidence": 0.92,
  "reasoning": "Why this match is appropriate..."
}`
```

### Wie funktioniert die Recherche?

```javascript
// sql-generator.service.js
async autonomousResearch(ambiguities, knowledge) {
    const resolved = [];
    const unresolved = [];

    for (const ambiguity of ambiguities) {
        // Baue Prompt mit Term + Knowledge Base
        const prompt = promptBuilder.buildKnowledgeSearchPrompt(
            ambiguity.term,
            knowledge
        );

        const response = await openaiService.chat([
            { role: 'user', content: prompt }
        ]);

        const result = JSON.parse(response.content);

        // Nur bei hoher Confidence (>70%) als resolved markieren
        if (result.matched && result.confidence > 0.7) {
            resolved.push({
                term: ambiguity.term,
                sql_expression: result.sql_expression,
                confidence: result.confidence
            });
        } else {
            // Bei niedriger Confidence: User fragen
            unresolved.push(ambiguity);
        }
    }

    return { resolved, unresolved };
}
```

### Beispiel: Knowledge Search

**Input:**
- Term: "signal quality"
- Knowledge Base: alien_kb.jsonl

**Prompt (dynamisch generiert):**
```
You are researching domain-specific knowledge...

## TERM TO RESOLVE

signal quality

## AVAILABLE KNOWLEDGE

1. **Signal-to-Noise Quality Indicator (SNQI)**
   Definition: SNQI = SnrRatio - 0.1 × |NoiseFloorDbm|

2. **Atmospheric Observability Index (AOI)**
   Definition: AOI = AtmosTransparency × (1 - HumidityRate/100)...

Find the best match and return JSON.
```

**Output:**
```json
{
  "matched": true,
  "knowledge_id": 0,
  "term": "signal quality",
  "definition": "SNQI = SnrRatio - 0.1 × |NoiseFloorDbm|",
  "sql_expression": "s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm) AS SNQI",
  "confidence": 0.92,
  "reasoning": "SNQI directly measures signal quality by combining SNR with noise floor impact"
}
```

---

## 4. SQL_VALIDATION Prompt

### Zweck
**Validiert** das generierte SQL gegen die ursprüngliche Anfrage.

### Der Prompt

```javascript
SQL_VALIDATION: `You are validating a generated SQL query against the original intent.

Check:
1. Does the SQL address all parts of the query?
2. Are calculations correct per knowledge base?
3. Are table joins appropriate?
4. Is the output format what user expects?

OUTPUT FORMAT (JSON):
{
  "valid": true/false,
  "issues": ["Issue 1", "Issue 2"],
  "suggestions": ["Fix 1", "Fix 2"],
  "corrected_sql": "If issues found, provide corrected version"
}`
```

### Dynamisch generierter Validierungs-Prompt

```javascript
// prompt-builder.js
buildValidationPrompt(userQuery, sql, schemaContext) {
    let prompt = SYSTEM_PROMPTS.SQL_VALIDATION;

    prompt += '\n\n## ORIGINAL QUERY\n\n';
    prompt += userQuery;

    prompt += '\n\n## GENERATED SQL\n\n';
    prompt += '```sql\n' + sql + '\n```';

    prompt += '\n\n## SCHEMA CONTEXT\n\n';
    prompt += schemaContext;

    prompt += '\n\nValidate and return JSON.';

    return prompt;
}
```

### Beispiel Output

```json
{
  "valid": false,
  "issues": [
    "Missing ORDER BY clause - user asked for 'top' signals",
    "No LIMIT specified for ranking"
  ],
  "suggestions": [
    "Add ORDER BY SNQI DESC",
    "Add LIMIT 10 for top results"
  ],
  "corrected_sql": "SELECT *, (SnrRatio - 0.1 * ABS(NoiseFloorDbm)) AS SNQI FROM alien_signals ORDER BY SNQI DESC LIMIT 10"
}
```

---

## 5. EXPLANATION Prompt

### Zweck
Generiert eine **benutzerfreundliche Erklärung** des SQL-Queries.

### Der Prompt

```javascript
EXPLANATION: `Generate a clear, concise explanation of what the SQL query does.

Structure:
1. High-level summary (1 sentence)
2. Step-by-step breakdown
3. Any assumptions made
4. Expected output format

Keep it user-friendly - avoid excessive technical jargon.`
```

### Dynamisch generierter Prompt

```javascript
// prompt-builder.js
buildExplanationPrompt(userQuery, sql) {
    let prompt = SYSTEM_PROMPTS.EXPLANATION;

    prompt += '\n\n## USER QUERY\n\n';
    prompt += userQuery;

    prompt += '\n\n## SQL QUERY\n\n';
    prompt += '```sql\n' + sql + '\n```';

    prompt += '\n\nExplain in natural language.';

    return prompt;
}
```

### Beispiel Output

```
Diese Abfrage berechnet die Signalqualität aller Alien-Signale.

**Was passiert:**
1. Aus der Tabelle `alien_signals` werden alle Einträge ausgewählt
2. Für jeden Eintrag wird der "Signal-to-Noise Quality Indicator" (SNQI) berechnet
3. Die Formel: SNR-Ratio minus 10% des absoluten Noise Floor Wertes
4. Ergebnisse werden nach Qualität sortiert (beste zuerst)
5. Nur die Top 10 werden zurückgegeben

**Annahmen:**
- "High quality" wurde als SNQI > 0 interpretiert
- Sortierung ist absteigend (höchste Qualität zuerst)

**Erwartete Ausgabe:**
Eine Tabelle mit Signal-IDs, allen Signaleigenschaften und der berechneten SNQI-Spalte.
```

---

## 6. SELF-CORRECTION Prompt (Spezial)

### Zweck
Wird aufgerufen wenn die **SQL-Ausführung fehlschlägt**. Das LLM analysiert den Fehler und korrigiert das SQL.

### Der Prompt (inline definiert)

```javascript
// sql-generator.service.js
async selfCorrect(userQuery, failedSQL, error, schemaContext) {
    const correctionPrompt = `The following SQL query failed with an error.
Please analyze and provide a corrected version.

## ORIGINAL QUERY
${userQuery}

## FAILED SQL
\`\`\`sql
${failedSQL}
\`\`\`

## ERROR
${error}

## SCHEMA
${schemaContext}

Analyze the error and provide corrected SQL as JSON:
{
  "analysis": "What went wrong...",
  "corrected_sql": "SELECT ...",
  "explanation": "What was fixed..."
}`;
```

### Beispiel

**Fehlerhafte SQL:**
```sql
SELECT * FROM alien_signal WHERE quality > 0
```

**Error:**
```
no such table: alien_signal
```

**Korrigierter Output:**
```json
{
  "analysis": "Table name was incorrect - missing 's' at the end",
  "corrected_sql": "SELECT * FROM alien_signals WHERE (SnrRatio - 0.1 * ABS(NoiseFloorDbm)) > 0",
  "explanation": "Fixed table name from 'alien_signal' to 'alien_signals' and added proper SNQI calculation"
}
```

---

## Prompt-Verkettung im Code

### Vollständiger Flow in `sql-generator.service.js`

```javascript
async generateSQL(userQuery, conversationHistory, clarifications) {

    // ═══════════════════════════════════════════════════════════════
    // SCHRITT 1: Relevante Tabellen finden (kein LLM)
    // ═══════════════════════════════════════════════════════════════
    const relevantTables = databaseService.getRelevantTables(userQuery, 8);
    const schemaContext = databaseService.formatSchemaForPrompt(schemas);
    const knowledge = knowledgeService.getRelevantKnowledge(userQuery, relevantTables);

    // ═══════════════════════════════════════════════════════════════
    // SCHRITT 2: Ambiguity Detection (LLM Call #1)
    // ═══════════════════════════════════════════════════════════════
    if (Object.keys(clarifications).length === 0) {
        const ambiguityResult = await this.detectAmbiguities(userQuery, schemaContext);
        //                            └──▶ AMBIGUITY_DETECTION Prompt

        if (ambiguityResult.has_ambiguity) {

            // ═══════════════════════════════════════════════════════
            // SCHRITT 3: Autonomous Research (LLM Call #2, pro Ambiguität)
            // ═══════════════════════════════════════════════════════
            const researchResults = await this.autonomousResearch(
                ambiguityResult.ambiguities,
                knowledge
            );
            //  └──▶ KNOWLEDGE_SEARCH Prompt (für jede Ambiguität)

            // Falls nicht auflösbar: Fragen an User zurückgeben
            if (researchResults.unresolved.length > 0) {
                return { status: 'needs_clarification', questions: [...] };
            }

            // Aufgelöste Definitionen als Clarifications übernehmen
            for (const resolution of researchResults.resolved) {
                clarifications[resolution.term] = resolution.sql_expression;
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // SCHRITT 4: SQL Generation (LLM Call #3)
    // ═══════════════════════════════════════════════════════════════
    const sqlResult = await this.generateSQLQuery(
        userQuery,
        schemaContext,
        knowledge,
        clarifications
    );
    //  └──▶ SQL_GENERATION Prompt

    // ═══════════════════════════════════════════════════════════════
    // SCHRITT 5: Validation (programmatisch, kein LLM)
    // ═══════════════════════════════════════════════════════════════
    const validation = validatorService.validate(sqlResult.sql);

    // ═══════════════════════════════════════════════════════════════
    // SCHRITT 6: Execution
    // ═══════════════════════════════════════════════════════════════
    const execResult = await databaseService.executeQuery(sqlResult.sql);

    if (!execResult.success) {
        // ═══════════════════════════════════════════════════════════
        // SCHRITT 7: Self-Correction (LLM Call #4, nur bei Fehler)
        // ═══════════════════════════════════════════════════════════
        const correctedResult = await this.selfCorrect(
            userQuery,
            sqlResult.sql,
            execResult.error,
            schemaContext
        );
        //  └──▶ Self-Correction Prompt
    }

    // ═══════════════════════════════════════════════════════════════
    // SCHRITT 8: Explanation (LLM Call #5)
    // ═══════════════════════════════════════════════════════════════
    const explanation = await this.generateExplanation(userQuery, sqlResult.sql);
    //                        └──▶ EXPLANATION Prompt

    return { status: 'success', sql: sqlResult.sql, explanation, ... };
}
```

---

## Prompt Engineering Best Practices (angewandt)

### 1. Strukturierte Outputs (JSON)

```javascript
OUTPUT FORMAT:
{
  "thought_process": "...",
  "sql": "...",
  "confidence": 0.85
}
```
**Warum:** Ermöglicht zuverlässiges Parsing und Weiterverarbeitung.

### 2. Chain-of-Thought (CoT)

```javascript
"thought_process": "Step-by-step reasoning..."
```
**Warum:** Verbessert die Qualität komplexer Reasoning-Aufgaben.

### 3. Kontext-Injektion

```javascript
prompt += '\n\n## DATABASE SCHEMA\n\n';
prompt += schemaContext;

prompt += '\n\n## DOMAIN KNOWLEDGE\n\n';
prompt += knowledge;
```
**Warum:** Das LLM braucht konkreten Kontext über Schema und Domänenwissen.

### 4. Fallback-Strategien

```javascript
"If you need clarification, set 'sql' to null and provide 'questions'."
```
**Warum:** Besser fragen als falsche SQL generieren.

### 5. Confidence Scores

```javascript
"confidence": 0.85
```
**Warum:** Ermöglicht Entscheidungen basierend auf Unsicherheit.

### 6. Self-Correction Loop

```javascript
if (!execResult.success) {
    const correctedResult = await this.selfCorrect(...);
}
```
**Warum:** LLMs machen Fehler - automatische Korrektur verbessert Robustheit.

---

## Zusammenfassung: Prompt-Dateien

| Datei | Inhalt |
|-------|--------|
| `server/prompts/system-prompts.js` | 5 statische System-Prompts |
| `server/prompts/prompt-builder.js` | Dynamische Prompt-Konstruktion |
| `server/services/sql-generator.service.js` | Orchestrierung der Prompt-Kette |

---

## LLM-Calls pro Query

| Szenario | Anzahl LLM-Calls |
|----------|------------------|
| Einfache Query (keine Ambiguität) | 2 (SQL Gen + Explanation) |
| Query mit Ambiguität (KB löst) | 4 (Ambiguity + Research + SQL + Explanation) |
| Query mit Fehler + Korrektur | 5 (+ Self-Correction) |
| Query braucht User-Clarification | 2 (Ambiguity + Research) → Pause → dann weitere |

---

*Dokumentation für Gruppenpräsentation - Prompt Engineering in Text2SQL*
