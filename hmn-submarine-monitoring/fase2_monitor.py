#!/usr/bin/env python3
"""Monitor Fase 2 tasks - simple polling until completion"""
import subprocess
import time
from datetime import datetime

PROJECT_DIR = "/Volumes/disco1tb/projects/hmn-submarine-monitoring"
SWARM_ID = "swarm-1778097400528-0g8vo4"
RUFLO = "/usr/local/bin/ruflo"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def get_tasks_status():
    """Get current tasks status"""
    try:
        result = subprocess.run(
            f"cd {PROJECT_DIR} && {RUFLO} task list --swarm {SWARM_ID}",
            shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

def main():
    log("=== MONITOR FASE 2 INICIADO ===")
    
    completed = 0
    total = 3
    
    while completed < total:
        output = get_tasks_status()
        
        # Count completed tasks
        completed = output.count('completed') + output.count('100%')
        in_progress = output.count('in_progress')
        
        log(f"Status: {completed}/{total} concluídas, {in_progress} em progresso")
        
        # Print task summary
        for line in output.split('\n'):
            if 'implementation' in line or 'pending' in line or 'in_progress' in line or '%' in line:
                log(f"  {line.strip()}")
        
        if completed < total:
            log("Aguardando 60s...")
            time.sleep(60)
    
    log("=== FASE 2 CONCLUÍDA! ===")

if __name__ == "__main__":
    main()
