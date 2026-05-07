#!/usr/bin/env python3
"""
SISTEMA AUTÓNOMO: Monitorização de Task + Avanço Fase 2
Sem intervenção humana - decisão baseada em PHASE2_AUTONOMOUS_CRITERIA.md
"""

import json
import os
import time
import subprocess
from datetime import datetime

SWARM_ID = "swarm-1778097400528-0g8vo4"
PROJECT_DIR = "/Volumes/disco1tb/projects/hmn-submarine-monitoring"
TASK_STORE = f"{PROJECT_DIR}/.claude-flow/tasks/store.json"
AGENT_STORE = f"{PROJECT_DIR}/.claude-flow/agents/store.json"
PHASE2_CRITERIA = f"{PROJECT_DIR}/PHASE2_AUTONOMOUS_CRITERIA.md"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def read_task_status():
    """Lê estado da task do researcher"""
    try:
        with open(TASK_STORE, 'r') as f:
            data = json.load(f)
            for task_id, task in data.get('tasks', {}).items():
                if task.get('assignedTo') and 'agent-1778097644463-oqv1a3' in task.get('assignedTo', []):
                    return task
    except Exception as e:
        log(f"Erro ao ler task store: {e}")
    return None

def read_agent_status():
    """Lê estado dos agentes"""
    try:
        with open(AGENT_STORE, 'r') as f:
            data = json.load(f)
            return data.get('agents', {})
    except Exception as e:
        log(f"Erro ao ler agent store: {e}")
        return {}

def check_research_outputs():
    """Verifica se existem ficheiros de output do research"""
    output_patterns = [
        f"{PROJECT_DIR}/outputs/research_results_NMS.json",
        f"{PROJECT_DIR}/outputs/research_*.md",
        f"{PROJECT_DIR}/.claude-flow/outputs/*research*"
    ]
    outputs = []
    for pattern in output_patterns:
        if '*' in pattern:
            import glob
            outputs.extend(glob.glob(pattern))
        else:
            if os.path.exists(pattern):
                outputs.append(pattern)
    return outputs

def analyze_research_results():
    """Lê e analisa resultados do research para decidir Fase 2"""
    outputs = check_research_outputs()
    
    if not outputs:
        log("Nenhum ficheiro de output encontrado. Task pode ainda estar a correr.")
        return None
    
    # Ler primeiro ficheiro encontrado
    output_file = outputs[0]
    log(f"Analisando resultados: {output_file}")
    
    try:
        with open(output_file, 'r') as f:
            content = f.read()
        
        # Análise simples: detetar protocolos mencionados
        protocols = {
            'SNMP': 'snmp' in content.lower(),
            'NetConf': 'netconf' in content.lower(),
            'YANG': 'yang' in content.lower(),
            'OTDR': 'otdr' in content.lower(),
            'FBG': 'fbg' in content.lower()
        }
        
        log(f"Protocolos detetados: {protocols}")
        return protocols
    except Exception as e:
        log(f"Erro ao ler output: {e}")
        return None

def create_phase2_tasks(protocols):
    """Cria tarefas Fase 2 baseadas nos resultados do research"""
    log("=== CRIAÇÃO AUTÓNOMA DE TAREFAS FASE 2 ===")
    
    tasks_created = []
    
    # Task 1: SNMP (se detetado)
    if protocols.get('SNMP'):
        log("CRIANDO: Task SNMP Integration para hmn-coder")
        cmd = f"cd {PROJECT_DIR} && /usr/local/bin/ruflo task create --type implementation --name 'Fase2: SNMP Integration' --description 'Implementar SNMP poller para NMS usando pysnmp baseado no research' --swarm {SWARM_ID} --assigned-agent agent-1778097772903-ppipho --non-interactive"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            tasks_created.append("SNMP Integration")
            log("✓ Task SNMP criada")
        else:
            log(f"✗ Erro ao criar task SNMP: {result.stderr}")
    
    # Task 2: NetConf/YANG (se detetado)
    if protocols.get('NetConf') or protocols.get('YANG'):
        log("CRIANDO: Task NetConf/YANG Integration para hmn-coder")
        cmd = f"cd {PROJECT_DIR} && /usr/local/bin/ruflo task create --type implementation --name 'Fase2: NetConf/YANG Integration' --description 'Implementar NetConf client com YANG models baseado no research' --swarm {SWARM_ID} --assigned-agent agent-1778097772903-ppipho --non-interactive"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            tasks_created.append("NetConf/YANG Integration")
            log("✓ Task NetConf/YANG criada")
        else:
            log(f"✗ Erro ao criar task NetConf/YANG: {result.stderr}")
    
    # Task 3: OTDR/FBG (se detetado)
    if protocols.get('OTDR') or protocols.get('FBG'):
        log("CRIANDO: Task Optical Probe Processing para hmn-analyst")
        cmd = f"cd {PROJECT_DIR} && /usr/local/bin/ruflo task create --type analysis --name 'Fase2: Optical Probe Data Processing' --description 'Processar dados OTDR/FBG das sondas HMN' --swarm {SWARM_ID} --assigned-agent agent-1778097870487-1coy25 --non-interactive"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            tasks_created.append("Optical Probe Processing")
            log("✓ Task Optical Probe criada")
        else:
            log(f"✗ Erro ao criar task Optical: {result.stderr}")
    
    return tasks_created

def update_todo_list():
    """Atualiza todo list: Fase 1 → completed, Fase 2 → in_progress"""
    log("Atualizando todo list...")
    # Isto seria feito via Hermes todo tool, mas como é script autónomo,
    # vamos criar um ficheiro de sinalização
    with open(f"{PROJECT_DIR}/.phase2_ready", 'w') as f:
        f.write(f"Phase 2 ready at {datetime.now().isoformat()}\n")
    log("✓ Sinalizado: Fase 2 pronta para iniciar")

def main():
    log("=== INÍCIO DA MONITORIZAÇÃO AUTÓNOMA ===")
    log(f"Swarm: {SWARM_ID}")
    
    # Verificar estado inicial
    task = read_task_status()
    if not task:
        log("ERRO: Task do researcher não encontrada!")
        return
    
    log(f"Task status inicial: {task.get('status')} (progress: {task.get('progress')}%)")
    
    # Loop de monitorização (vai correr até task completar)
    while True:
        task = read_task_status()
        
        if not task:
            log("Task não encontrada. Aguardando...")
            time.sleep(60)
            continue
        
        status = task.get('status')
        progress = task.get('progress', 0)
        
        log(f"Task status: {status} | Progress: {progress}%")
        
        if status == 'completed':
            log("=== TASK COMPLETADA! ===")
            
            # Analisar resultados
            protocols = analyze_research_results()
            
            if protocols:
                # Criar tarefas Fase 2 autonomamente
                tasks = create_phase2_tasks(protocols)
                
                # Atualizar todo list
                update_todo_list()
                
                log(f"=== FASE 2 INICIADA AUTONOMAMENTE ===")
                log(f"Tarefas criadas: {tasks}")
                
                # Sinalizar conclusão
                with open(f"{PROJECT_DIR}/.phase2_started", 'w') as f:
                    f.write(f"Phase 2 started at {datetime.now().isoformat()}\n")
                    f.write(f"Tasks: {tasks}\n")
                
                break
            else:
                log("Sem resultados de research. Aguardando ficheiros de output...")
                time.sleep(60)
                continue
                
        elif status == 'failed':
            log("=== TASK FAILED! ===")
            log("Tentando respawn do researcher...")
            # Aqui poderia fazer spawn de novo researcher
            break
            
        else:
            # Ainda em progresso, aguardar
            log("Task em progresso. Aguardando 60s...")
            time.sleep(60)

if __name__ == "__main__":
    main()
