# FASE 2: Critérios Autónomos de Avanço

## FONTE DE DADOS
- **Task do Researcher**: hmn-researcher (task in_progress)
- **Output Esperado**: research_results_NMS.json

## CRITÉRIOS PARA AVANÇAR (AUTONOMOUS)

### 1. RESEARCHER TASK COMPLETION
- [ ] Task status = `completed`
- [ ] Output file existe e tem >1000 chars
- [ ] Contém: SNMP, NetConf, YANG, OTDR, ou FBG references

### 2. NMS INTEGRATION READINESS
Baseado nos resultados do researcher, avaliar:
- **Se SNMP detetado** → Criar tarefa para `hmn-coder`: "Implementar SNMP poller usando pysnmp"
- **Se NetConf/YANG detetado** → Criar tarefa para `hmn-coder`: "Implementar NetConf client usando ncclient"
- **Se OTDR/FBG mencionado** → Criar tarefa para `hmn-analyst`: "Processar dados de sondas óticas"

### 3. AGENT AVAILABILITY
- [ ] Pelo menos 6 agentes operacionais no swarm
- [ ] hmn-coder disponível para Fase 2
- [ ] hmn-analyst disponível para Fase 2

### 4. DECISÃO AUTÓNOMA (SEM INTERVENÇÃO HUMANA)

QUANDO os critérios 1-3 forem cumpridos:

**AÇÃO A**: Criar tarefas Fase 2 baseadas no output do researcher
```bash
# Exemplo (preencher baseado no research real)
npx ruflo@latest task create \
  --type implementation \
  --name "Fase2: Implementar NMS Integration" \
  --description "Baseado no research: [RESEARCH_SUMMARY]" \
  --swarm swarm-1778097400528-0g8vo4 \
  --assigned-agent hmn-coder \
  --non-interactive
```

**AÇÃO B**: Atualizar todo list
```bash
# Marcar Fase 1 como completa, Fase 2 como in_progress
```

**AÇÃO C**: Reportar via Discord
- Enviar resumo dos resultados do researcher
- Listar tarefas criadas para Fase 2
- Mostrar critérios cumpridos

## MONITORING LOOP

Enquanto researcher task IN_PROGRESS:
1. Poll task status a cada 60s
2. Se concluído → ler resultados → criar tarefas Fase 2
3. Se erro → spawnar novo researcher → retry

## FASE 2 TASK TEMPLATES (Preparados)

### Template A: SNMP Integration
```
Task: Implementar SNMP Polling para NMS
Agent: hmn-coder
Inputs: [SNMP OIDs from research], [MIB files identified]
Deliverables: 
  - snmp_poller.py
  - nms_integration_snmp.py
  - Unit tests
```

### Template B: NetConf/YANG Integration
```
Task: Implementar NetConf Client com YANG Models
Agent: hmn-coder
Inputs: [YANG models from research], [NetConf endpoints]
Deliverables:
  - netconf_client.py
  - yang_models/*.yang
  - Integration tests
```

### Template C: Optical Probe Data Processing
```
Task: Pipeline OTDR/FBG Data Processing
Agent: hmn-analyst + hmn-coder
Inputs: [Probe specs from research]
Deliverables:
  - otdr_parser.py
  - fbg_analyzer.py
  - Data validation tests
```

---
*Este documento guia a decisão autónoma. O Hermes Agent executará as ações A/B/C sem pedir confirmação humana.*