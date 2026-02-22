# 🤖 Scouts Automatizados

## Overview

Scouts automatizados que correm em background para encontrar oportunidades.

## Scouts Ativos

| Scout | Frequência | Source | Status |
|-------|------------|--------|--------|
| **ProductHunt** | 6h | ProductHunt AI category | 🟡 Configurado |
| **GitHub** | 6h | GitHub Trending repos | 🟡 Configurado |
| **Reddit** | 12h | r/SaaS, r/MachineLearning | 🔴 Pendente |
| **Twitter** | 6h | IndieHackers, SaaS | 🔴 Pendente |

## Configuração

### LaunchAgent (macOS)

```bash
# ProductHunt Scout
cat > ~/Library/LaunchAgents/com.hexalabs.scout-producthunt.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hexalabs.scout-producthunt</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/augustosilva/clawd/innovation-team/scouts/scout-producthunt.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>21600</integer>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.hexalabs.scout-producthunt.plist
```

## APIs Necessárias

- **ProductHunt:** API Key (https://www.producthunt.com/v2/oauth)
- **GitHub:** Personal Access Token
- **Reddit:** PRAW library
- **Twitter:** API v2

## Logs

```
~/clawd/innovation-team/logs/
├── scout-producthunt.log
├── scout-github.log
└── scout-reddit.log
```

## Manual Override

Para correr manualmente:

```bash
~/clawd/innovation-team/scouts/scout-producthunt.sh
```
