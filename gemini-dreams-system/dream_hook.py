import sys
import os
import json
from datetime import datetime
from config_loader import load_config

def main():
    if len(sys.argv) < 2:
        print("Usage: python dream_hook.py <agent_name>")
        sys.exit(1)
        
    agent_name = sys.argv[1]
    config = load_config() # Load default config
    
    # Find logs dir for this agent
    agents_config = config.get("agents", {})
    if agent_name not in agents_config:
        print(f"Agent {agent_name} not found in config.")
        sys.exit(1)
        
    logs_dir = agents_config[agent_name].get("logs_dir")
    logs_dir = os.path.expanduser(logs_dir)
    
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)
        
    log_file = os.path.join(logs_dir, f"{agent_name}_history.jsonl")
    
    # Read from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        try:
            # Verify it's valid JSON
            data = json.loads(line)
            
            # Add timestamp if not present
            if "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()
                
            # Append to JSONL
            with open(log_file, 'a') as f:
                f.write(json.dumps(data) + "\n")
        except json.JSONDecodeError:
            # If not JSON, wrap it in a log object
            data = {
                "timestamp": datetime.now().isoformat(),
                "message": line
            }
            with open(log_file, 'a') as f:
                f.write(json.dumps(data) + "\n")
            
if __name__ == "__main__":
    main()
