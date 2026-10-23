<!--
File: migrations/README.md
Purpose: Database migrations.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->
# Database migrations

Alembic migrations are reviewed and committed source files. Set `DATABASE_URL`
in `.env`, then run migration commands from the repository root.

Do not apply a new migration to persistent data until its SQL has passed the
corresponding review stop. Generate offline SQL with:

```bash
alembic upgrade head --sql
```
