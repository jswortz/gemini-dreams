#!/usr/bin/env python3
import sys
import json
import os
import time
from datetime import datetime
from config_loader import load_config

def get_skill_lineage():
    roots = [
        os.path.expanduser("~/.gemini/skills"),
        os.path.expanduser("~/.claude/skills"),
    ]
    for env_var in ["GEMINI_PROJECT_DIR", "CLAUDE_PROJECT_DIR"]:
        if env_var in os.environ:
            roots.append(os.path.join(os.environ[env_var], ".gemini/skills"))
            roots.append(os.path.join(os.environ[env_var], ".claude/skills"))
            
    lineage = {}
    for root in roots:
        if not os.path.exists(root):
            continue
        try:
            for skill_name in os.listdir(root):
                skill_path = os.path.join(root, skill_name)
                if not os.path.isdir(skill_path):
                    continue
                # Try VERSION first
                version_file = os.path.join(skill_path, "VERSION")
                if os.path.exists(version_file):
                    with open(version_file, "r") as f:
                        lineage[skill_name] = f.read().strip()
                else:
                    # Try SKILL.md frontmatter for version, otherwise default to 1.0.0
                    skill_md = os.path.join(skill_path, "SKILL.md")
                    version = "1.0.0"
                    if os.path.exists(skill_md):
                        with open(skill_md, "r") as f:
                            for i, line in enumerate(f):
                                if i > 50: break # only check top
                                if line.startswith("version:"):
                                    version = line.split(":", 1)[1].strip().strip('"\'')
                                    break
                    lineage[skill_name] = version
        except Exception:
            pass
    return lineage
def _extract_text(content):
    """Pull plain text out of a Claude Code message.content (str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                parts.append(block.get("text", ""))
            elif btype == "thinking":
                continue
            elif btype == "tool_use":
                parts.append(f"[tool_use:{block.get('name')}]")
            elif btype == "tool_result":
                tr = block.get("content")
                if isinstance(tr, str):
                    parts.append(f"[tool_result] {tr[:500]}")
        return "\n".join(p for p in parts if p)
    return ""


def _extract_text_only(content):
    """Extract only real text blocks from content, ignoring tool_use/tool_result."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(p for p in parts if p)
    return ""


def _extract_tool_names(content):
    """Extract tool names from tool_use blocks in message content."""
    if not isinstance(content, list):
        return []
    return [
        block.get("name")
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name")
    ]


def _normalize_claude_payload(data):
    """Convert a Claude Code Stop/UserPromptSubmit payload into the
    {prompt, prompt_response, session_id, ...} shape the dream_runner expects."""
    out = {
        "session_id": data.get("session_id", "default_session"),
        "cwd": data.get("cwd"),
        "hook_event_name": data.get("hook_event_name"),
        "transcript_path": data.get("transcript_path"),
    }

    if "prompt" in data:
        out["prompt"] = data["prompt"]

    transcript_path = data.get("transcript_path")
    if transcript_path and os.path.exists(transcript_path):
        last_user_text = None
        last_assistant_text = None
        last_text_response = None
        all_tools = []
        try:
            with open(transcript_path, "r") as tf:
                for line in tf:
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    etype = entry.get("type")
                    msg = entry.get("message") or {}
                    if etype == "user" and msg.get("role") == "user":
                        text = _extract_text(msg.get("content"))
                        if text and not text.startswith("[tool_result]"):
                            last_user_text = text
                    elif etype == "assistant" and msg.get("role") == "assistant":
                        content = msg.get("content")
                        text = _extract_text(content)
                        if text:
                            last_assistant_text = text
                        real_text = _extract_text_only(content)
                        if real_text:
                            last_text_response = real_text
                        all_tools.extend(_extract_tool_names(content))
        except Exception:
            pass

        if last_user_text and "prompt" not in out:
            out["prompt"] = last_user_text
        out["prompt_response"] = last_text_response or last_assistant_text
        if all_tools:
            out["tools_used"] = list(dict.fromkeys(all_tools))

    return out


def main():
    start_time = time.time()

    # Optional agent_name from CLI argument
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "gemini_cli"

    try:
        # The hook payload is passed via stdin
        input_data = sys.stdin.read()

        # If no input is provided, just allow the interaction
        if not input_data.strip():
            print(json.dumps({"continue": True, "suppressOutput": True}))
            return

        data = json.loads(input_data)

        # Detect Claude Code by hook payload shape and normalize
        is_claude = "hook_event_name" in data or "transcript_path" in data
        if is_claude:
            agent_name = "claude_code"
            data = _normalize_claude_payload(data)

        # Load configuration to find the correct logs directory
        config = load_config()
        agents_config = config.get("agents", {})

        # Fallback to claude_code if no GEMINI_PROJECT_DIR but CLAUDE_PROJECT_DIR is set
        if agent_name == "gemini_cli" and "CLAUDE_PROJECT_DIR" in os.environ and "GEMINI_PROJECT_DIR" not in os.environ:
            agent_name = "claude_code"
            
        # Get logs dir for this agent
        agent_info = agents_config.get(agent_name, agents_config.get("gemini_cli", {}))
        logs_dir = agent_info.get("logs_dir", "~/.gemini/sessions")
        logs_dir = os.path.expanduser(logs_dir)
        os.makedirs(logs_dir, exist_ok=True)
        
        # History is tracked in agent_name_history.jsonl
        log_file = os.path.join(logs_dir, f"{agent_name}_history.jsonl")
        
        # Add metadata
        data["timestamp"] = datetime.now().isoformat()
        data["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        data["skills"] = get_skill_lineage()
        data["agent_name"] = agent_name
        if is_claude:
            data["cli_type"] = "claude"
        else:
            data["cli_type"] = "gemini" if "GEMINI_PROJECT_DIR" in os.environ else "claude"
        
        
        # Try to extract tool & model metadata
        # Some hooks pass 'model', or it could be inside 'prompt' or 'response'
        if 'model' in data:
            pass # already there
        elif 'model_name' in data:
            data['model'] = data['model_name']
        elif 'GEMINI_MODEL' in os.environ:
            data['model'] = os.environ['GEMINI_MODEL']
        else:
            data['model'] = 'gemini-3-flash-preview' # Assumed fallback per rule
        
        # Tools: if the payload contains tools_called or similar
        tools = []
        if 'tools_called' in data:
            tools = data['tools_called']
        elif 'tools' in data:
            tools = data['tools']
        elif 'tool_calls' in data:
            tools = data['tool_calls']
        elif 'response' in data and '"name":' in str(data['response']):
            # naive heuristic if it's stringified
            pass

        if tools:
            data['tools_used'] = tools

        # For debug, save full raw input
        try:
            with open(os.path.join(logs_dir, "latest_raw_payload.json"), "w") as rf:
                rf.write(input_data)
        except Exception:
            pass

        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")

        # Output silent continuation. Both Gemini CLI and Claude Code accept
        # an empty/{"continue": true} response as "allow this turn through".
        if is_claude:
            print(json.dumps({"continue": True, "suppressOutput": True}))
        else:
            print(json.dumps({"decision": "allow"}))

    except Exception as e:
        # If anything fails, still allow the response to proceed normally
        try:
            if 'is_claude' in locals() and is_claude:
                print(json.dumps({"continue": True, "suppressOutput": True}))
                return
        except Exception:
            pass
        print(json.dumps({"decision": "allow", "systemMessage": f"Auto-logger hook error: {str(e)}"}))

if __name__ == "__main__":
    main()