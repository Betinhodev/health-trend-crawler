# PRD - Health Trend Crawler
## Sistema de Monitoramento de Tendencias de Saude para Copywriters

---

## 1. Visao Geral

Sistema automatizado que roda 2x/dia numa VPS, crawla 28 sites americanos (gossip + saude), filtra por keywords de 5 nichos de saude, analisa com Claude Code CLI, e gera um dashboard HTML acessivel de qualquer lugar via browser.

**Owner:** Gilberto (Copywriter - Direct Response Health)
**Stack:** Python + Claude Code CLI + Jinja2 + Caddy (web server) + Cron
**Infra:** VPS com Claude Code (plano Max)

---

## 2. Problema

Copywriters de direct response precisam acompanhar diariamente tendencias de consumo nos EUA para criar angulos de copy relevantes. Hoje isso e feito manualmente, visitando dezenas de sites, o que consome horas e gera perda de oportunidades.

## 3. Solucao

Um agente automatizado que:
1. Coleta noticias relevantes 2x/dia
2. Analisa com IA gerando angulos de copy prontos
3. Apresenta tudo num dashboard web limpo e acessivel

---

## 4. Nichos Monitorados

| Nicho | Keywords Principais |
|-------|-------------------|
| Memory | memory loss, alzheimer, dementia, brain fog, cognitive decline |
| Joint Pain | joint pain, chronic pain, pain relief, arthritis, fibromyalgia |
| Neuropathy | neuropathy, nerve pain, nerve damage, tingling, numbness |
| Weight Loss | weight loss, ozempic, monjaro, metabolism, GLP-1, semaglutide |
| Type 2 Diabetes | type 2 diabetes, blood sugar, metformin, insulin, A1C |

## 5. Sites Monitorados (28 total)

### 5.1 Gossip/Celebrity (20 sites)
TMZ, Page Six, Perez Hilton, Radar Online, The Blast, Hollywood Life,
Just Jared, US Weekly, In Touch Weekly, Lainey Gossip, OK Magazine,
Dlisted, Blind Gossip, Naughty Gossip, Bossip, Celebuzz, MediaTakeOut,
Gawker, Crazy Days and Nights, Star Magazine

### 5.2 Saude/Ciencia (8 sites)
Healthline, WebMD, CNN Health, NBC Health, ScienceDaily,
Medical News Today, Mayo Clinic News, NIH News

---

## 6. Arquitetura Tecnica

\`\`\`
CRON (2x/dia)
    |
    v
[run.sh] --- Ativa venv, dispara pipeline
    |
    v
[crawler.py] --- Google News RSS + scraping direto
    |               - Busca por site + keyword
    |               - Extrai conteudo dos top artigos
    |               - Salva JSON em data/raw/
    v
[analyzer.py] --- Claude Code CLI
    |               - Analisa cada nicho separadamente
    |               - Gera trending topics, angulos de copy
    |               - Identifica celebridades, estudos, produtos
    |               - Gera resumo diario cross-nicho
    |               - Salva JSON em data/reports/
    v
[dashboard.py] --- Jinja2 Templates
    |               - Le reports JSON
    |               - Gera HTML estatico
    |               - Copia para /var/www/dashboard/
    v
[Caddy Web Server] --- Serve HTML na porta 443/80
                        - HTTPS automatico (opcional)
                        - Acesso via IP ou dominio
                        - Protecao por senha (Basic Auth)
\`\`\`

## 7. Dashboard - Telas e Funcionalidades

### 7.1 Pagina Principal (index.html)
- Data e horario da ultima atualizacao
- Briefing diario (resumo executivo em 3-4 frases)
- "Nicho mais quente hoje" em destaque
- Top 5 angulos acionaveis (com badge de urgencia)
- Tendencias cross-nicho
- Cards de cada nicho com preview (clicavel)

### 7.2 Pagina por Nicho (niche_*.html)
- Todos os trending topics do dia com score de relevancia
- Mencoes de celebridades (com contexto e potencial de copy)
- Novos estudos/descobertas (com angulo de headline)
- Tendencias de produto (subindo/descendo/estavel)
- Top 3 angulos de copy (tipo, headline exemplo, emocao-alvo)
- Lista completa de artigos coletados (titulo, fonte, link)

### 7.3 Historico (/history/)
- Lista de relatorios anteriores por data
- Cada data clicavel abre o relatorio daquele dia
- Ultimos 30 dias mantidos

### 7.4 Design
- Dark mode (padrao) com toggle para light
- Responsivo (funciona no celular)
- Cores por urgencia: vermelho (high), amarelo (medium), verde (low)
- Cards com hover effect
- Font moderna (Inter)
- Badges coloridos por tipo de angulo (fear/desire/curiosity/authority)
- Sem framework CSS externo (CSS puro, leve e rapido)

---

## 8. Consumo de Recursos

| Recurso | Por execucao | Por dia (2x) |
|---------|-------------|-------------|
| Tokens Claude | ~15k-25k | ~30k-50k |
| Tempo de execucao | ~5-10 min | ~10-20 min |
| Armazenamento | ~2-5 MB | ~4-10 MB |
| Requests HTTP | ~100-200 | ~200-400 |

**Plano Max:** Muito confortavel para esse volume.
**Cleanup automatico:** Dados com mais de 30 dias sao removidos.

---

## 9. Proximas Fases (Futuro)

### Fase 2 - Ad Spy Monitor
- Monitorar Meta Ads Library com keywords do PDF
- Combinacoes nicho + palavra de mercado

### Fase 3 - Alertas
- Notificacao por Telegram/email quando surgir trend de alta urgencia

### Fase 4 - Base de Conhecimento
- Armazenar historico de trends num banco (SQLite)
- Busca por keyword/data/nicho
- Graficos de tendencia ao longo do tempo
