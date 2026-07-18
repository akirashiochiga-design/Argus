"""Point d'entrée FastAPI.

Lancement (depuis backend/) :  uvicorn app.main:app --reload --port 8000
"""
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from .db import create_db_and_tables
from .db import engine
from .models import Template
from .routers import admin, agents, audit, dashboard, dossiers, taches
from .seed import seed

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
app.include_router(taches.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(admin.router)

# Servir les fichiers statiques (images, documents)
docs_path = Path(__file__).parent.parent.parent / "docs"
if docs_path.exists():
    app.mount("/docs", StaticFiles(directory=str(docs_path)), name="docs")


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        base_vide = session.exec(select(Template)).first() is None
    if base_vide:
        seed()


@app.get("/health")
def health() -> dict:
    return {"statut": "ok", "service": "argus-backend"}


# En production, FastAPI sert également l'application React compilée.
frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
