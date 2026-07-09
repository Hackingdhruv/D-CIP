# Neo4j

Provisioned and health-checked, but not currently load-bearing — connectivity
is verified (`driver.verify_connectivity()`) in a few places, but the app
writes no Cypher queries against it. The relationship graph actually shown in
the UI is computed from PostgreSQL entity co-occurrence instead. See
[`ARCHITECTURE.md`](../../ARCHITECTURE.md) §7 for the full explanation.

Connection settings come from the environment (`NEO4J_URI`, `NEO4J_USER`,
`NEO4J_PASSWORD`). The `conf/` directory is mounted into the container for
optional overrides; it is intentionally empty so the image defaults apply.
Excluded from the default `core` Docker Compose profile — see the `full`
profile to run it.
