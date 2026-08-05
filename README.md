# SM Content Creator v2

Social media content generation system for **FieldPie** (Global / US, English) and
**Evatro** (Turkey, Turkish). It automates ~70–80% of the production chain into
reviewable drafts, with a **human approval checkpoint at every critical stage** —
this is a human-in-the-loop system, not a fully autonomous publisher.

## Pipeline

```
Trend input (RSS / Google Trends)
   -> Monthly calendar draft          [HUMAN APPROVAL #1]
   -> Headline + description variants  [HUMAN SELECT   #2]
   -> Branded image draft (to Drive review folder)  [HUMAN APPROVAL #3]
   -> Final composition in Canva (manual) + schedule
```

The single source of truth is the pipeline table in Postgres
(`brand, solution, date, status, headline, description, image_url`). The admin
panel is a view over that table.

## Tech stack

| Concern            | Choice                                                     |
|--------------------|------------------------------------------------------------|
| Backend            | Python + FastAPI                                            |
| Database           | Railway Postgres (SQLAlchemy + Alembic)                     |
| Text generation    | Claude API                                                  |
| Image generation   | Gemini `gemini-3-pro-image` (primary), OpenAI `gpt-image` (fallback) |
| Storage            | Google Drive API (review folder for generated images)      |
| Admin panel        | FastAPI + Jinja2 + HTMX, HTTP basic auth                   |
| Scheduling         | Railway Cron                                                |
| Deploy             | Railway                                                     |
| Canva              | Intentionally manual (API needs Enterprise)                |

No external automation platform (no n8n / Zapier / Make) — everything is our own code.

## Conventions

- **Language:** all code, comments, docs and commits are in American English.
  Only *Evatro content outputs* are Turkish; *FieldPie content outputs* are English.
- **Brand isolation:** a brand's profile/language must never leak into the other.
- **Secrets:** only in `.env` / Railway env vars. Never in code, repo, or logs.
- **Model-agnostic:** model names live in config (`.env`), not hardcoded.

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # then fill in values
uvicorn app.main:app --reload
# check: http://localhost:8000/health
```

## Project layout

```
app/
  main.py        FastAPI entry + health check
  config.py      env-driven settings (incl. model ids)
  brands/        brand profiles (fieldpie.yaml, evatro.yaml) + loader
  providers/     model-agnostic AI layer (Phase 2)
  services/      pipeline stages (ingestion, calendar, copy, image)
  db/            models, session, migrations (Phase 1)
  admin/         approval panel (Phase 6)
  jobs/          cron entry points (Phase 5/7)
config/          trend source config
assets/reference/ brand reference images & logos
docs/PROJECT_MEMORY.md   living handoff log — read this to resume work
```

## Roadmap

See `docs/PROJECT_MEMORY.md` for the phased roadmap and current status.
