import os
import json

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.gemini/dream_config.json")

def get_default_config():
    return {
        "agents": {
            "gemini_cli": {
                "logs_dir": os.path.expanduser("~/.gemini/sessions"),
                "turn_threshold": 5
            },
            "antigravity": {
                "logs_dir": os.path.expanduser("~/.antigravity/sessions"),
                "turn_threshold": 5
            },
            "jetski": {
                "logs_dir": os.path.expanduser("~/.jetski/sessions"),
                "turn_threshold": 5
            },
            "claude_code": {
                "logs_dir": os.path.expanduser("~/.claude/sessions"),
                "turn_threshold": 5
            }
        },
        "db_path": os.path.expanduser("~/.gemini/dream_metrics.db"),
        "state_path": os.path.expanduser("~/.gemini/dream_state.json"),
        "lookback_days": 1,
        "bigquery": {
            "enabled": False,
            "project_id": "your-project-id",
            "dataset_id": "gemini_dreams",
            "table_prefix": "dream_"
        },
        "headless_command": ["gemini", "run", "--headless"],
        "post_process_action": "keep",
        "skill_repository": "~/my-skills"
        }
def load_config(config_path=None):
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
        
    default_config = get_default_config()
    
    if not os.path.exists(config_path):
        # Create directory if it doesn't exist
        dir_name = os.path.dirname(config_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config

    with open(config_path, 'r') as f:
        config = json.load(f)
        
    # Ensure agents structure exists (migration/merging)
    if "agents" not in config:
        config["agents"] = default_config["agents"]
        # If the old config had a top-level logs_dir, use it for gemini_cli
        if "logs_dir" in config:
            config["agents"]["gemini_cli"]["logs_dir"] = config["logs_dir"]
            
    # Merge other top-level keys
    for key, value in default_config.items():
        if key not in config:
            config[key] = value
            
    return config

def save_config(config, config_path=None):
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
