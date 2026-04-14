# 🤖 Gemini Agents & Skills

This document describes the agents and skills monitored by the Gemini Nightly Dream System.

## Overview

Gemini Agents are specialized assistants or automated workflows that interact with users. Skills are modular capabilities that can be added to agents to extend their functionality.

The Nightly Dream System helps maintain the quality of these agents and skills by:
1. **Enforcing Evaluations**: Ensuring every skill has a test suite.
2. **Analyzing Logs**: Looking for opportunities to improve skills based on real user interactions.

## Monitored Skills

The system looks for skills in your configured isolated directories per agent. Examples of skills that can be monitored include:

- **`antigravity`**: Handles complex physics simulations and defying gravity.
- **`jetski`**: Handles web application development and refactoring automation.
- **`dream-analyzer`**: The internal skill used by this system to analyze logs.

### Skill Installation
To install a skill (like `dream-analyzer` included in this repo), copy the skill directory to your agent's skill path:
```bash
cp -r skills/dream-analyzer ~/.gemini/skills/
```

## Usage & History Lookback

When running the dream analyzer, you can control how far back in history it scans for logs.

### Default Behavior
By default, the system scans for logs since the `last_run` timestamp stored in state, or defaults to looking back `1` day (configurable via `lookback_days` in `config.json`).

### Forcing Lookback
You can force the system to look back a specific number of days by using the `--days` flag with the `run` command:
```bash
dream run --days 7
```
This is useful for analyzing historical data or catching up on missed runs.

## Adding Evaluations

To ensure your skill is recognized and passes the `eval_checker`, you must include an evaluation suite.

1. Create a `SKILL.md` file in your skill directory explaining how to run the evaluation.
2. The `eval_checker` will scan for these files to ensure coverage.
3. It will guide you to use the prompt standard: *"Read learning/gemini/agents/skills/run_skill_eval/SKILL.md to learn how to run a skill evaluation"* to run your newly created tests.

---

## 🧬 Skill Lineage & Versioning

To ensure the Nightly Dream System can accurately attribute logs and epiphanies to specific versions of your skills, every skill should include a `VERSION` file.

### Adding a Version File
Create a plain text file named `VERSION` in your skill's root directory:
```bash
echo "1.0.0" > ~/.gemini/skills/my-skill/VERSION
```

### Why this matters
The **Native Log Hook** scans your active skills and records their versions in every log entry. This allows the system to:
- Detect when a skill update fixed a previous repetition issue.
- Correlate latency changes with specific skill versions.
- Prevent "collision" when analyzing logs across different environments or versions.

## ⏱️ Latency Tracking

The `native_log_hook.py` automatically records `latency_ms` for every interaction. This tracks the processing time of the hook itself and helps identify if log-writing overhead is impacting CLI performance. In the future, this will be expanded to track model generation latency for performance optimization.

*Built with ❤️ for Gemini Agents.*
