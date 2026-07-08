# OpenSearch

Full-text and (later) semantic search. Connection settings come from the
environment (`OPENSEARCH_HOST`, `OPENSEARCH_PORT`, credentials). For local
development the compose service runs single-node with the security plugin
disabled, so the client connects over plain HTTP.

`index-templates/` holds example mappings for reference only; nothing is applied
automatically in the foundation milestone.
