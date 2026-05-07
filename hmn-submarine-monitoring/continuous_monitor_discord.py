#!/usr/bin/env python3
"""
HMN SUBMARINE MONITORING - Continuous Monitor & Discord Reporter
Prova de vida cada 5 minutos com detalhe máximo de todos os agentes
Envia para Discord channel: 1486678863877505064
EXECUÇÃO 100% AUTÓNOMA - Sem intervenção humana
"""

import json
import os
import time
import subprocess
from datetime import datetime, timedelta
import sys

# Configuração
PROJECT_DIR = "/Volumes/disco1tb/projects/hmn-submarine-monitoring"
SWARM_ID = "swarm-1778097400528-0g8vo4"
DISCORD_CHANNEL = "1486678863877505064"
CHECK_INTERVAL = 300  # 5 minutos em segundos

# Ficheiros de estado
AGENT_STORE = f"{PROJECT_DIR}/.claude-flow/agents/store.json"
TASK_STORE = f"{PROJECT_DIR}/.claude-flow/tasks/store.json"
SWARM_STATE = f"{PROJECT_DIR}/.claude-flow/swarm/swarm-state.json"
SPAWN_LOG = f"{PROJECT_DIR}/logs/agent-spawn.log"

# Histórico para detetar evolução
history_file = f"{PROJECT_DIR}/.monitor_history.json"

def load_history():
    """Carrega histórico de monitorização"""
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except:
            return {"checks": [], "agent_evolution": {}, "task_evolution": {}}
    return {"checks": [], "agent_evolution": {}, "task_evolution": {}}

def save_history(history):
    """Guarda histórico"""
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def read_agent_status():
    """Lê estado detalhado de todos os agentes"""
    try:
        with open(AGENT_STORE, 'r') as f:
            data = json.load(f)
            return data.get('agents', {})
    except Exception as e:
        log(f"Erro ao ler agentes: {e}")
        return {}

def read_task_status():
    """Lê estado detalhado de todas as tarefas"""
    try:
        with open(TASK_STORE, 'r') as f:
            data = json.load(f)
            return data.get('tasks', {})
    except Exception as e:
        log(f"Erro ao ler tarefas: {e}")
        return {}

def read_swarm_status():
    """Lê estado do swarm"""
    try:
        with open(SWARM_STATE, 'r') as f:
            data = json.load(f)
            return data.get('swarms', {}).get(SWARM_ID, {})
    except Exception as e:
        log(f"Erro ao ler swarm: {e}")
        return {}

def get_agent_evolution(agents, history):
    """Deteta mudanças nos agentes vs histórico anterior"""
    evolution = []
    agent_evo = history.get('agent_evolution', {})
    
    for agent_id, agent_data in agents.items():
        current_status = agent_data.get('status')
        current_task = agent_data.get('currentTask', 'none')
        
        if agent_id in agent_evo:
            prev = agent_evo[agent_id]
            if prev.get('status') != current_status:
                evolution.append(f"🔄 {agent_data.get('agentType', agent_id)}: {prev.get('status')} → {current_status}")
            if prev.get('currentTask') != current_task and current_task != 'none':
                evolution.append(f"📋 {agent_data.get('agentType', agent_id)}: nova task {current_task}")
        
        # Atualizar histórico
        history['agent_evolution'][agent_id] = {
            'status': current_status,
            'currentTask': current_task,
            'health': agent_data.get('health'),
            'taskCount': agent_data.get('taskCount', 0),
            'timestamp': datetime.now().isoformat()
        }
    
    return evolution

def get_task_evolution(tasks, history):
    """Deteta mudanças nas tarefas vs histórico anterior"""
    evolution = []
    task_evo = history.get('task_evolution', {})
    
    for task_id, task_data in tasks.items():
        current_status = task_data.get('status')
        current_progress = task_data.get('progress', 0)
        
        if task_id in task_evo:
            prev = task_evo[task_id]
            if prev.get('status') != current_status:
                evolution.append(f"📊 Task {task_id}: {prev.get('status')} → {current_status}")
            if prev.get('progress', 0) != current_progress:
                evolution.append(f"📈 Task {task_id}: progresso {prev.get('progress', 0)}% → {current_progress}%")
        
        # Atualizar histórico
        history['task_evolution'][task_id] = {
            'status': current_status,
            'progress': current_progress,
            'assignedTo': task_data.get('assignedTo', []),
            'timestamp': datetime.now().isoformat()
        }
    
    return evolution

def format_discord_message(agents, tasks, swarm, evolution_events, check_num):
    """Formata mensagem detalhada para Discord"""
    
    # Emojis por status
    status_emoji = {
        'active': '🟢',
        'idle': '🟡',
        'busy': '🔵',
        'error': '🔴',
        'registered': '⚪'
    }
    
    msg = f"**HMN SUBMARINE MONITORING - PROVA DE VIDA #{check_num}**\n"
    msg += f"_Monitorização autónoma a cada 5min_\n\n"
    
    # Métricas Swarm
    msg += f"📊 **MÉTRICAS SWARM**\n"
    msg += f"- **Swarm ID**: `{SWARM_ID}`\n"
    msg += f"- **Topology**: {swarm.get('topology', 'N/A')}\n"
    msg += f"- **Max Agents**: {swarm.get('config', {}).get('maxAgents', 'N/A')}\n"
    msg += f"- **Status Swarm**: {swarm.get('status', 'N/A')}\n"
    msg += f"- **Total Agentes**: {len(agents)}\n"
    msg += f"- **Total Tarefas**: {len(tasks)}\n\n"
    
    # Detalhe de todos os agentes
    msg += f"⚙️ **ESTADO DE TODOS OS AGENTES**\n"
    
    # Agrupar por status
    active_agents = []
    idle_agents = []
    other_agents = []
    
    for agent_id, agent_data in agents.items():
        agent_type = agent_data.get('agentType', 'unknown')
        status = agent_data.get('status', 'unknown')
        health = agent_data.get('health', 'N/A')
        task_count = agent_data.get('taskCount', 0)
        current_task = agent_data.get('currentTask', 'none')
        model = agent_data.get('model', 'N/A')
        
        agent_line = f"  **{agent_type}** ({agent_id[:20]}...)\n"
        agent_line += f"    Status: {status_emoji.get(status, '⚪')} {status} | Health: {health} | Tasks: {task_count}\n"
        if current_task != 'none':
            agent_line += f"    Task atual: `{current_task}`\n"
        agent_line += f"    Model: `{model}`\n"
        
        if status == 'active':
            active_agents.append(agent_line)
        elif status == 'idle':
            idle_agents.append(agent_line)
        else:
            other_agents.append(agent_line)
    
    if active_agents:
        msg += f"\n🟢 **ACTIVE ({len(active_agents)})**\n" + "\n".join(active_agents)
    if idle_agents:
        msg += f"\n🟡 **IDLE ({len(idle_agents)})**\n" + "\n".join(idle_agents)
    if other_agents:
        msg += f"\n⚪ **OUTROS ({len(other_agents)})**\n" + "\n".join(other_agents)
    
    # Detalhe de todas as tarefas
    if tasks:
        msg += f"\n📋 **ESTADO DE TODAS AS TAREFAS**\n"
        for task_id, task_data in tasks.items():
            status = task_data.get('status', 'unknown')
            progress = task_data.get('progress', 0)
            task_type = task_data.get('type', 'unknown')
            priority = task_data.get('priority', 'normal')
            assigned = task_data.get('assignedTo', [])
            desc = task_data.get('description', 'N/A')[:100]
            
            msg += f"\n  **Task {task_id[:20]}...**\n"
            msg += f"    Status: {status_emoji.get(status, '⚪')} {status} | Progresso: {progress}%\n"
            msg += f"    Tipo: {task_type} | Prioridade: {priority}\n"
            msg += f"    Descrição: {desc}...\n"
            if assigned:
                msg += f"    Atribuída a: {len(assigned)} agente(s)\n"
    else:
        msg += f"\n📋 **ESTADO DE TAREFAS**: Nenhuma tarefa registrada\n"
    
    # Evolução (mudanças desde último check)
    if evolution_events:
        msg += f"\n🔄 **EVOLUÇÃO DETETADA**\n"
        for event in evolution_events[:10]:  # Máximo 10 eventos
            msg += f"- {event}\n"
    else:
        msg += f"\n✅ **Sem mudanças desde último check**\n"
    
    # Rodapé
    msg += f"\n⏰ **Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} GMT\n"
    msg += f"──────\n"
    msg += f"*Próxima prova de vida em 5 minutos*"
    
    return msg

def send_to_discord(message):
    """Envia mensagem para Discord usando Hermes CLI"""
    try:
        # Usar o comando send_message do Hermes via subprocess
        # Escapar aspas no message
        escaped_message = message.replace('"', '\\"').replace('$', '\\$')
        
        cmd = f'cd {PROJECT_DIR} && echo "{escaped_message}" | hermes send --target discord:{DISCORD_CHANNEL} 2>&1'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            log(f"✓ Mensagem enviada para Discord #{DISCORD_CHANNEL}")
            return True
        else:
            log(f"✗ Erro ao enviar para Discord: {result.stderr}")
            # Fallback: guardar em ficheiro
            with open(f"{PROJECT_DIR}/logs/discord_queue.log", 'a') as f:
                f.write(f"\n=== {datetime.now().isoformat()} ===\n{message}\n")
            return False
    except Exception as e:
        log(f"✗ Exceção ao enviar para Discord: {e}")
        return False

def main():
    log("=== INÍCIO DA MONITORIZAÇÃO AUTÓNOMA CONTÍNUA ===")
    log(f"Canal Discord: #{DISCORD_CHANNEL}")
    log(f"Intervalo: {CHECK_INTERVAL}s (5 minutos)")
    
    history = load_history()
    check_num = len(history.get('checks', [])) + 1
    
    while True:
        try:
            log(f"=== CHECK #{check_num} ===")
            
            # Ler estados
            agents = read_agent_status()
            tasks = read_task_status()
            swarm = read_swarm_status()
            
            # Detetar evolução
            agent_evo = get_agent_evolution(agents, history)
            task_evo = get_task_evolution(tasks, history)
            evolution_events = agent_evo + task_evo
            
            # Formatar mensagem Discord
            message = format_discord_message(agents, tasks, swarm, evolution_events, check_num)
            
            # Enviar para Discord
            send_to_discord(message)
            
            # Atualizar histórico
            history['checks'].append({
                'check_num': check_num,
                'timestamp': datetime.now().isoformat(),
                'agent_count': len(agents),
                'task_count': len(tasks),
                'evolution_events': len(evolution_events)
            })
            
            # Manter apenas últimos 100 checks
            if len(history['checks']) > 100:
                history['checks'] = history['checks'][-100:]
            
            save_history(history)
            
            log(f"Check #{check_num} concluído. Próximo em 5 minutos.")
            check_num += 1
            
            # Aguardar 5 minutos
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("Monitorização interrompida pelo utilizador")
            break
        except Exception as e:
            log(f"Erro no loop de monitorização: {e}")
            log("A retentar em 60 segundos...")
            time.sleep(60)

if __name__ == "__main__":
    main()
