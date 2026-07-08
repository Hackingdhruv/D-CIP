# PostgreSQL

System of record for D-CIP. Scripts in `init/` run once when the data volume is
first created (via the official image's `docker-entrypoint-initdb.d` hook) and
only set up extensions — never tables. All schema is managed by Alembic
migrations in `apps/api/alembic`.
