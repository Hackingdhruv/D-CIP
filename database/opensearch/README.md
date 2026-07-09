# OpenSearch

Optional full-text search, gated end-to-end by `OPENSEARCH_ENABLED`
(default `false`) — every call no-ops gracefully when disabled or
unreachable. The single index (`dcip_evidence`) and its mapping are defined
in code (`apps/api/app/services/opensearch_service.py`), not applied from
files on disk. Connection settings come from the environment
(`OPENSEARCH_HOST`, `OPENSEARCH_PORT`, credentials). For local development
the compose service runs single-node with the security plugin disabled, so
the client connects over plain HTTP. Excluded from the default `core`
Docker Compose profile — see the `full` profile to run it.
