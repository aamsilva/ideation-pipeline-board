# Score de Projetos em Execução — Gestão Diária 24/7

## 🎯 Objetivo
Sistema dinâmico de priorização de projetos ativos para otimizar alocação de recursos 24/7.

---

## 📊 Critérios de Score (Projetos em Execução)

### 1. Progresso vs Timeline (25%)
| Status | Score |
|--------|-------|
| Ahead (>110%) | 100 |
| On track (90-110%) | 80 |
| Slight delay (70-89%) | 60 |
| Delayed (<70%) | 40 |
| Blocked | 20 |

### 2. Impacto Potencial (20%)
| Impacto | Score |
|---------|-------|
| Transformacional (€10M+) | 100 |
| Significativo (€1-10M) | 80 |
| Moderado (€100K-1M) | 60 |
| Pequeno (<€100K) | 40 |

### 3. Risco Atual (20%)
| Risco | Score |
|-------|-------|
| Baixo | 100 |
| Médio | 70 |
| Alto | 40 |
| Crítico | 20 |

### 4. Resource Efficiency (20%)
| Eficiência | Score |
|------------|-------|
| Muito eficiente | 100 |
| Eficiente | 80 |
| Médio | 60 |
| Ineficiente | 40 |

### 5. Stakeholder Priority (15%)
| Prioridade | Score |
|------------|-------|
| Estratégico | 100 |
| Alto | 80 |
| Médio | 60 |
| Baixo | 40 |

---

## 🔄 Processo Diário (Automático)

### 06:00 — Daily Score Update
```
Para cada projeto ativo:
  1. Coletar métricas (progresso, riscos, blockers)
  2. Calcular score ponderado
  3. Atualizar ranking
  4. Identificar projetos em risco
```

### 12:00 — Midday Check
- Projetos com score <60: Alerta amarelo
- Projetos com score <40: Alerta vermelho

### 18:00 — Evening Review
- Ranking atualizado
- Recomendações de realocação
- Decisões de pause/continue

### 00:00 — Daily Report
- Score cards de todos os projetos
- Tendências (subindo/descendo)
- Previsões

---

## 📈 Matriz de Decisão

| Score | Prioridade | Ação |
|-------|------------|------|
| **≥80** | P0 — Crítico | Máximos recursos, acelerar |
| **60-79** | P1 — Alto | Manter recursos, monitorar |
| **40-59** | P2 — Médio | Reavaliar, possível pausa |
| **<40** | P3 — Baixo | Pausar ou arquivar |

---

## 🎯 Exemplos de Decisões

### Caso 1: Recursos Limitados
```
Projetos ativos:
- Projeto A: Score 85 (P0) → Continue
- Projeto B: Score 72 (P1) → Continue  
- Projeto C: Score 45 (P2) → Pausar
- Projeto D: Score 35 (P3) → Arquivar
```

### Caso 2: Novo Projeto Urgente
```
Novo projeto P0 chega:
- Score inicial: 90
- Ação: Alocar recursos de P3/P2
- Pausar projetos score <50
```

---

## 🤖 Automação Henry (24/7)

### Tarefas Diárias Automáticas:
1. **06:00:** Calcular scores
2. **12:00:** Alertas projetos em risco
3. **18:00:** Recomendações realocação
4. **00:00:** Report diário

### Tarefas Semanais:
- Análise tendências
- Previsões de completion
- Recomendações de priorização

### Alertas Imediatos:
- Projeto bloqueado >24h
- Score cai >20 pontos
- Delay >1 semana

---

## 📊 Dashboard

**Atualizado:** A cada 6 horas
**Acesso:** `reports/project-scores-daily.md`

| Projeto | Score | Prioridade | Trend | Ação |
|---------|-------|------------|-------|------|
| DeepVerify | 85 | P0 | ↑ | Acelerar |
| Agent Sandbox | 72 | P1 | → | Manter |
| Vibe Coding | 45 | P2 | ↓ | Reavaliar |

---

## 📝 Documentação

**Processo:** `docs/score-projetos-execucao.md`
**Reports:** `reports/project-scores-YYYY-MM-DD.md`
**Decisões:** `decisions/prioritization-YYYY-MM-DD.md`

---

*Criado: 2026-02-23 | Responsável: Henry (24/7)*
