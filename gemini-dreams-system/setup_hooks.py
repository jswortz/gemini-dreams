#!/usr/bin/env python3
import os
import json
import sys

def get_config_paths():
    """Identify potential Gemini and Claude configuration files."""
    return {
        "gemini": os.path.expanduser("~/.gemini/settings.json"),
        "claude": os.path.expanduser("~/.clauderc")
    }

def update_config(config_path, hook_command):
    """Safely add or update the AfterAgent hook in a JSON configuration file."""
    if not os.path.exists(config_path):
        print(f"Creating new configuration file at {config_path}...")
        config = {"hooks": {"AfterAgent": []}}
    else:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {config_path} is not a valid JSON file. Skipping.")
            return False

    if "hooks" not in config:
        config["hooks"] = {}
    if "AfterAgent" not in config["hooks"]:
        config["hooks"]["AfterAgent"] = []

    # Prepare hook configurations
    new_hooks = [
        {
            "matcher": "jetski",
            "hooks": [
                {
                    "name": "jetski-logger",
                    "type": "command",
                    "command": f"{hook_command} jetski"
                }
            ]
        },
        {
            "matcher": "*",
            "hooks": [
                {
                    "name": "default-logger",
                    "type": "command",
                    "command": f"{hook_command} gemini_cli"
                }
            ]
        }
    ]

    # Check for existing hooks with the same names to avoid duplicates
    existing_hook_names = []
    for entry in config["hooks"]["AfterAgent"]:
        for hook in entry.get("hooks", []):
            existing_hook_names.append(hook.get("name"))

    for new_entry in new_hooks:
        hook_name = new_entry["hooks"][0]["name"]
        if hook_name not in existing_hook_names:
            config["hooks"]["AfterAgent"].append(new_entry)
            print(f"  ✅ Added '{hook_name}' hook to {config_path}")
        else:
            print(f"  ⏭️ Hook '{hook_name}' already exists in {config_path}. Skipping.")

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    return True

def main():
    print("🚀 Scripting native log hook installation for Gemini CLI and Claude Code...")
    
    # Get the absolute path to native_log_hook.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    hook_script_path = os.path.join(script_dir, "native_log_hook.py")
    
    if not os.path.exists(hook_script_path):
        print(f"❌ Error: {hook_script_path} not found. Please run this from the repo root.")
        sys.exit(1)

    hook_command = f"python3 {hook_script_path}"
    config_paths = get_config_paths()

    updated_any = False
    for cli_type, path in config_paths.items():
        print(f"Checking {cli_type} configuration...")
        if update_config(path, hook_command):
            updated_any = True

    if updated_any:
        print("\n✨ Installation complete! Your interactions will now be automatically logged.")
        print(f"Logs will be stored in ~/.gemini/sessions/ and ~/.jetski/sessions/")
    else:
        print("\n❌ No configuration files were updated.")

if __name__ == "__main__":
    main()