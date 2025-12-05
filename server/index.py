# server/index.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from server.routes.api import router as api_router

# dotenv laden (entspricht dotenv.config())
load_dotenv()

# FastAPI App starten (entspricht express())
app = FastAPI()

# PORT setzen wie in Node
PORT = int(os.getenv("PORT", 3000))

# -------------------------------------------
# Middleware (entspricht helmet() + cors() + express.json())
# -------------------------------------------

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # entspricht cors()
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# STATIC FILES (entspricht: app.use(express.static('public')))
app.mount("/", StaticFiles(directory="public", html=True), name="public")

# -------------------------------------------
# API ROUTES (entspricht: app.use('/api', apiRoutes))
# -------------------------------------------
app.include_router(api_router, prefix="/api")


# -------------------------------------------
# Server starten (entspricht app.listen(PORT))
# -------------------------------------------
if __name__ == "__main__":
    import uvicorn

    print(f"Server läuft auf http://localhost:{PORT}")
    uvicorn.run("server.index:app", host="0.0.0.0", port=PORT, reload=True)
