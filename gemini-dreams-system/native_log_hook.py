#!/usr/bin/env python3
import sys
import json
import os
import time
from datetime import datetime
from config_loader import load_config

def get_skill_lineage():
    # Detect both Gemini and Claude project roots
    roots = [
        os.path.expanduser("~/.gemini/skills"),
        os.path.expanduser("~/.claude/skills"),
    ]
    
    # Try local project skills if directories are set
    for env_var in ["GEMINI_PROJECT_DIR", "CLAUDE_PROJECT_DIR"]:
        if env_var in os.environ:
            local_skills = os.path.join(os.environ[env_var], ".gemini/skills")
            roots.append(local_skills)
            local_claude_skills = os.path.join(os.environ[env_var], ".claude/skills")
            roots.append(local_claude_skills)

    lineage = {}
    for root in roots:
        if not os.path.exists(root):
            continue
        try:
            for skill_name in os.listdir(root):
                skill_path = os.path.join(root, skill_name)
                if not os.path.isdir(skill_path):
                    continue
                version_file = os.path.join(skill_path, "VERSION")
                if os.path.exists(version_file):
                    with open(version_file, "r") as f:
                        lineage[skill_name] = f.read().strip()
        except Exception:
            pass
    return lineage

def main():
    start_time = time.time()
    
    # Optional agent_name from CLI argument
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "gemini_cli"
    
    try:
        # The hook payload is passed via stdin
        input_data = sys.stdin.read()
        
        # If no input is provided, just allow the interaction
        if not input_data.strip():
            print(json.dumps({"decision": "allow"}))
            return
            
        data = json.loads(input_data)
        
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
        data["cli_type"] = "gemini" if "GEMINI_PROJECT_DIR" in os.environ else "claude"
        
        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")
            
        # Must output this to stdout for the CLI to allow the response through
        print(json.dumps({"decision": "allow"}))
        
    except Exception as e:
        # If anything fails, still allow the response to proceed normally
        print(json.dumps({"decision": "allow", "systemMessage": f"Auto-logger hook error: {str(e)}"}))

if __name__ == "__main__":
    main()