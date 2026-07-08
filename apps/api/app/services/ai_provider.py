"""AI provider — OpenAI-compatible API client for text generation and embeddings.

Supports:
  - ``none``   — AI disabled; all calls return None silently
  - ``openai`` — OpenAI API (requires AI_API_KEY)
  - ``ollama`` — Local Ollama server (AI_API_BASE must point to Ollama)

All methods return None on error or when AI is disabled, so callers can treat
AI output as optional enrichment without failing the pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an AI assistant embedded in D-CIP, a Digital Criminal
Investigation Platform. You help investigators analyze evidence, not make investigative
decisions. Your role is strictly analytical and advisory.

Rules you MUST follow:
1. Only use information from the provided evidence context. Never fabricate facts.
2. Always cite which evidence item your statements reference (use "Evidence: <filename>").
3. If the evidence is insufficient to answer, say "I don't have enough evidence to answer this."
4. Never speculate beyond what the evidence shows.
5. Be precise, factual, and professional.
6. You are scoped to a single case — never reference other cases.
"""


@dataclass
class AISummaryResult:
    summary_text: str
    key_findings: list[str]
    model_used: str


@dataclass
class AICaseSummaryResult:
    summary_text: str
    key_findings: list[str]
    potential_leads: list[str]
    missing_information: list[str]
    open_questions: list[str]
    model_used: str


@dataclass
class AIChatResult:
    content: str
    evidence_references: list[str]
    model_used: str


@dataclass
class AIImportPreviewResult:
    title: str
    description: str | None
    priority: str  # low / medium / high / critical
    category: str | None
    tags: list[str]
    notes: list[str]


@dataclass
class AITimelineAnalysisResult:
    narrative: str
    model_used: str


def _get_client():
    """Return an openai.OpenAI client configured from settings, or None."""
    try:
        from openai import OpenAI
        from app.core.config import settings
        if settings.ai_provider == "none":
            return None, None
        return OpenAI(
            api_key=settings.ai_api_key or "no-key",
            base_url=settings.ai_api_base,
        ), settings.ai_model
    except Exception as exc:
        logger.warning("AI provider not available: %s", exc)
        return None, None


def generate_evidence_summary(
    filename: str,
    mime_type: str,
    extracted_text: str,
    entity_summary: dict,
) -> AISummaryResult | None:
    """Generate a brief AI summary for a single piece of evidence."""
    client, model = _get_client()
    if not client:
        return None

    from app.core.config import settings
    context = (
        f"Evidence file: {filename} ({mime_type})\n\n"
        f"Extracted entities: {_format_entities(entity_summary)}\n\n"
        f"Extracted text (excerpt):\n{extracted_text[:4000]}"
    )
    prompt = (
        "Analyze this evidence and provide:\n"
        "1. A 2-3 sentence factual summary of what this evidence contains.\n"
        "2. Up to 5 key findings as bullet points. Each finding must reference the evidence file.\n\n"
        "Format your response as JSON:\n"
        '{"summary": "...", "key_findings": ["...", ...]}'
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nTask:\n{prompt}"},
            ],
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
            response_format={"type": "json_object"},
        )
        import json
        data = json.loads(response.choices[0].message.content or "{}")
        return AISummaryResult(
            summary_text=str(data.get("summary", "")),
            key_findings=[str(f) for f in data.get("key_findings", [])],
            model_used=model or "",
        )
    except Exception as exc:
        logger.warning("Evidence summary generation failed: %s", exc)
        return None


def generate_case_summary(
    case_title: str,
    evidence_summaries: list[dict],
    entity_counts: dict,
) -> AICaseSummaryResult | None:
    """Generate an AI summary for the entire case based on evidence summaries."""
    client, model = _get_client()
    if not client:
        return None

    from app.core.config import settings
    ev_text = "\n\n".join(
        f"Evidence: {s['filename']}\nSummary: {s['summary']}"
        for s in evidence_summaries[:20]  # cap to 20 items
    )
    context = (
        f"Case: {case_title}\n\n"
        f"Entity counts: {_format_entities(entity_counts)}\n\n"
        f"Evidence summaries:\n{ev_text}"
    )
    prompt = (
        "Analyze this case and provide a structured intelligence summary. "
        "Format as JSON:\n"
        '{"summary": "...", "key_findings": ["..."], '
        '"potential_leads": ["..."], "missing_information": ["..."], '
        '"open_questions": ["..."]}'
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nTask:\n{prompt}"},
            ],
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
            response_format={"type": "json_object"},
        )
        import json
        data = json.loads(response.choices[0].message.content or "{}")
        return AICaseSummaryResult(
            summary_text=str(data.get("summary", "")),
            key_findings=[str(f) for f in data.get("key_findings", [])],
            potential_leads=[str(f) for f in data.get("potential_leads", [])],
            missing_information=[str(f) for f in data.get("missing_information", [])],
            open_questions=[str(f) for f in data.get("open_questions", [])],
            model_used=model or "",
        )
    except Exception as exc:
        logger.warning("Case summary generation failed: %s", exc)
        return None


def chat(
    case_title: str,
    messages: list[dict],
    evidence_context: list[dict],
) -> AIChatResult | None:
    """Answer a question using only the provided evidence context."""
    client, model = _get_client()
    if not client:
        return None

    from app.core.config import settings
    ev_text = "\n\n---\n\n".join(
        f"Evidence ID: {e['id']}\nFile: {e['filename']}\n"
        f"Summary: {e.get('summary', 'No summary')}\n"
        f"Excerpt:\n{str(e.get('text', ''))[:1500]}"
        for e in evidence_context[:10]
    )
    system_with_context = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"=== Case: {case_title} ===\n\n"
        f"=== Available Evidence ===\n{ev_text or 'No processed evidence available yet.'}"
    )

    # Track which evidence IDs are referenced
    referenced: list[str] = [e["id"] for e in evidence_context if e.get("id")]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_with_context}] + messages,
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
        )
        content = response.choices[0].message.content or "I was unable to generate a response."
        return AIChatResult(
            content=content,
            evidence_references=referenced,
            model_used=model or "",
        )
    except Exception as exc:
        logger.warning("AI chat failed: %s", exc)
        return None


def generate_timeline_analysis(
    case_title: str,
    structured_findings: dict,
    event_digest: list[dict],
) -> AITimelineAnalysisResult | None:
    """Produce a narrative reconstruction of the case timeline.

    *structured_findings* is the deterministic output of the analysis engine
    (counts of gaps, conflicts, clusters, ...). *event_digest* is a list of
    ``{"timestamp", "type", "title", "evidence"}`` rows drawn directly from the
    timeline. The model is instructed to interpret only these events and to
    reference supporting evidence — it must never invent events.
    """
    client, model = _get_client()
    if not client:
        return None

    from app.core.config import settings

    digest = "\n".join(
        f"- [{e.get('timestamp', 'undated')}] {e.get('type', 'event')}: "
        f"{e.get('title', '')}"
        + (f" (Evidence: {e['evidence']})" if e.get("evidence") else "")
        for e in event_digest[:80]
    )
    context = (
        f"Case: {case_title}\n\n"
        f"Deterministic findings: {structured_findings}\n\n"
        f"Timeline events (chronological):\n{digest or 'No dated events.'}"
    )
    prompt = (
        "Write a concise, factual narrative reconstruction of this investigation "
        "timeline. Call out gaps, suspicious activity clusters, and conflicting "
        "timestamps where the findings indicate them. Reference the supporting "
        "evidence for any claim. Do NOT introduce any event that is not listed "
        "above. If the timeline is too sparse to interpret, say so plainly."
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nTask:\n{prompt}"},
            ],
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
        )
        content = response.choices[0].message.content or ""
        if not content.strip():
            return None
        return AITimelineAnalysisResult(narrative=content, model_used=model or "")
    except Exception as exc:
        logger.warning("Timeline analysis generation failed: %s", exc)
        return None


def parse_document_for_case(
    filename: str,
    extracted_text: str,
) -> AIImportPreviewResult | None:
    """Extract structured case fields from raw document text.

    Returns None when AI is disabled or the call fails — callers must provide
    a non-AI fallback.
    """
    client, model = _get_client()
    if not client:
        return None

    from app.core.config import settings

    text_excerpt = extracted_text[:6000]
    prompt = (
        "You are a case intake assistant for a criminal investigation platform.\n"
        "A user has uploaded a document and wants to create an investigation case from it.\n\n"
        f"Document filename: {filename}\n\n"
        f"Document text (excerpt):\n{text_excerpt}\n\n"
        "Extract the following case fields from the document and return them as JSON:\n"
        '{\n'
        '  "title": "concise case title (max 120 chars)",\n'
        '  "description": "1-3 sentence summary of the case",\n'
        '  "priority": "low|medium|high|critical",\n'
        '  "category": "one of: Fraud, Cybercrime, Compliance, HR, Financial, Legal, Other — or null",\n'
        '  "tags": ["relevant", "keywords"],\n'
        '  "notes": ["key fact 1", "key fact 2"]\n'
        "}\n\n"
        "Rules:\n"
        "- Only use information from the document above.\n"
        "- If you cannot determine a field, use null (or [] for arrays).\n"
        "- title must not be null.\n"
        "- priority: default to medium unless clear urgency signals are present.\n"
        "- notes: up to 5 key facts or entities extracted from the document."
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=min(settings.ai_max_tokens, 1024),
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        import json
        data = json.loads(response.choices[0].message.content or "{}")
        priority = str(data.get("priority") or "medium").lower()
        if priority not in ("low", "medium", "high", "critical"):
            priority = "medium"
        return AIImportPreviewResult(
            title=str(data.get("title") or filename)[:120],
            description=str(data["description"]) if data.get("description") else None,
            priority=priority,
            category=str(data["category"]) if data.get("category") else None,
            tags=[str(t) for t in (data.get("tags") or [])[:10]],
            notes=[str(n) for n in (data.get("notes") or [])[:5]],
        )
    except Exception as exc:
        logger.warning("Document import parse failed: %s", exc)
        return None


def generate_embeddings(text: str) -> list[float] | None:
    """Generate semantic embedding vector for *text*. Returns None if unavailable."""
    client, _ = _get_client()
    if not client:
        return None
    try:
        from app.core.config import settings
        response = client.embeddings.create(
            model=settings.ai_embedding_model,
            input=text[:8000],
        )
        return response.data[0].embedding
    except Exception as exc:
        logger.debug("Embedding generation skipped: %s", exc)
        return None


def _format_entities(counts: dict) -> str:
    return ", ".join(f"{k}: {v}" for k, v in counts.items() if v)
