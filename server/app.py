from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from server.ai_service import assistant_response
from src.config import demo_mode_enabled, openai_explanation_enabled


app = FastAPI(title="新北市青年就業 AI 決策助理")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AssistantRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "demo_mode": demo_mode_enabled(),
        "openai_explanation": "enabled" if openai_explanation_enabled() else "disabled",
        "deterministic_assistant": "enabled",
    }


@app.post("/api/assistant")
def assistant(request: AssistantRequest) -> dict:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    return assistant_response(query)
