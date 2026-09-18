"""Main FastAPI application entrypoint.

Governed Clinical Trial Patient Screening & Regulatory Audit Agent
Built on Lyzr Agent API architecture & Lyzr Safe AI design principles.
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import BASE_DIR
from backend.database import init_db
from backend.routes.ingestion import router as ingestion_router
from backend.routes.screening import router as screening_router
from backend.routes.dossier import router as dossier_router
from backend.routes.aims import router as aims_router
from backend.routes.webhook import router as webhook_router

# Initialize SQLite tables on startup
init_db()

app = FastAPI(
    title="Governed Clinical Trial Patient Screening & Regulatory Audit Agent",
    description="Multi-agent clinical trial screening platform with Safe AI PHI redaction, deterministic criteria matching, and FDA 21 CFR Part 11 audit dossiers.",
    version="2.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(ingestion_router)
app.include_router(screening_router)
app.include_router(dossier_router)
app.include_router(aims_router)
app.include_router(webhook_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Governed Clinical Trial Screening Agent",
        "version": "2.1.0",
        "triad_architecture": ["Environment Layer", "Agent Layer", "Inference Layer", "Compliance Layer"],
        "safe_ai_phi_redaction": "Active",
        "hallucination_control": "Pure Deterministic Code Engine",
        "fda_part_11_ready": True
    }


# Mount Frontend UI static assets
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
