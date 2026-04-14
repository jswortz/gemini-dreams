# 🌙 Gemini Nightly Dream System - macOS Setup Guide

This guide explains how to install, configure, and manage the Gemini Nightly Dream system on macOS. This system autonomously analyzes your Gemini CLI and ADK agent sessions to find optimizations, track skill lineage, and visualize performance improvements.

## 🏗️ System Architecture

1.  **Native Log Hook**: Intercepts every CLI interaction to record metadata (latency, tokens, skill versions).
2.  **JSONL History**: Stores raw session data in `~/.gemini/sessions/`.
3.  **Dream Runner**: A Python service that analyzes logs via LLM to generate "Epiphanies."
4.  **Metrics Database**: An SQLite DB (`~/.gemini/dream_metrics.db`) storing epiphanies and performance gains.
5.  **Dream Dashboard**: A FastAPI + Vite web interface to visualize the system's evolution.

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have Python 3.9+ and Node.js installed.
```bash
brew install python node
```

### 2. Install Dependencies
```bash
# Backend
cd gemini-dreams-system
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Frontend
cd frontend
npm install
```

### 3. Initialize the Database
Run the simulation script to set up the schema and add demo data:
```bash
python3 gemini-dreams-system/simulate_metrics_v2.py
```

### 4. Configure your Agent Logs
Update `gemini-dreams-system/config.json` to point to your actual agent log directories.

---

## 🛠️ Components Setup

### Native Log Hook
To enable autonomous logging, add the hook to your agent's configuration. The hook is located at:
`gemini-dreams-system/native_log_hook.py`

### Dream Dashboard (UI)
Start the backend and frontend to view your epiphanies and metrics:

**Start Backend (Port 8000):**
```bash
python3 gemini-dreams-system/api.py
```

**Start Frontend (Port 5173):**
```bash
cd gemini-dreams-system/frontend
npm run dev -- --port 5173
```
Visit: [http://localhost:5173](http://localhost:5173)

---

## 📅 Scheduling (launchd)

The system is configured to run a "Dream Session" every day at **noon**.

### Management Commands:
-   **Load/Start Schedule:**
    ```bash
    launchctl load ~/Library/LaunchAgents/com.gemini.nightly.dream.plist
    ```
-   **Unload/Stop Schedule:**
    ```bash
    launchctl unload ~/Library/LaunchAgents/com.gemini.nightly.dream.plist
    ```
-   **Check Logs:**
    ```bash
    tail -f ~/.gemini/logs/dream_runner_stdout.log
    tail -f ~/.gemini/logs/dream_runner_stderr.log
    ```

---

## 📈 Understanding Metrics

The dashboard displays three key improvement indicators:
1.  **Skill Update Badge**: Shows version transitions (e.g., `v1.0.0 -> v1.0.1`) when an epiphany triggers a code change.
2.  **Latency Chip**: Shows the reduction in processing time (ms) achieved by the update.
3.  **Token Chip**: Shows the reduction in token consumption, directly lowering API costs.

---

## 🔒 Security
-   The system uses a `.gitignore` to prevent committing `.env`, `.db`, or `.jsonl` files.
-   Always verify your `config.json` doesn't contain hardcoded keys before pushing to GitHub.

*Built with ❤️ for self-aware agents.*
