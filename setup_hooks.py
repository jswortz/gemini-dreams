#!/usr/bin/env python3
"""Install native log hooks for Gemini CLI and Claude Code.

Gemini CLI uses an `AfterAgent` event with matchers; Claude Code uses a `Stop`
event (no matcher) that fires whenever the assistant finishes a turn. The two
CLIs have different hook schemas, so we write distinct configs to each settings
file.
"""
import os
import json
import sys


GEMINI_SETTINGS = os.path.expanduser("~/.gemini/settings.json")
CLAUDE_SETTINGS = os.path.expanduser("~/.claude/settings.json")


def _load(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"  ❌ {path} is not valid JSON. Skipping.")
        return None


def _save(path, config):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def install_gemini(hook_command):
    """Append AfterAgent hooks to ~/.gemini/settings.json (Gemini CLI schema)."""
    config = _load(GEMINI_SETTINGS)
    if config is None:
        return False
    if not config:
        print(f"  📄 Creating new {GEMINI_SETTINGS}")

    config.setdefault("hooks", {})
    config["hooks"].setdefault("AfterAgent", [])

    new_entries = [
        {
            "matcher": "jetski",
            "hooks": [
                {"name": "jetski-logger", "type": "command",
                 "command": f"{hook_command} jetski"}
            ],
        },
        {
            "matcher": "*",
            "hooks": [
                {"name": "default-logger", "type": "command",
                 "command": f"{hook_command} gemini_cli"}
            ],
        },
    ]

    existing_names = {
        h.get("name")
        for entry in config["hooks"]["AfterAgent"]
        for h in entry.get("hooks", [])
    }

    added = 0
    for entry in new_entries:
        name = entry["hooks"][0]["name"]
        if name in existing_names:
            print(f"  ⏭️  {name} already in {GEMINI_SETTINGS}")
            continue
        config["hooks"]["AfterAgent"].append(entry)
        print(f"  ✅ Added {name} to {GEMINI_SETTINGS}")
        added += 1

    _save(GEMINI_SETTINGS, config)
    return added > 0 or bool(existing_names)


def install_claude(hook_command):
    """Register a Stop hook in ~/.claude/settings.json (Claude Code schema).

    Claude Code's Stop event has no `matcher` field. We give the entry a
    sentinel substring (`gemini-dreams-logger`) in the command so this script
    is idempotent across re-runs.
    """
    config = _load(CLAUDE_SETTINGS)
    if config is None:
        return False
    if not config:
        print(f"  📄 Creating new {CLAUDE_SETTINGS}")

    config.setdefault("hooks", {})
    config["hooks"].setdefault("Stop", [])
    config["hooks"].setdefault("UserPromptSubmit", [])

    sentinel = "# gemini-dreams-logger"
    stop_command = f"{hook_command} claude_code {sentinel}"

    def _already_present(event_list):
        for entry in event_list:
            for h in entry.get("hooks", []):
                if sentinel in (h.get("command") or ""):
                    return True
        return False

    added = 0
    if _already_present(config["hooks"]["Stop"]):
        print(f"  ⏭️  Stop hook already in {CLAUDE_SETTINGS}")
    else:
        config["hooks"]["Stop"].append({
            "hooks": [
                {
                    "type": "command",
                    "command": stop_command,
                }
            ]
        })
        print(f"  ✅ Added Stop hook to {CLAUDE_SETTINGS}")
        added += 1

    if _already_present(config["hooks"]["UserPromptSubmit"]):
        print(f"  ⏭️  UserPromptSubmit hook already in {CLAUDE_SETTINGS}")
    else:
        config["hooks"]["UserPromptSubmit"].append({
            "hooks": [
                {
                    "type": "command",
                    "command": stop_command,
                }
            ]
        })
        print(f"  ✅ Added UserPromptSubmit hook to {CLAUDE_SETTINGS}")
        added += 1

    _save(CLAUDE_SETTINGS, config)
    return True


def main():
    print("🚀 Installing native log hooks for Gemini CLI and Claude Code...")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    hook_script = os.path.join(script_dir, "native_log_hook.py")
    if not os.path.exists(hook_script):
        print(f"❌ {hook_script} not found. Run from the repo root.")
        sys.exit(1)

    hook_command = f"python3 {hook_script}"

    print("\nGemini CLI:")
    install_gemini(hook_command)

    print("\nClaude Code:")
    install_claude(hook_command)

    print(
        "\n✨ Done. Logs will land in:"
        "\n   ~/.gemini/sessions/   (Gemini CLI / jetski)"
        "\n   ~/.claude/sessions/   (Claude Code)"
    )


if __name__ == "__main__":
    main()
