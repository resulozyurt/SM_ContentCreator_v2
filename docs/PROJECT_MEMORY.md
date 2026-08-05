# PROJECT MEMORY — SM Content Creator v2

> **Purpose of this file.** This is the living handoff log. When a new chat
> starts, read this file top to bottom to know exactly what the system is, what
> has been decided, what is built, and what comes next — without losing context.
> **Every stage must update this file** (status table + changelog + next steps).

_Last updated: 2026-08-05 — end of Phase 1 (database layer)._

---

## 1. What we are building

A social media content generation system for two brands:

- **FieldPie** — Global / US, **American English** outputs.
- **Evatro** — Turkey, **Turkish** outputs.

Goal: automate ~70–80% of the chain into reviewable drafts —
trend research → monthly content calendar → headline + description → branded image.
**Human-in-the-loop: a human approves at every critical stage.** Not a fully
autonomous publisher (brand risk across two languages/identities).

Pipeline & human checkpoints:

```
Trend input (RSS / Google Trends / industry & competitor RSS)
  -> Monthly calendar draft            [HUMAN APPROVAL #1]
  -> Headline + description variants   [HUMAN SELECT   #2]
  -> Branded image draft -> Drive review folder  [HUMAN APPROVAL #3]
  -> Final composition in Canva (manual) + scheduling
```

Single source of truth: the pipeline table in Postgres
(`brand, solution, date, status, headline, description, image_url`).
The admin panel is a view over that table.

Solution areas: merchandising, field_audit, field_sales, home_service, ai, general.
(Evatro focuses mainly on merchandising, audit, AI.)

---

## 2. Given decisions (fixed)

- **Live env:** Railway.
- **No external automation platform** (no n8n / Zapier / Make). Own code only.
- **Backend:** Python + FastAPI.
- **DB:** Railway Postgres. SQLAlchemy + Alembic for models/migrations.
- **Text gen:** Claude API.
- **Image gen:** primary Gemini `gemini-3-pro-image` ("Nano Banana Pro");
  fallback OpenAI `gpt-image`. Model names live in config, not hardcoded.
- **Canva:** intentionally manual (API needs Enterprise; we have Pro). System
  makes the image step "~80% done", does not automate Canva.
- **Model-agnostic:** every provider behind one interface; swap = one file.
- **Secrets:** only in `.env` / Railway env vars; never in repo/code/logs.
- **No social scraping** (ToS risk). Legitimate trend sources only.
- **Cost-conscious:** ask before adding any paid third-party service.

### Decisions made in-chat (answers to open questions)

- **Storage → Google Drive API** (user has the account). Generated images land
  in a Drive "review" folder. `GOOGLE_DRIVE_REVIEW_FOLDER_ID` in env.
- **Admin auth → HTTP basic auth** (single user, `ADMIN_USERNAME` /
  `ADMIN_PASSWORD`). Approved as the simplest functional option.

### Working conventions (user-requested)

- **All development is in native American English** — code, comments, docs,
  commit messages. **Only Evatro content outputs are Turkish**; FieldPie content
  outputs are English. (Chat conversation with the user stays Turkish.)
- **A ready-to-use commit is provided at the end of each stage.** The user
  pushes to GitHub: `https://github.com/resulozyurt/SM_ContentCreator_v2.git`.
- **This memory file is updated every stage** so any new chat can resume cleanly.

---

## 3. Tech stack summary

FastAPI (backend) · Railway Postgres + SQLAlchemy/Alembic (data) · Claude (text) ·
Gemini `gemini-3-pro-image` + OpenAI `gpt-image` fallback (image) ·
Google Drive API (storage) · FastAPI+Jinja2+HTMX basic-auth (admin) ·
Railway Cron (scheduling) · Railway (deploy) · Canva manual.

---

## 4. Roadmap & status

Crawl (infra) → Walk (end-to-end drafting) → Run (live + automation).

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Repo skeleton, structure, `.env.example`, README, config, boot | ✅ DONE |
| 1 | DB models + Alembic migrations (pipeline/status table) | ✅ DONE |
| 2 | Model-agnostic AI provider layer (Claude / Gemini / OpenAI) | ⬜ next |
| 3 | Copy service: headline + description variants (brand-aware) | ⬜ |
| 4 | Image service: branded image + write to Drive review folder | ⬜ |
| 5 | Trend ingestion + monthly calendar draft + cron | ⬜ |
| 6 | Admin panel: 3 approval checkpoints (basic auth) | ⬜ |
| 7 | Railway deploy: services, cron, secrets, Drive wired, live | ⬜ |
| 8 | Hardening: error handling, retry/fallback, tests, docs | ⬜ |

**Definition of Done (per module):** code runs + deploys on Railway +
`.env.example`/README current + migrations present + human checkpoints functional
+ secrets external + basic error handling.

---

## 4a. Pipeline status state machine (Phase 1)

Lives on `calendar_slots.status` (the content item is the source of truth):

```
draft -> calendar_approved -> copy_selected -> image_review -> approved -> published
                       \___________ rejected (from any checkpoint) ___________/
```

- `draft` → seeded from a trend or added manually; awaiting calendar approval.
- `calendar_approved` → HUMAN CHECKPOINT #1 passed; ready for copy generation.
- `copy_selected` → HUMAN CHECKPOINT #2 passed; a `copy_variant.is_selected` is set.
- `image_review` → image generated, sitting in the Drive review folder.
- `approved` → HUMAN CHECKPOINT #3 passed; ready for manual Canva + publish.
- `published` → posted (recorded manually). `rejected` → dropped.

Assets have their own `AssetStatus`: review → approved → rejected.

## 5. What exists right now (end of Phase 1)

```
app/
  __init__.py            version
  main.py                FastAPI app + GET /health (working)
  config.py              pydantic-settings; env + model ids
  brands/
    __init__.py
    profiles.py          BrandProfile dataclass + YAML loader (working)
    fieldpie.yaml        FieldPie identity (teal/slate, en-US, 6 solutions)
    evatro.yaml          Evatro identity (red/navy, tr-TR, merch/audit/ai)
  providers/
    __init__.py
    base.py              TextProvider / ImageProvider ABCs (contracts only)
  services/__init__.py   stage map (stubs, implemented phases 3–5)
  db/
    __init__.py
    base.py              Base + enums (Brand, Solution, PipelineStatus, AssetStatus)
    models.py            Trend, CalendarSlot, CopyVariant, Asset
    session.py           lazy engine + session_scope() (psycopg v3)
    migrations/          Alembic (env.py, script.py.mako, versions/)
      versions/f821b6f74a13_initial_pipeline_schema.py
  admin/__init__.py      stub (phase 6)
  jobs/__init__.py       stub (phase 5/7)
config/trend_sources.yaml  structure only (phase 5)
assets/reference/README.md brand asset layout
alembic.ini
.env.example · .gitignore · requirements.txt · Procfile · railway.json · runtime.txt
README.md · docs/PROJECT_MEMORY.md
```

Verified:
- Phase 0: FastAPI app imports and `/health` responds `{status: ok}`.
- Phase 1: models import; migration renders correct **Postgres** DDL offline
  (`alembic upgrade head --sql`) — each enum type created exactly once (the
  shared-enum duplicate-CREATE-TYPE trap is handled by hand-editing the
  migration to create enums explicitly with checkfirst); downgrade drops tables
  then types cleanly. Real Postgres run happens on Railway in Phase 7
  (couldn't install a local Postgres in the sandbox — no root).

---

## 6. Next step

**Phase 2 — Model-agnostic AI provider layer.** Implement concrete providers
behind the interfaces in `app/providers/base.py`:
- `claude.py` — TextProvider (Anthropic API), model from `CLAUDE_TEXT_MODEL`.
- `gemini.py` — ImageProvider (Gemini `gemini-3-pro-image`), primary.
- `openai_image.py` — ImageProvider (OpenAI `gpt-image`), fallback.
- a small factory that returns the configured provider, so swapping a model =
  one config change. Add deps: `anthropic`, `google-genai`, `openai`.
Wait for user approval before starting (step-by-step approval rule).

Reminder: run `alembic upgrade head` against Railway Postgres during Phase 7.

---

## 7. Changelog

- **2026-08-05 — Phase 1.** Database layer: `db/base.py` (Base + 4 enums),
  `db/models.py` (Trend, CalendarSlot, CopyVariant, Asset), lazy `db/session.py`,
  Alembic (`alembic.ini`, `env.py` reading DATABASE_URL from settings,
  `script.py.mako`, initial migration `f821b6f74a13`). Status state machine
  defined on `calendar_slots.status`. Fixed the shared-enum duplicate CREATE TYPE
  by hand-editing the migration. Verified Postgres DDL renders correctly offline.
  Added SQLAlchemy/alembic/psycopg to requirements.
- **2026-08-05 — Phase 0.** Repo skeleton created: package layout, `config.py`,
  FastAPI boot + `/health`, brand YAML profiles, provider interfaces, `.env.example`,
  `.gitignore`, `requirements.txt`, `Procfile`, `railway.json`, README, this file.
  Decisions locked: Google Drive storage, basic-auth admin, English-only dev,
  per-stage commits, memory-file handoff.
