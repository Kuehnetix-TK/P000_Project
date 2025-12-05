# server/routes/api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from server.services.sql_generator_service import generate_sql_and_execute

router = APIRouter()


# ----------------------------------------------
# Request Body Model (wie req.body in Express)
# ----------------------------------------------
class QueryRequest(BaseModel):
    query: str


# ----------------------------------------------
# GET /api/health
# ----------------------------------------------
@router.get("/health")
async def health():
    return {"status": "ok"}


# ----------------------------------------------
# POST /api/query
# ----------------------------------------------
@router.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        result = await generate_sql_and_execute(request.query)
        return result
    except Exception as err:
        print(err)
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(err)})
