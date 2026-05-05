# Cron Jobs - Configuração Limpa (Pós-Hexalabs)

**Data:** 2026-05-05  
**Estado:** Arranque do zero após remoção de jobs #sistema (hexalabs)

## Jobs Ativos

| Job ID | Nome | Frequência | Destino | Skills | Estado |
|--------|------|------------|---------|--------|--------|
| 6d4550e75f6e | Inbox Digest | 60m | telegram | google-workspace, email-organization | ✅ Ativo |
| 8a10df73a371 | Outlook RAG Importer | 30m | discord:1474791029285847267 | outlook-browser-automation | ✅ Ativo |
| yt_transcript_maximizer | YouTube Transcript Maximizer | 60m | discord:1474789361781309582 | shell | ✅ Ativo |
| cd7dce4f7a23 | YouTube Channel Metrics Tracker | 30m | discord:1474789361781309582 | - | ✅ Ativo |
| e1f4acf9da0d | daily-news-extraction | 360m | discord:1474789361781309582 | - | ✅ Ativo |
| 2c8e7be4c370 | YouTube Video Dashboard Generator | 360m | discord:1474789361781309582 | - | ✅ Ativo |
| 57fe331360fb | 🌍 GeoRisk Dashboard v2 | 360m | discord:1474789361781309582 | date-time-calculation | ✅ Ativo |
| 736c86856dde | 📰 #daily-news v5 | 180m | discord:1474789361781309582 | - | ✅ Ativo |
| 2f09c0cc2db8 | 🧠 Auto-Research Engine v2 | 720m | discord:1474789361781309582 | - | ✅ Ativo |
| 54d5cdceaaff | dev-agent-orchestration-hub | 60m | discord:1486678863877505064 | - | ✅ Ativo |
| 2a4d7c310e5a | factory-health-check | 15m | discord:1474791029285847267 | - | ✅ Ativo |
| 44f512059a48 | dev-deepverify-enterprise-api | 60m | discord:1486678863877505064 | - | ✅ Ativo |
| d21902506624 | dev-kyc-network | 1440m | discord:1486678863877505064 | - | ✅ Ativo |
| 16a132eb5a5b | Token Usage - Project Monitor | 360m | discord:1474791029285847267 | - | ✅ Ativo |
| 69a13177ad16 | YouTube Unified Pipeline | 60m | discord:1474789361781309582 | - | ✅ Ativo |
| e0390e031316 | Synthetic.new Quota Monitor | 30m | local | - | ✅ Ativo |
| e7986358b1d0 | Hermes Config Backup | 30m | origin | - | ✅ Ativo |

## Jobs Removidos (Limpeza)

| Job ID | Nome | Razão |
|--------|------|------|
| b543d5a1a05c | Limpar Inbox - Gmail + Outlook | Canal #sistema eliminado |
| 7c84992164b8 | Filtrar Action Required - Gmail + Outlook | Canal #sistema eliminado |
| 40ac96951ba5 | Weekly Deep Dive | Canal #sistema eliminado |
| 6b455b33933f | Outlook RAG Importer 24h | Canal #sistema eliminado |
| 5943682761ff | dev-model-router-saas | Pausado (Quality Gates) |
| 31e39b52fbfb | dev-edge-ai-compiler | Pausado (Quality Gates) |
| 4f308893c96a | dev-ai-observability-platform | Pausado (Quality Gates) |
| 24c4671c8a6f | dev-smb-ai-adoption-platform | Pausado (Quality Gates) |
| 133559891500 | dev-ai-supply-chain-shield | Pausado (Quality Gates) |
| e54982391324 | dev-agent-testing-qa | Pausado (Quality Gates) |
| 543da9820430 | dev-edge-inference-network | Pausado (Quality Gates) |
| 5701dee16f7e | dev-agent-governance-firewall | Pausado (Quality Gates) |
| 528b2cf44fd6 | Software Factory Autopilot | Pausado (Quality Gates) |

## Configuração de Monitorização

### Circuit Breaker
- **Ativo:** Sim (automático)
- **Trigger:** 3 falhas consecutivas
- **Ação:** Pausar job automaticamente
- **Notificação:** Telegram Home

### Modelo Padrão
- **Model:** z-ai/glm-4.5-air:free
- **Provider:** openrouter
- **Template:** Ver skill `cron-job-template`

## Canais de Entrega

| Canal Discord | ID | Propósito |
|--------------|-----|-----------|
| #personal | 1473322596102701078 | Discord Home |
| #daily-news | 1474789361781309582 | Notícias YouTube |
| #system-health | 1474791029285847267 | Saúde do sistema |
| #software-factory | 1486678863877505064 | Software Factory |

| Plataforma | Destino |
|-----------|---------|
| Telegram | 1753732062 (Home - Prioridade 1) |
| Local | ~/.hermes/cron/output/ |
| Origin | Canal atual |

## Próximos Passos

1. ✅ Jobs #sistema removidos
2. ✅ Limpeza de jobs pausados antigos
3. ✅ Novos jobs criados (Inbox Digest, Outlook RAG)
4. ⏳ Monitorizar execução dos novos jobs
5. ⏳ Ajustar frequências se necessário
6. ⏳ Configurar alertas de quota (Synthetic.new)

---
*Autonomous cleanup completed: 2026-05-05 19:50 UTC*
