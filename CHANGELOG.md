# Changelog

All notable changes to D-CIP are documented in this file.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Version numbers follow [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-07-09

Initial public release.

### Added

- Case management with status workflow, tasks, notes, and per-case team assignment.
- Evidence intelligence engine: streamed upload with SHA-256 integrity, an async
  Celery pipeline (metadata → OCR → entity/keyword extraction → timeline →
  search indexing → optional AI summary), and an immutable chain-of-custody log.
- Entity extraction: regex-based IOCs plus optional spaCy NLP for people,
  organizations, and locations.
- Timeline reconstruction with gap/conflict/duplicate detection and a
  manual verification workflow.
- Evidence-scoped AI assistant with mandatory per-claim citation, running
  against OpenAI, any OpenAI-compatible endpoint, or a local Ollama model —
  or fully disabled, with the rest of the platform unaffected either way.
- Entity-relationship graph visualization (React Flow) computed from
  cross-evidence entity co-occurrence.
- Reporting engine: 9 report types across 6 templates, exported as PDF,
  DOCX, HTML, or JSON, with version history.
- Universal Ctrl+K search across cases, evidence, entities, notes, tasks,
  and timeline events.
- Watchlists and alerts across 16 IOC types with automatic matching and
  cross-case correlation.
- Role-based access control: 5 roles, granular `resource:action`
  permissions enforced server-side on every route.
- Enterprise administration: identity, session, audit, and system-health
  management.
- 428 backend tests (unit + integration).

### Known Limitations

See [`ARCHITECTURE.md`](ARCHITECTURE.md#12-known-discrepancies-docsmarketing-vs-code--trust-the-code)
for the full, honest list. Highlights:

- Neo4j is provisioned and health-checked but not yet load-bearing — the
  entity-relationship graph is computed from PostgreSQL, not a graph query.
- OpenSearch full-text search is optional and flag-gated (`OPENSEARCH_ENABLED`).
- AI grounding is enforced via prompt engineering, not a code-level
  verification step.
