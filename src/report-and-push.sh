#!/bin/bash
# Report & Push — Gera relatório e faz push para GitHub
# Executado a cada 15 minutos pelo Pipeline Manager

REPO_DIR="/Users/augustosilva/clawd/projects/ideation-pipeline-board"
WORKSPACE="/Users/augustosilva/clawd/innovation-team"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H-%M)

# Gerar relatório
"$REPO_DIR/src/summary-generator.sh"

# Copiar relatório para o repositório
REPORT_SRC="$WORKSPACE/reports/pipeline-summary-$DATE.md"
REPORT_DEST="$REPO_DIR/reports/daily/pipeline-summary-$DATE.md"

mkdir -p "$REPO_DIR/reports/daily"

if [ -f "$REPORT_SRC" ]; then
    cp "$REPORT_SRC" "$REPORT_DEST"
    
    # Atualizar status no README
    BACKLOG=$(find "$WORKSPACE/backlog/pending" -name "*.md" 2>/dev/null | wc -l)
    ACTIVE=$(find "$WORKSPACE/../projects" -maxdepth 1 -type d | grep -v "^$WORKSPACE/../projects$" | wc -l)
    
    cat > "$REPO_DIR/STATUS.md" << EOF
# Status em Tempo Real

**Última atualização:** $TIMESTAMP

## 📊 Métricas Atuais

| Métrica | Valor |
|---------|-------|
| Backlog | $BACKLOG/100 ideias |
| Projetos Ativos | $ACTIVE |
| Status Pipeline | 🟢 Ativo 24/7 |

## 🔄 Última Atividade

- Ver relatório em: \`reports/daily/pipeline-summary-$DATE.md\`

## 📈 Dashboard

- [Relatório de Hoje](reports/daily/pipeline-summary-$DATE.md)
- [Histórico](reports/daily/)

---
*Atualizado automaticamente a cada 15 minutos*
EOF

    # Commit e push
    cd "$REPO_DIR"
    git add -A
    git commit -m "Report update: $TIMESTAMP | Backlog: $BACKLOG | Projects: $ACTIVE" --quiet
    git push origin main --quiet
    
    echo "[$TIMESTAMP] Report pushed to GitHub: backlog=$BACKLOG, projects=$ACTIVE"
else
    echo "[$TIMESTAMP] No report generated"
fi
