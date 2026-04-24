import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from google.cloud import bigquery

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_bq_config():
    try:
        with open(os.path.join(os.path.dirname(__file__) or ".", "config.json")) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    bq = cfg.get("bigquery", {})
    return {
        "project_id": bq.get("project_id", "wortz-project-352116"),
        "dataset_id": bq.get("dataset_id", "gemini_dreams"),
        "table_prefix": bq.get("table_prefix", "dream_"),
    }


def _bq_client():
    cfg = _load_bq_config()
    return bigquery.Client(project=cfg["project_id"]), cfg


def _table(cfg, name):
    return f"`{cfg['project_id']}.{cfg['dataset_id']}.{cfg['table_prefix']}{name}`"


def _rows_to_dicts(result):
    return [dict(row) for row in result]


@app.get("/api/eval-results")
async def eval_results():
    client, cfg = _bq_client()
    query = f"""
        SELECT timestamp, skill_name, passed, failed
        FROM {_table(cfg, 'eval_results')}
        ORDER BY timestamp ASC
    """
    rows = _rows_to_dicts(client.query(query).result())
    for r in rows:
        if hasattr(r.get("timestamp"), "isoformat"):
            r["timestamp"] = r["timestamp"].isoformat()
    return rows


@app.get("/api/coverage")
async def coverage():
    client, cfg = _bq_client()
    query = f"""
        SELECT timestamp, skill_name, has_evals
        FROM {_table(cfg, 'eval_coverage')}
        ORDER BY timestamp DESC
        LIMIT 50
    """
    rows = _rows_to_dicts(client.query(query).result())
    for r in rows:
        if hasattr(r.get("timestamp"), "isoformat"):
            r["timestamp"] = r["timestamp"].isoformat()
    return rows


@app.get("/api/sessions")
async def sessions():
    client, cfg = _bq_client()
    query = f"""
        SELECT timestamp, session_id, turn_count, epiphanies, review_status
        FROM {_table(cfg, 'session_analysis')}
        ORDER BY timestamp DESC
        LIMIT 50
    """
    rows = _rows_to_dicts(client.query(query).result())
    for r in rows:
        if hasattr(r.get("timestamp"), "isoformat"):
            r["timestamp"] = r["timestamp"].isoformat()
    return rows


@app.get("/api/stats")
async def stats():
    client, cfg = _bq_client()
    query = f"""
        SELECT
            COUNT(*) AS total_sessions,
            COUNT(DISTINCT session_id) AS unique_sessions,
            COUNTIF(agent_name = 'claude_code') AS claude_sessions,
            COUNTIF(agent_name = 'gemini_cli') AS gemini_sessions,
            COUNTIF(agent_name = 'router') AS router_sessions,
            MIN(timestamp) AS earliest,
            MAX(timestamp) AS latest
        FROM {_table(cfg, 'raw_logs')}
    """
    rows = _rows_to_dicts(client.query(query).result())
    if rows:
        r = rows[0]
        for k in ("earliest", "latest"):
            if hasattr(r.get(k), "isoformat"):
                r[k] = r[k].isoformat()
        return r
    return {}


# Serve Vite build in production
DIST = os.path.join(os.path.dirname(__file__) or ".", "frontend", "dist")
if os.path.isdir(DIST):
    @app.get("/")
    async def index():
        return FileResponse(os.path.join(DIST, "index.html"))

    app.mount("/", StaticFiles(directory=DIST), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
