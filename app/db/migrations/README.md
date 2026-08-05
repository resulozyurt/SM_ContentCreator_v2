# Migrations

Alembic migrations for the pipeline schema.

```bash
# create the DB tables (run once, and after each new migration)
alembic upgrade head

# after changing models, generate a new migration
alembic revision --autogenerate -m "describe change"

# roll back one step
alembic downgrade -1
```

The database URL comes from the environment (`DATABASE_URL`), resolved in
`env.py` via app settings — it is never written into `alembic.ini`.
