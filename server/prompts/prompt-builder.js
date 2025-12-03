// server/prompts/prompt-builder.js
import { SYSTEM_PROMPTS } from './system-prompts.js';

export function buildSQLGenerationPrompt(userQuery, schemaContext, knowledge, clarifications) {
  let prompt = SYSTEM_PROMPTS.SQL_GENERATION;

  prompt += '\n\n## DATABASE SCHEMA\n\n';
  prompt += schemaContext;

  if (knowledge && knowledge.length > 0) {
    prompt += '\n\n## DOMAIN KNOWLEDGE\n\n';
    prompt += knowledge;
  }

  if (clarifications && Object.keys(clarifications).length > 0) {
    prompt += '\n\n## USER CLARIFICATIONS\n\n';
    for (const [question, answer] of Object.entries(clarifications)) {
      prompt += `Q: ${question}\nA: ${answer}\n\n`;
    }
  }

  prompt += '\n\n## USER QUERY\n\n';
  prompt += userQuery;

  return prompt;
}

// Ähnlich: buildAmbiguityDetectionPrompt, buildKnowledgeSearchPrompt,
// buildValidationPrompt, buildExplanationPrompt
