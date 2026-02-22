#!/bin/bash
# Pipeline Summary Generator — Relatório detalhado a cada 15 min
# Inclui: atividade últimos 15min + métricas 2 meses

WORKSPACE="/Users/augustosilva/clawd/innovation-team"
REPORT_FILE="$WORKSPACE/reports/pipeline-summary-$(date +%Y-%m-%d).md"
LOG_DIR="$WORKSPACE/logs"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
TODAY=$(date +%Y-%m-%d)

mkdir -p "$WORKSPACE/reports"

# ============================================
# 1. ATIVIDADE ÚLTIMOS 15 MINUTOS
# ============================================
cat > "$REPORT_FILE" << EOF
# 📊 Pipeline Summary — $TIMESTAMP

## 🔄 Últimos 15 Minutos

EOF

# Novas oportunidades
NEW_OPPS=$(find "$WORKSPACE/opportunities" -name "*.md" -not -name "template.md" -mmin -15 2>/dev/null | wc -l)
if [ "$NEW_OPPS" -gt 0 ]; then
    echo "- **Novas oportunidades:** $NEW_OPPS" >> "$REPORT_FILE"
    for f in "$WORKSPACE/opportunities"/*.md; do
        [ -f "$f" ] && [ "$(basename "$f")" != "template.md" ] && {
            echo "  - $(basename "$f" .md)" >> "$REPORT_FILE"
        }
    done
else
    echo "- **Novas oportunidades:** 0" >> "$REPORT_FILE"
fi

# Backlog atual
BACKLOG=$(find "$WORKSPACE/backlog/pending" -name "*.md" 2>/dev/null | wc -l)
echo "- **Backlog pending:** $BACKLOG ideias" >> "$REPORT_FILE"

# Em votação
FORUM=$(find "$WORKSPACE/backlog/forum" -name "*.md" 2>/dev/null | wc -l)
echo "- **Em votação:** $FORUM ideias" >> "$REPORT_FILE"

# Projetos ativos
ACTIVE=$(find "$WORKSPACE/../projects" -maxdepth 1 -type d | grep -v "^$WORKSPACE/../projects$" | wc -l)
echo "- **Projetos ativos:** $ACTIVE" >> "$REPORT_FILE"

# Projetos validados
VALIDATED=$(find "$WORKSPACE/backlog/validadas" -name "*.md" 2>/dev/null | wc -l)
echo "- **Projetos validados (total):** $VALIDATED" >> "$REPORT_FILE"

# ============================================
# 2. MÉTRICAS ÚLTIMOS 2 MESES
# ============================================
cat >> "$REPORT_FILE" << EOF

## 📈 Métricas — Últimos 60 Dias

### Throughput
EOF

# Contar oportunidades criadas nos últimos 60 dias
OPPS_60D=$(find "$WORKSPACE/backlog" -name "*.md" -mtime -60 2>/dev/null | wc -l)
echo "- **Ideias processadas (60d):** $OPPS_60D" >> "$REPORT_FILE"

# Calcular approval rate (ideias validadas / total em votação)
APPROVED_60D=$(find "$WORKSPACE/backlog/validadas" -name "*.md" -mtime -60 2>/dev/null | wc -l)
if [ "$OPPS_60D" -gt 0 ]; then
    APPROVAL_RATE=$((APPROVED_60D * 100 / OPPS_60D))
else
    APPROVAL_RATE=0
fi
echo "- **Taxa de aprovação:** ${APPROVAL_RATE}%" >> "$REPORT_FILE"

# Projetos arquivados (rejeitados)
ARCHIVED=$(find "$WORKSPACE/backlog/arquivado" -name "*.md" -mtime -60 2>/dev/null | wc -l)
echo "- **Ideias arquivadas:** $ARCHIVED" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "### Pipeline Health" >> "$REPORT_FILE"
echo "- **Projetos atuais ativos:** $ACTIVE" >> "$REPORT_FILE"
echo "- **Capacidade utilizada:** ${ACTIVE}/4 slots" >> "$REPORT_FILE"

if [ "$BACKLOG" -le 8 ]; then
    BACKLOG_STATUS="🟢 Saudável"
elif [ "$BACKLOG" -le 10 ]; then
    BACKLOG_STATUS="🟡 Atenção"
else
    BACKLOG_STATUS="🟠 Limite"
fi
echo "- **Estado do backlog:** $BACKLOG_STATUS ($BACKLOG ideias)" >> "$REPORT_FILE"

# ============================================
# 3. HISTÓRICO DETALHADO (2 meses)
# ============================================
cat >> "$REPORT_FILE" << EOF

## 📜 Histórico Detalhado (2 Meses)

### Projetos Criados
EOF

# Listar projetos validados com datas
for f in "$WORKSPACE/backlog/validadas"/*.md; do
    [ -f "$f" ] && {
        PROJ_NAME=$(basename "$f" .md)
        PROJ_DATE=$(stat -f "%Sm" -t "%Y-%m-%d" "$f")
        echo "- **$PROJ_NAME** — $PROJ_DATE" >> "$REPORT_FILE"
    }
done

echo "" >> "$REPORT_FILE"
echo "### Decisões de Fórum (últimos 60 dias)" >> "$REPORT_FILE"
if [ -d "$WORKSPACE/forum/decisions" ]; then
    for f in "$WORKSPACE/forum/decisions"/*.md; do
        [ -f "$f" ] && {
            DECISION=$(basename "$f" .md)
            echo "- $DECISION" >> "$REPORT_FILE"
        }
    done
else
    echo "- *Nenhuma decisão registada*" >> "$REPORT_FILE"
fi

# ============================================
# 4. TENDÊNCIAS
# ============================================
cat >> "$REPORT_FILE" << EOF

## 📊 Tendências

EOF

# Calcular média diária de ideias
IDEAS_PER_DAY=$((OPPS_60D / 60))
echo "- **Média ideias/dia:** $IDEAS_PER_DAY" >> "$REPORT_FILE"

# Tempo médio no backlog (estimado)
if [ "$OPPS_60D" -gt 0 ]; then
    AVG_DAYS=$((60 * BACKLOG / OPPS_60D))
    echo "- **Tempo médio no backlog:** ~${AVG_DAYS} dias" >> "$REPORT_FILE"
else
    echo "- **Tempo médio no backlog:** N/A" >> "$REPORT_FILE"
fi

# ============================================
# 5. AÇÕES RECOMENDADAS
# ============================================
cat >> "$REPORT_FILE" << EOF

## 🎯 Ações Recomendadas

EOF

if [ "$BACKLOG" -gt 10 ]; then
    echo "⚠️ **BACKLOG ALTO:** Considerar aumentar capacity de projetos simultâneos (4→6)" >> "$REPORT_FILE"
fi

if [ "$FORUM" -eq 0 ] && [ "$BACKLOG" -gt 0 ]; then
    echo "📋 **Convocar fórum:** Há ideias pendentes de votação" >> "$REPORT_FILE"
fi

if [ "$ACTIVE" -lt 4 ] && [ "$VALIDATED" -gt "$ACTIVE" ]; then
    echo "🚀 **Iniciar projeto:** Slots disponíveis para novos projetos" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "*Gerado automaticamente pelo Pipeline Manager | Próximo: 15 minutos*" >> "$REPORT_FILE"

# Log da geração
echo "[$TIMESTAMP] Summary generated: $(basename $REPORT_FILE)" >> "$LOG_DIR/pipeline-manager-$TODAY.log"
