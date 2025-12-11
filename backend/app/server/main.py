from typing import Dict, Any, Optional, List
from fastapi import FastAPI
from pydantic import BaseModel
from app.server.agent_logic import run_text_to_sql_pipeline

app = FastAPI(
    title="SQL backend",
    description="Text to SQL Pipeline",
    version="1.0.0",
)

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    type: str
    sql: Optional[str] = None
    confidence: Optional[float] = None
    answer: Optional[str] = None
    data_preview: Optional[str] = None
    clarification_questions: Optional[List[str]] = None
    reason: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None

CONFIDENCE_THRESHOLD = 0.85
@app.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest) -> QueryResponse:
    result = run_text_to_sql_pipeline(request.question)

    # 1. harte Fehler in der Pipeline 
    if result["type"] == "error":
        return QueryResponse(
            type="error",
            reason=result.get("message", "Unbekannter Fehler"),
            debug=result.get("debug")
        )
    
    # 2. Rückfrage, weil Ambiguität oder fehlendes SQL
    if result["type"] == "clarification_needed":
        return QueryResponse(
            type="clarification_needed",
            reason=result.get("reason"),
            clarification_questions=result.get("questions", [])
        )
    
    # 3. Resultat mit SQL
    if result["type"] == "sucess":
        sql = result.get("sql")
        confidence = result.get("confidence", 0)
        answer = result.get("answer", "")
        data_preview = result.get("data_preview", "")

        if confidence < CONFIDENCE_THRESHOLD:
            return QueryResponse(
                type="clarification_needed",
                confidence = confidence,
                answer=answer,
                data_preview=data_preview,
                reason="Niedrige SQL-Generierungs-Sicherheit",
                debug=result.get("debug")
            )
        
        return QueryResponse(
            type="success",
            sql=sql,
            confidence=confidence,
            answer=answer,
            data_preview=data_preview,
            debug=result.get("debug")
        )

    # Fallback - sollte nie erreicht werden
    return QueryResponse(
        type="error",
        reason="Unbekannter Antworttyp aus der Pipeline",
        debug=result.get("debug")
    )
    