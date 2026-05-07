#!/bin/bash
# Monitorização da nova tarefa do researcher
LOG="/Volumes/disco1tb/projects/hmn-submarine-monitoring/logs/new-task-monitor.log"
TASK_ID="task-1778107040348-1d7iu7"
SWARM_ID="swarm-moumze5c"
RUFLO="/usr/local/bin/ruflo"

echo "[$(date)] === INÍCIO MONITORIZAÇÃO NOVA TAREFA ===" >> "$LOG"
echo "[$(date)] Task: $TASK_ID | Swarm: $SWARM_ID" >> "$LOG"

for i in {1..60}; do  # 60 iterações = 60 minutos
    # Obter status da tarefa
    STATUS=$($RUFLO task status $TASK_ID --swarm $SWARM_ID 2>&1)
    PROGRESS=$(echo "$STATUS" | grep "Progress:" | awk '{print $2}')
    TASK_STATUS=$(echo "$STATUS" | grep "Status:" | awk '{print $2}')
    
    echo "[$(date)] Iteração $i: Status=$TASK_STATUS | Progresso=$PROGRESS" >> "$LOG"
    
    # Se progresso > 0%, relatar
    if [[ "$PROGRESS" != "0%" && -n "$PROGRESS" ]]; then
        echo "[$(date)] 🎉 PROGRESSO DETETADO: $PROGRESS" >> "$LOG"
        $RUFLO task status $TASK_ID --swarm $SWARM_ID >> "$LOG"
        break
    fi
    
    # Se tarefa concluída ou erro
    if [[ "$TASK_STATUS" == "completed" || "$TASK_STATUS" == "failed" ]]; then
        echo "[$(date)] 🏁 TAREFA FINALIZADA: $TASK_STATUS" >> "$LOG"
        $RUFLO task status $TASK_ID --swarm $SWARM_ID >> "$LOG"
        break
    fi
    
    sleep 60
done

echo "[$(date)] === FIM MONITORIZAÇÃO ===" >> "$LOG"
