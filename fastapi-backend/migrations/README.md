P01 starts a new Alembic history for the FastAPI backend.

The initial revision is for an empty PostgreSQL database. It must not be run
against the existing production schema. Production adoption requires a schema
comparison and an explicitly approved Alembic baseline/stamp during P07.
