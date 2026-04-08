# Health Trend Crawler - Guia de Deploy na VPS

## O que este sistema faz

Roda 2x por dia (8h e 18h EST) na sua VPS e:
1. Crawla 28 sites americanos (20 gossip + 8 saude) via Google News RSS
2. Filtra por keywords de 5 nichos: Memory, Joint Pain, Neuropathy, Weight Loss, Type 2 Diabetes
3. Usa o Claude Code CLI pra analisar tendencias e gerar angulos de copy
4. Gera um dashboard HTML bonito, acessivel de qualquer lugar via browser

---

## Passo 1: Copiar para a VPS

\`\`\`bash
# Opcao A: scp do seu PC
scp -r health-trend-crawler/ user@sua-vps:~/

# Opcao B: git clone (se subiu pra um repo)
git clone seu-repo ~/health-trend-crawler

# Entrar na pasta
cd ~/health-trend-crawler
\`\`\`

## Passo 2: Rodar o Setup

\`\`\`bash
chmod +x setup.sh run.sh
./setup.sh
\`\`\`

O setup vai:
- Criar virtual environment Python
- Instalar dependencias (feedparser, requests, beautifulsoup4, jinja2)
- Verificar se o Claude Code CLI esta no PATH
- Instalar e configurar o Caddy (web server)
- Pedir uma senha para proteger o dashboard
- Configurar os cron jobs (8h e 18h EST)

## Passo 3: Teste Rapido

\`\`\`bash
source venv/bin/activate
python main.py --test
\`\`\`

Roda com escopo reduzido (1 nicho, 3 artigos). Se funcionar, o dashboard ja tera dados em http://SEU_IP

## Passo 4: Acessar o Dashboard

Abra no browser: http://SEU_IP_DA_VPS
- Usuario: gilberto
- Senha: a que voce definiu no setup

## Passo 5: Pipeline Completo

\`\`\`bash
python main.py
\`\`\`

---

## Comandos Uteis

\`\`\`bash
# Pipeline completo
python main.py

# So crawl (sem analise)
python main.py --crawl-only

# Analisar crawl anterior
python main.py --analyze data/raw/crawl_20260407_0800.json

# Regenerar dashboard dos dados existentes
python main.py --dashboard-only

# Teste rapido
python main.py --test

# Ver logs
tail -f data/logs/main.log

# Ver cron
crontab -l

# Reiniciar web server
sudo systemctl restart caddy
\`\`\`

## Ajustar Horarios do Cron

Se sua VPS esta em UTC (padrao):
- 12:00 UTC = 08:00 EST
- 22:00 UTC = 18:00 EST

\`\`\`bash
crontab -e
\`\`\`

## Consumo de Recursos

- ~6 chamadas ao Claude por execucao (~20k-30k tokens)
- 2x por dia = ~40k-60k tokens/dia
- Confortavel no plano Max
- Dados auto-limpam apos 30 dias
