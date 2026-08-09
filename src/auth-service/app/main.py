"""auth-service entrypoint (FastAPI :8002)."""
from __future__ import annotations

import os
import sys

# make `shared` importable (src/ is 3 levels up from app/main.py)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, auth
from app.core.db import init_db
from app.services.seed import seed
from shared.schemas.errors import AppError, error_response

app = FastAPI(title="WorkBuddy Enterprise auth-service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return error_response(exc.status_code, exc.code, exc.message)


@app.on_event("startup")
def on_startup():
    init_db()
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-service"}
