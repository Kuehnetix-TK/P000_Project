from fastapi import FastAPI
from app.agent_logic import run_text_to_sql_pipeline

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(q: str):
    return run_text_to_sql_pipeline(q)
