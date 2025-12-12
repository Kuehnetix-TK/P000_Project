from typing import Dict


def build_sql_generation_prompt(user_query: str, schema_context: str, knowledge: str, clarifications: Dict) -> str:
    """Compose the prompt text for SQL generation."""
    clarifications_text = ""
    if clarifications:
        clarifications_text = f"Clarifications: {clarifications}"

    return f"""You are to generate a SQLite SELECT query.

User Query:
{user_query}

Database Schema:
{schema_context}

Relevant Knowledge:
{knowledge}

{clarifications_text}
"""
