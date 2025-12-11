# server/prompts/prompt_builder.py
import json

# JSON-Datei mit System Prompts laden (entspricht system-prompts.js/.json)
with open("./server/prompts/system-prompts.json", "r", encoding="utf-8") as f:
    SYSTEM_PROMPTS = json.load(f)


def build_sql_generation_prompt(user_query, schema_context, knowledge, clarifications):
    """
    1:1 Portierung von buildSQLGenerationPrompt aus JavaScript.
    """
    prompt = SYSTEM_PROMPTS["SQL_GENERATION"]

    # DATABASE SCHEMA
    prompt += "\n\n## DATABASE SCHEMA\n\n"
    prompt += schema_context

    # DOMAIN KNOWLEDGE
    if knowledge and len(knowledge) > 0:
        prompt += "\n\n## DOMAIN KNOWLEDGE\n\n"
        prompt += knowledge

    # USER CLARIFICATIONS
    if clarifications and len(clarifications.keys()) > 0:
        prompt += "\n\n## USER CLARIFICATIONS\n\n"
        for question, answer in clarifications.items():
            prompt += f"Q: {question}\nA: {answer}\n\n"

    # USER QUERY
    prompt += "\n\n## USER QUERY\n\n"
    prompt += user_query

    return prompt
