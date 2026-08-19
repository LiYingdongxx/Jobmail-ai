"""FastAPI service for JobPilot AI local engineering demo."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from evaluate_quality import evaluate_items, load_eval_set, write_outputs
from jobmail_agent import JobMailAgent, OpenAICompatibleClient
from jobmail_agent.storage import RunStore


class EmailRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    sender: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    date: str = ""
    force_offline: bool = False


class RunListResponse(BaseModel):
    runs: list[dict[str, Any]]


def create_app(store: RunStore | None = None) -> FastAPI:
    app = FastAPI(
        title="JobPilot AI API",
        description="Local API for recruitment email Agent analysis and quality evaluation.",
        version="1.0.0",
    )
    app.state.store = store or RunStore()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "jobpilot-api"}

    @app.post("/analyze_email")
    def analyze_email(request: EmailRequest) -> dict[str, Any]:
        email = {
            "subject": request.subject,
            "sender": request.sender,
            "date": request.date,
            "body": request.body,
        }
        client = OpenAICompatibleClient()
        result = JobMailAgent(llm_client=client).process(
            email,
            force_offline=request.force_offline,
        )
        run_id = app.state.store.save_analysis(email, result)
        return {"run_id": run_id, **result}

    @app.post("/evaluate_quality")
    def evaluate_quality() -> dict[str, Any]:
        items = load_eval_set()
        metrics, badcases = evaluate_items(items)
        write_outputs(metrics, badcases)
        run_id = app.state.store.save_evaluation(metrics, badcases)
        return {"run_id": run_id, "metrics": metrics}

    @app.get("/runs", response_model=RunListResponse)
    def list_runs(limit: int = 20) -> dict[str, Any]:
        return {"runs": app.state.store.list_runs(limit)}

    @app.get("/runs/{run_id}")
    def get_run(run_id: int) -> dict[str, Any]:
        run = app.state.store.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    return app


app = create_app()
