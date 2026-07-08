# Neo4j

Relationship graph store. Connection settings come from the environment
(`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`). The `conf/` directory is mounted
into the container for optional overrides; it is intentionally empty so the
image defaults apply. The graph schema and constraints are created in a later
milestone.
