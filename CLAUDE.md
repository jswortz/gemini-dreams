# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Gemini Dreams is a nightly self-improvement loop for AI agents. It ingests session logs from multiple CLI agents (Gemini CLI, Claude Code, Jetski, Antigravity, Router), analyzes them for inefficiencies and breakthroughs via an LLM, auto-generates skills, and stores results in SQLite + BigQuery. A Vite/FastAPI dashboard visualizes eval scores, session analysis, and epiphanies over time.

## Commands

```bash
# Install CLI
uv tool install .

# Run dream analysis (nightly log sweep)
dream run
dream run --days 7          # force 7-day lookback

# Check skill eval coverage
dream eval

# Launch local dev dashboard (FastAPI + Vite dev server)
dream dashboard

# Print loaded config
dream config

# Frontend dev
cd frontend && npm install --registry https://registry.npmjs.org && npm run dev

# Frontend production build
cd frontend && npm run build

# Run API server standalone
uv run python api.py        # serves on :8080

# Docker build & run
docker build -t gemini-dreams-dashboard .
docker run -p 8080:8080 gemini-dreams-dashboard

# Deploy to Cloud Run
gcloud run deploy gemini-dreams-dashboard --source . --region us-east1

# Install hooks into Gemini CLI / Claude Code settings
python3 setup_hooks.py
```

**npm registry note**: The system has a private Artifact Registry npm config that causes E401 errors. Always use `--registry https://registry.npmjs.org` when running npm install/ci, and the Dockerfile already does this.

**No formal test suite exists.** `simulate_interactions.py` generates synthetic JSONL data for pipeline validation.

## Architecture

### Data Flow

```
CLI hooks (AfterAgent) --> native_log_hook.py --> JSONL files (~/.gemini/sessions/, etc.)
                                                         |
                                                    dream run
                                                         |
                                              dream_runner.py (LLM analysis)
                                                    /          \
                                              SQLite            BigQuery
                                        (dream_metrics.db)    (4 tables)
                                                                 |
                                                            api.py (FastAPI)
                                                                 |
                                                        frontend/ (Vite + Chart.js)
```

### Key Modules

| File | Role |
|------|------|
| `dream.py` | CLI entry point (`dream` command). Dispatches to subcommands: run, eval, dashboard, config |
| `dream_runner.py` | Core engine. Scans JSONL logs, groups by session, calls headless Gemini for analysis, writes to SQLite + BigQuery, auto-generates skills |
| `native_log_hook.py` | Hook script invoked by AfterAgent. Captures prompt/response, latency, skill versions, writes JSONL |
| `eval_checker.py` | Scans skill repository for eval coverage, creates default eval files for uncovered skills |
| `config_loader.py` | Loads `config.json` with path expansion and auto-migration from legacy formats |
| `api.py` | FastAPI backend. 4 BQ query endpoints + static file serving from `frontend/dist/` |
| `setup_hooks.py` | Installs AfterAgent hooks into `~/.gemini/settings.json` and `~/.claude/settings.json` |
| `dream_dashboard.py` | Legacy Streamlit dashboard (superseded by Vite frontend) |
| `dream_hook.py` | Legacy stdin-pipe hook (superseded by native_log_hook.py) |

### BigQuery Tables

Project `wortz-project-352116`, dataset `gemini_dreams`, prefix `dream_`:

- `dream_session_analysis` — analyzed sessions with epiphanies, skill updates, latency/token diffs
- `dream_raw_logs` — ingested JSONL log entries with agent_name, session_id
- `dream_eval_coverage` — skill eval coverage snapshots (skill_name, has_evals)
- `dream_eval_results` — eval pass/fail results per skill over time

### Frontend

Vite vanilla JS app. Chart.js is loaded via CDN (`index.html`), not as an npm dependency. The frontend fetches from relative `/api/*` URLs so it works both in dev (proxied) and production (served by FastAPI).

### Dockerfile

Multi-stage: Node 22 builds Vite frontend, Python 3.11 runs FastAPI + serves `frontend/dist/` as static files. Single port 8080 for Cloud Run.

### Monitored Agents (config.json)

`gemini_cli`, `antigravity`, `jetski`, `claude_code`, `router` — each with its own `logs_dir` and `turn_threshold`.

## Deployment

The dashboard is deployed to Cloud Run at `gemini-dreams-dashboard-679926387543.us-east1.run.app`. It uses Application Default Credentials to query BigQuery.
