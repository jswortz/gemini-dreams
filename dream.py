#!/usr/bin/env python3
import argparse
import sys
import os
import subprocess
from config_loader import load_config, DEFAULT_CONFIG_PATH
import dream_runner
import eval_checker

def main():
    parser = argparse.ArgumentParser(description="Gemini Dreams CLI - Self-improving Agent System")
    parser.add_argument("--config", type=str, help="Path to a custom config JSON file", default=DEFAULT_CONFIG_PATH)
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a dream session (analyze logs and propose improvements)")
    run_parser.add_argument("--days", type=int, help="Force lookback of N days, ignoring state file")
    
    # Eval command
    eval_parser = subparsers.add_parser("eval", help="Check skill eval coverage and run skill evaluations")
    
    # Dashboard command
    dash_parser = subparsers.add_parser("dashboard", help="Launch the Streamlit dashboard")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Print or initialize the configuration")
    config_parser.add_argument("--init", action="store_true", help="Initialize default config file")

    args = parser.parse_args()
    
    if args.command == "run":
        dream_runner.main(args.config, force_days=args.days)
    elif args.command == "eval":
        eval_checker.main(args.config)
    elif args.command == "dashboard":
        print("Launching Dashboard (FastAPI + Vite)...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Start FastAPI backend
        api_process = subprocess.Popen(["uv", "run", "python", "api.py"], cwd=script_dir)
        
        # Start Vite frontend
        frontend_dir = os.path.join(script_dir, "frontend")
        vite_process = subprocess.Popen(["npm", "run", "dev"], cwd=frontend_dir)
        
        print("API running on http://localhost:8000")
        
        try:
            api_process.wait()
            vite_process.wait()
        except KeyboardInterrupt:
            print("\nStopping dashboard...")
            api_process.terminate()
            vite_process.terminate()
    elif args.command == "config":
        config = load_config(args.config)
        print(f"Configuration (loaded from {args.config}):")
        import json
        print(json.dumps(config, indent=4))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
