#!/usr/bin/env python3
"""
HMN SUBMARINE MONITORING - Prova de Vida para Discord
Envia para o canal: 1486678863877505064
"""

import json
import os
import subprocess
from datetime import datetime

PROJECT_DIR = "/Volumes/disco1tb/projects/hmn-submarine-monitoring"
AGENT_STORE = f"{PROJECT_DIR}/.claude-flow/agents/store.json"
TASK_STORE = f"{PROJECT_DIR}/.claude-flow/tasks/store.json"
SWARM_STATE = f"{PROJECT_DIR}/.claude-flow/swarm/swarm-state.json"
HISTORY_FILE = f"{PROJECT_DIR}/.claude-flow/.heartbeat_history.json"
DISCORD_CHANNEL = "1486678863877505064"

def load_json(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler {filepath}: {e}")
        return {}

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"check_num": 0, "last_check": None, "agents": {}, "tasks": {}}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def truncate_id(id_str, length=12):
    if len(id_str) > length:
        return id_str[:length] + "..."
    return id_str

def format_discord_message(agents, tasks, swarm, history):
    check_num = history.get("check_num", 0) + 1
    
    # Swarm info - usar o primeiro swarm running com hierarchical-mesh
    swarm_id = "N/A"
    swarm_status = "N/A"
    topology = "hierarchical-mesh"
    max_agents = 15
    
    if swarm:
        swarm_id = swarm.get("swarmId", "N/A")
        swarm_status = swarm.get("status", "N/A")
        topology = swarm.get("topology", "hierarchical-mesh")
        max_agents = swarm.get("config", {}).get("maxAgents", 15)
    
    total_agents = len(agents)
    total_tasks = len(tasks)
    
    # Build message
    msg = f"**HMN SUBMARINE MONITORING - PROVA DE VIDA CONTÍNUA #{check_num}**\n"
    msg += f"_Monitorização autónoma a cada 5min | Execução 100% sem intervenção humana_\n\n"
    
    msg += f"📊 **MÉTRICAS SWARM**\n"
    msg += f"- **Swarm ID**: {swarm_id}\n"
    msg += f"- **Topology**: {topology}\n"
    msg += f"- **Max Agents**: {max_agents}\n"
    msg += f"- **Status Swarm**: {swarm_status}\n"
    msg += f"- **Total Agentes**: {total_agents}\n"
    msg += f"- **Total Tarefas**: {total_tasks}\n\n"
    
    msg += f"⚙️ **ESTADO DE TODOS OS AGENTES**\n\n"
    
    # Active agents
    active_agents = [(aid, adata) for aid, adata in agents.items() if adata.get("status") == "active"]
    if active_agents:
        msg += f"🟢 **ACTIVE** ({len(active_agents)})\n"
        for agent_id, agent_data in active_agents:
            agent_type = agent_data.get("agentType", "unknown")
            health = agent_data.get("health", "N/A")
            task_count = agent_data.get("taskCount", 0)
            current_task = agent_data.get("currentTask", "")
            truncated_id = truncate_id(agent_id, 12)
            
            msg += f"- **{agent_type}** (`{truncated_id}`)\n"
            msg += f"  Status: 🟢 active | Health: {health} | Tasks: {task_count}\n"
            if current_task:
                msg += f"  Task atual: {current_task}\n"
            msg += f"  Modelo: smart-router (routing via litellm) ✅\n\n"
    
    # Idle agents
    idle_agents = [(aid, adata) for aid, adata in agents.items() if adata.get("status") == "idle"]
    if idle_agents:
        msg += f"🟡 **IDLE** ({len(idle_agents)})\n"
        for agent_id, agent_data in idle_agents:
            agent_type = agent_data.get("agentType", "unknown")
            health = agent_data.get("health", "N/A")
            task_count = agent_data.get("taskCount", 0)
            truncated_id = truncate_id(agent_id, 12)
            
            msg += f"- **{agent_type}** (`{truncated_id}`)\n"
            msg += f"  Status: 🟡 idle | Health: {health} | Tasks: {task_count}\n"
            msg += f"  Modelo: smart-router (routing via litellm) ✅\n"
            
            # Add special markers for architect types
            if agent_type == "architect":
                msg += f"  ⚡\n"
            elif agent_type == "security-architect":
                msg += f"  ⚡\n"
            
            msg += "\n"
    
    # Tasks
    msg += f"📋 **ESTADO DE TODAS AS TAREFAS**\n"
    if tasks:
        for task_id, task_data in tasks.items():
            status = task_data.get("status", "unknown")
            progress = task_data.get("progress", 0)
            task_type = task_data.get("type", "unknown")
            priority = task_data.get("priority", "normal")
            description = task_data.get("description", "N/A")
            if len(description) > 80:
                description = description[:80] + "..."
            assigned_to = task_data.get("assignedTo", [])
            
            status_emoji = "🟢" if status == "completed" else "🔵" if status == "in_progress" else "🟡" if status == "pending" else "⚪"
            truncated_task_id = truncate_id(task_id, 20)
            
            msg += f"\n- **{truncated_task_id}**\n"
            msg += f"  Status: {status_emoji} {status} | Progresso: {progress}%\n"
            msg += f"  Tipo: {task_type} | Prioridade: {priority}\n"
            msg += f"  Descrição: {description}\n"
            if assigned_to:
                assigned_str = ", ".join([truncate_id(a, 12) for a in assigned_to])
                msg += f"  Atribuída a: {assigned_str}\n"
    else:
        msg += "- Nenhuma tarefa registrada\n"
    
    # Evolution detection
    msg += f"\n🔄 **EVOLUÇÃO DETETADA**\n"
    evolution_found = False
    
    # Check agent changes
    prev_agents = history.get("agents", {})
    for agent_id, agent_data in agents.items():
        if agent_id in prev_agents:
            prev_status = prev_agents[agent_id].get("status")
            curr_status = agent_data.get("status")
            if prev_status != curr_status:
                msg += f"- {agent_data.get('agentType', agent_id)}: {prev_status} → {curr_status}\n"
                evolution_found = True
    
    # Check task changes
    prev_tasks = history.get("tasks", {})
    for task_id, task_data in tasks.items():
        if task_id in prev_tasks:
            prev_status = prev_tasks[task_id].get("status")
            curr_status = task_data.get("status")
            if prev_status != curr_status:
                msg += f"- Task {truncate_id(task_id, 20)}: {prev_status} → {curr_status}\n"
                evolution_found = True
            
            prev_progress = prev_tasks[task_id].get("progress", 0)
            curr_progress = task_data.get("progress", 0)
            if prev_progress != curr_progress:
                msg += f"- Task {truncate_id(task_id, 20)}: progresso {prev_progress}% → {curr_progress}%\n"
                evolution_found = True
    
    # Check for new tasks
    for task_id in tasks:
        if task_id not in prev_tasks:
            msg += f"- Nova tarefa: {truncate_id(task_id, 20)}\n"
            evolution_found = True
    
    # Check for new agents
    for agent_id in agents:
        if agent_id not in prev_agents:
            msg += f"- Novo agente: {agents[agent_id].get('agentType', agent_id)}\n"
            evolution_found = True
    
    if not evolution_found:
        msg += "- Sem mudanças desde último check\n"
    
    # Timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg += f"\n⏰ **Timestamp**: {now} GMT\n"
    msg += f"──────\n"
    msg += f"*Próxima prova de vida em 5 minutos*\n\n"
    msg += f"NOTA: Todos os agentes usam modelo \"smart-router\". O litellm proxy faz roteamento inteligente automático."
    
    return msg, check_num

def send_to_discord(message):
    """Envia mensagem para Discord usando hermes CLI"""
    try:
        # Escapar aspas e caracteres especiais
        escaped_message = message.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
        
        cmd = f'cd {PROJECT_DIR} && echo "{escaped_message}" | hermes send --target discord:{DISCORD_CHANNEL} 2>&1'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✓ Mensagem enviada para Discord #{DISCORD_CHANNEL}")
            return True
        else:
            print(f"✗ Erro ao enviar para Discord: {result.stderr}")
            # Tentar com webhook HMN como fallback
            webhook_url = os.environ.get('DISCORD_WEBHOOK_HMN') or os.environ.get('DISCORD_WEBHOOK')
            if webhook_url:
                import json
                payload = json.dumps({"content": message})
                curl_cmd = f'curl -s -X POST -H "Content-Type: application/json" -d \'{payload}\' "{webhook_url}"'
                curl_result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=30)
                if curl_result.returncode == 0:
                    print(f"✓ Mensagem enviada via webhook")
                    return True
            return False
    except Exception as e:
        print(f"✗ Exceção ao enviar para Discord: {e}")
        return False

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Enviando prova de vida...")
    
    # Load data
    agent_data = load_json(AGENT_STORE)
    task_data = load_json(TASK_STORE)
    swarm_data = load_json(SWARM_STATE)
    
    agents = agent_data.get("agents", {})
    tasks = task_data.get("tasks", {})
    
    # Get swarm info - usar o primeiro swarm running com hierarchical-mesh
    swarms = swarm_data.get("swarms", {})
    swarm_info = {}
    for sid, sdata in swarms.items():
        if sdata.get("status") == "running" and sdata.get("topology") == "hierarchical-mesh":
            swarm_info = sdata
            break
    if not swarm_info and swarms:
        swarm_info = list(swarms.values())[0]
    
    # Load history
    history = load_history()
    
    # Format message
    message, check_num = format_discord_message(agents, tasks, swarm_info, history)
    
    print("--- MENSAGEM ---")
    print(message)
    print("--- FIM MENSAGEM ---")
    
    # Send to Discord
    success = send_to_discord(message)
    
    # Update history
    history["check_num"] = check_num
    history["last_check"] = datetime.now().isoformat()
    history["agents"] = {k: {"status": v.get("status"), "taskCount": v.get("taskCount", 0)} for k, v in agents.items()}
    history["tasks"] = {k: {"status": v.get("status"), "progress": v.get("progress", 0)} for k, v in tasks.items()}
    
    save_history(history)
    
    print(f"Check #{check_num} concluído.")
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
