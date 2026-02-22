#!/bin/bash
# Innovation Team Metrics Dashboard — Estratégico
# Métricas + Análise de alinhamento estratégico

WORKSPACE="/Users/augustosilva/clawd/innovation-team"
REPORT_FILE="$WORKSPACE/reports/metrics-dashboard.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE=$(date +%Y-%m-%d)
WEEK=$(date +%Y-%W)

# Tema atual
THEME="AI Developer Tools"
THEME_WEEK="2026-W09"

# Calcular métricas
IDEAS_DAY=$(find "$WORKSPACE/opportunities" -name "*.md" -mtime -1 2>/dev/null | wc -l)
IDEAS_WEEK=$(find "$WORKSPACE/opportunities" "$WORKSPACE/backlog/pending" -name "*.md" -mtime -7 2>/dev/null | wc -l)
PENDING=$(find "$WORKSPACE/backlog/pending" -name "*.md" 2>/dev/null | wc -l)
FORUM=$(find "$WORKSPACE/backlog/forum" -name "*.md" 2>/dev/null | wc -l)
VALIDATED=$(find "$WORKSPACE/backlog/validadas" -name "*.md" 2>/dev/null | wc -l)
TOTAL_PIPELINE=$((PENDING + FORUM))

# Categorias (análise de conteúdo)
CODE_GEN=$(grep -l -i "code.generation\|copilot\|completion" "$WORKSPACE/opportunities"/*.md "$WORKSPACE/backlog/pending"/*.md 2>/dev/null | wc -l)
DEVOPS=$(grep -l -i "devops\|deploy\|infra" "$WORKSPACE/opportunities"/*.md "$WORKSPACE/backlog/pending"/*.md 2>/dev/null | wc -l)
TESTING=$(grep -l -i "test\|qa\|bug" "$WORKSPACE/opportunities"/*.md "$WORKSPACE/backlog/pending"/*.md 2>/dev/null | wc -l)
DOCS=$(grep -l -i "doc\|documentation" "$WORKSPACE/opportunities"/*.md "$WORKSPACE/backlog/pending"/*.md 2>/dev/null | wc -l)
DEBUG=$(grep -l -i "debug\|log\|error" "$WORKSPACE/opportunities"/*.md "$WORKSPACE/backlog/pending"/*.md 2>/dev/null | wc -l)

# Alinhamento estratégico (% que menciona o tema)
THEME_ALIGNED=$(grep -l -i "ai\|developer\|dev\|code" "$WORKSPACE/opportunities"/*.md "$WORKSPACE/backlog/pending"/*.md 2>/dev/null | wc -l)
if [ "$IDEAS_WEEK" -gt 0 ]; then
    ALIGNMENT=$((THEME_ALIGNED * 100 / IDEAS_WEEK))
else
    ALIGNMENT=0
fi

# Gerar dashboard
cat > "$REPORT_FILE" << EOF
# 📊 Innovation Team Metrics Dashboard

**Período:** $DATE | Semana $THEME_WEEK  
**Tema Estratégico:** $THEME  
**Última atualização:** $TIMESTAMP

---

## 📈 Métricas Operacionais

| Métrica | Atual | Target | Status | Trend |
|---------|-------|--------|--------|-------|
| 📝 Ideias/dia | $IDEAS_DAY | 2-3 | $(if [ "$IDEAS_DAY" -ge 2 ]; then echo "🟢"; elif [ "$IDEAS_DAY" -ge 1 ]; then echo "🟡"; else echo "🔴"; fi) | — |
| 📦 Backlog pending | $PENDING | <50 | $(if [ "$PENDING" -lt 50 ]; then echo "🟢"; elif [ "$PENDING" -lt 75 ]; then echo "🟡"; else echo "🔴"; fi) | — |
| 🗳️ Em votação | $FORUM | 1-5 | $(if [ "$FORUM" -ge 1 ] && [ "$FORUM" -le 5 ]; then echo "🟢"; elif [ "$FORUM" -eq 0 ]; then echo "🟡"; else echo "🟠"; fi) | — |
| 📈 Ideias/semana | $IDEAS_WEEK | 10-15 | $(if [ "$IDEAS_WEEK" -ge 10 ]; then echo "🟢"; elif [ "$IDEAS_WEEK" -ge 5 ]; then echo "🟡"; else echo "🔴"; fi) | — |
| ✅ Validadas (total) | $VALIDATED | — | 🟢 | — |

---

## 🎯 Alinhamento Estratégico

### Tema da Semana: $THEME

| Indicador | Valor | Status |
|-----------|-------|--------|
| **Alinhamento ao tema** | ${ALIGNMENT}% | $(if [ "$ALIGNMENT" -ge 70 ]; then echo "🟢 Forte"; elif [ "$ALIGNMENT" -ge 40 ]; then echo "🟡 Moderado"; else echo "🔴 Fraco"; fi) |
| **Briefing efetividade** | $(if [ "$IDEAS_WEEK" -gt 0 ]; then echo "✅ Sim"; else echo "⏳ Ainda sem dados"; fi) | — |

### Distribuição por Categoria

| Categoria | Quantidade | % do Total | Status |
|-----------|------------|------------|--------|
| 🤖 AI Code Generation | $CODE_GEN | $(if [ "$TOTAL_PIPELINE" -gt 0 ]; then echo $((CODE_GEN * 100 / TOTAL_PIPELINE)); else echo "0"; fi)% | 🎯 Prioridade |
| 🚀 AI DevOps | $DEVOPS | $(if [ "$TOTAL_PIPELINE" -gt 0 ]; then echo $((DEVOPS * 100 / TOTAL_PIPELINE)); else echo "0"; fi)% | 🎯 Prioridade |
| 🧪 AI Testing | $TESTING | $(if [ "$TOTAL_PIPELINE" -gt 0 ]; then echo $((TESTING * 100 / TOTAL_PIPELINE)); else echo "0"; fi)% | 🎯 Prioridade |
| 📚 AI Documentation | $DOCS | $(if [ "$TOTAL_PIPELINE" -gt 0 ]; then echo $((DOCS * 100 / TOTAL_PIPELINE)); else echo "0"; fi)% | 🎯 Prioridade |
| 🐛 AI Debugging | $DEBUG | $(if [ "$TOTAL_PIPELINE" -gt 0 ]; then echo $((DEBUG * 100 / TOTAL_PIPELINE)); else echo "0"; fi)% | 🎯 Prioridade |

---

## 🚨 Alertas Estratégicos

$(if [ "$IDEAS_DAY" -lt 2 ]; then
    echo "### 🔴 CRÍTICO: Pipeline subnutrido"
    echo "- Ideias/dia abaixo do target (2-3)"
    echo "- **Ação:** Ativar scouts imediatamente"
    echo "- **Responsável:** Scout Lead"
fi)

$(if [ "$ALIGNMENT" -lt 40 ] && [ "$IDEAS_WEEK" -gt 0 ]; then
    echo "### 🟡 ATENÇÃO: Desalinhamento estratégico"
    echo "- Menos de 40% das ideias alinham com o tema $THEME"
    echo "- **Ação:** Rever briefing com scouts"
    echo "- **Possível causa:** Tema muito específico ou scouts a procurar fora do scope"
fi)

$(if [ "$CODE_GEN" -eq 0 ] && [ "$DEVOPS" -eq 0 ] && [ "$TESTING" -eq 0 ]; then
    echo "### 🟡 ATENÇÃO: Nenhuma ideia nas categorias prioritárias"
    echo "- Zero oportunidades nas 5 categorias de AI Developer Tools"
    echo "- **Ação:** Reforçar briefing com exemplos específicos"
fi)

$(if [ "$FORUM" -eq 0 ] && [ "$PENDING" -ge 3 ]; then
    echo "### 🟡 ATENÇÃO: Gargalo no fórum"
    echo "- $PENDING ideias pendentes mas nenhuma em votação"
    echo "- **Ação:** Convocar fórum de votação"
fi)

$(if [ "$IDEAS_DAY" -ge 3 ]; then
    echo "### 🟢 POSITIVO: Meta diária atingida"
    echo "- $IDEAS_DAY ideias/dia (target: 2-3)"
    echo "- **Nota:** Scouts a funcionar bem"
fi)

---

## 💡 Recomendações Estratégicas

### Para Esta Semana ($THEME_WEEK)

$(if [ "$IDEAS_DAY" -lt 2 ]; then
    echo "1. **Urgente:** Ativar scout manual ProductHunt hoje"
    echo "2. **Urgente:** Verificar se scouts automatizados estão a correr"
    echo "3. **Médio:** Enviar lembrete aos scouts com exemplos de AI Code Gen"
else
    echo "1. **Manter:** Ritmo atual de scouting"
    echo "2. **Foco:** Garantir que ideias são de qualidade (score ≥60)"
    echo "3. **Atenção:** Mover ideias rapidamente para fórum"
fi)

### Próximo Tema (Semana $((WEEK + 1)))

$(if [ "$ALIGNMENT" -ge 70 ]; then
    echo "- Considerar continuar tema '$THEME' (alto alinhamento)"
else
    echo "- Avaliar mudar tema (baixo alinhamento atual)"
    echo "- Sugestões: 'Local-First SaaS' ou 'Privacy Tools'"
fi)

---

## 📊 Trend Analysis

| Indicador | Esta Semana | Semana Anterior | Variação |
|-----------|-------------|-----------------|----------|
| Ideias/semana | $IDEAS_WEEK | — | — |
| Alinhamento tema | ${ALIGNMENT}% | — | — |
| Projetos validados | $VALIDATED | — | — |

---

## 🎯 Input Henry (Análise Estratégica)

$(if [ "$IDEAS_DAY" -lt 1 ]; then
    echo "**Diagnóstico:** Pipeline vazio é risco operacional. Scouts automatizados recém-ativados (ProductHunt, GitHub) devem começar a gerar oportunidades nas próximas 24h. Se em 48h não houver melhoria, escalar para scouts manuais imediatos."
elif [ "$ALIGNMENT" -lt 40 ]; then
    echo "**Diagnóstico:** Desalinhamento entre briefing e execução. Possíveis causas: (1) Tema 'AI Developer Tools' muito específico, (2) Scouts não compreenderam categorias, (3) Oportunidades existem mas não estão a ser identificadas. Recomendo: review de briefing com exemplos concretos."
else
    echo "**Diagnóstico:** Pipeline saudável. Alinhamento estratégico forte. Foco deve ser em manter ritmo e acelerar validação (fóruns)."
fi)

---

**Próximo update:** 15 minutos  
**Gerado por:** Pipeline Manager  
**Algoritmo:** v1.0-estratégico
EOF

echo "[$TIMESTAMP] Strategic dashboard generated" >> "$WORKSPACE/logs/metrics.log"
