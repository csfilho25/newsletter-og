# O&G + Mining Intelligence Brief

Newsletter diaria de inteligencia setorial em **Oil & Gas, Energia Eletrica e Mineracao** no Brasil. Curadoria focada em headhunters e profissionais de executive search.

## Portal

**[https://csfilho25.github.io/newsletter-og/](https://csfilho25.github.io/newsletter-og/)**

## Funcionalidades

- **Portal web** com edicao mais recente e arquivo de edicoes anteriores
- **Audio player** — ouca a newsletter no navegador (Web Speech API, pt-BR)
- **Mobile-first** — design responsivo otimizado para celular
- **Automacao diaria** — nova edicao seg-sex as 8h (Brasilia)
- **Email** — edicao completa entregue por email com link para versao web

## Estrutura

```
index.html              Portal/landing page
css/                    Estilos separados (theme, edition, portal, audio-player)
js/                     Audio player e logica do portal
editions/               Arquivo de edicoes (1 HTML por dia util)
editions/index.json     Manifesto com metadata de todas edicoes
templates/              Templates para geracao automatica
PROMPT.md               Prompt master para geracao de conteudo
```

## Secoes da Newsletter

1. Resumo Executivo
2. Key Numbers (8 indicadores)
3. Geopolitica & Petroleo
4. Petrobras & Upstream Brasil
5. Energia Eletrica
6. Radar de Leiloes & Eventos
7. Mineracao & Minerais Criticos
8. Analise Estrategica — Visao Headhunter
9. Market Pulse
10. Dados-Chave

## Tech Stack

- HTML/CSS/JS puro (sem frameworks)
- GitHub Pages (hospedagem)
- Web Speech API (audio text-to-speech)
- Claude AI (geracao de conteudo)
- Claude Code Scheduled Tasks (automacao)

---

*Powered by Claude AI — Dados publicos — Nao constitui recomendacao de investimento*
