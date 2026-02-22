#!/bin/bash
# Pipeline Manager Cron — 24/7 Ideation Pipeline
# Frequência: Cada 15 minutos

WORKSPACE="/Users/augustosilva/clawd/innovation-team"
LOG_FILE="$WORKSPACE/logs/pipeline-manager-$(date +%Y-%m-%d).log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$WORKSPACE/logs"

echo "[$TIMESTAMP] Pipeline Manager check-in" >> "$LOG_FILE"

# 1. Verificar novas oportunidades
OPPORTUNITIES=$(find "$WORKSPACE/opportunities" -name "*.md" -not -name "template.md" 2>/dev/null | wc -l)
if [ "$OPPORTUNITIES" -gt 0 ]; then
    echo "[$TIMESTAMP] Found $OPPORTUNITIES new opportunities" >> "$LOG_FILE"
    # Mover para pending e notificar Validator
    for file in "$WORKSPACE/opportunities"/*.md; do
        [ -f "$file" ] && [ "$(basename "$file")" != "template.md" ] && {
            mv "$file" "$WORKSPACE/backlog/pending/"
            echo "[$TIMESTAMP] Moved $(basename "$file") to pending" >> "$LOG_FILE"
        }
    done
fi

# 2. Verificar backlog (política: saudável <50, normal 50-75, atenção 75-100, limite >100)
BACKLOG=$(find "$WORKSPACE/backlog/pending" -name "*.md" 2>/dev/null | wc -l)
echo "[$TIMESTAMP] Backlog atual: $BACKLOG ideias" >> "$LOG_FILE"

if [ "$BACKLOG" -ge 150 ]; then
    echo "[$TIMESTAMP] 🆘 BACKLOG CRÍTICO: $BACKLOG ideias — ESCALAÇÃO IMEDIATA" >> "$LOG_FILE"
elif [ "$BACKLOG" -ge 100 ]; then
    echo "[$TIMESTAMP] 🔴 BACKLOG LIMITE: $BACKLOG ideias (máx 100) — ralentizar significativamente" >> "$LOG_FILE"
elif [ "$BACKLOG" -ge 75 ]; then
    echo "[$TIMESTAMP] 🟠 BACKLOG ATENÇÃO: $BACKLOG ideias (aproximando 100)" >> "$LOG_FILE"
elif [ "$BACKLOG" -ge 50 ]; then
    echo "[$TIMESTAMP] 🟡 BACKLOG INFO: $BACKLOG ideias (metade da capacidade)" >> "$LOG_FILE"
fi

# 3. Verificar ideias em votação >24h sem decisão
# (lógica implementada no agente)

# 3. Verificar projetos aprovados sem canal criado
VALIDATED=$(find "$WORKSPACE/backlog/validadas" -name "*.md" 2>/dev/null | wc -l)
echo "[$TIMESTAMP] Validated projects: $VALIDATED" >> "$LOG_FILE"

# 4. Check pipeline capacity
ACTIVE_PROJECTS=$(find "$WORKSPACE/../projects" -maxdepth 1 -type d | wc -l)
echo "[$TIMESTAMP] Active projects: $ACTIVE_PROJECTS" >> "$LOG_FILE"

# 5. Report via Discord (se houver novidades)
if [ "$OPPORTUNITIES" -gt 0 ] || [ "$VALIDATED" -gt 0 ]; then
    echo "[$TIMESTAMP] Pipeline activity detected — reporting" >> "$LOG_FILE"
fi

# Gerar relatório detalhado com histórico de 2 meses
"$WORKSPACE/reports/summary-generator.sh"

echo "[$TIMESTAMP] Check complete" >> "$LOG_FILE"
