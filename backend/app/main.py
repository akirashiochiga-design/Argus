"""Point d'entrée FastAPI.

Lancement (depuis backend/) :  uvicorn app.main:app --reload --port 8000
"""
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import create_db_and_tables
from .routers import agents, dossiers

load_dotenv()

app = FastAPI(title="Argus", version="0.1.0")

# Le front Vite tourne sur :5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(dossiers.router)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/health")
def health() -> dict:
    return {"statut": "ok", "service": "argus-backend"}
