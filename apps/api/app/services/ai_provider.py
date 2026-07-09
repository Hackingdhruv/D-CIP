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
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an AI assistant embedded in D-CIP, a Digital Criminal
Investigation Platform. You help investigators analyze evidence, not make investigative
decisions. Your role is strictly analytical and advisory.

Rules you MUST follow:
1. Only use information from the provided evidence context. Never fabricate facts.
2. Always cite which evidence item your statements reference, using the exact format
   "[Evidence: <filename>]" (square brackets). Never invent a citation for a file that
   was not given to you in the evidence context.
3. If, after reviewing the evidence, you cannot provide ANY substantive answer, reply
   only with "I don't have enough evidence to answer this." Never append that sentence
   after you have already given a substantive, evidence-based answer — the two are
   contradictory and confuse the investigator.
4. Never speculate beyond what the evidence shows.
5. Be precise, factual, and professional.
6. You are scoped to a single case — never reference other cases.
7. Never output raw internal identifiers (database IDs, UUIDs, hashes not present in the
   evidence text, or similar tokens) unless they are genuinely useful to the investigator
   and clearly labeled (e.g. a file hash the evidence itself reports). Cite evidence by
   filename only, as instructed in rule 2.

Entity formatting — evidence often contains several distinct identifiers for the same
person or asset. Keep them distinct and never conflate them:
- Person names (e.g. "Dr. Erin Solano") are proper names. Use them when referring to a
  person.
- Account or login identifiers (e.g. "HELIOS\\e.solano", "DOMAIN\\username", or an email
  address used as a login) identify a system account, not a person's name. Only use the
  literal account string when the point is specifically about a login/account event;
  otherwise refer to the person by name if the evidence links the two.
- Devices and media (e.g. USB drives, hard disks, phones, hostnames) are objects, not
  locations — never phrase a device as somewhere a person or event was "at". Say
  "using device X" or "via device X" instead.

Numeric formatting — when evidence reports a byte count or other large raw number,
report the exact figure as given, and you may add a human-readable approximation in
parentheses, e.g. "23,449,600,000 bytes (~23.45 GB)". Only compute totals or
correlations you can actually derive from the numbers present in the evidence — never
estimate or invent a figure that is not supported by the evidence.

Response structure — for questions asking for an investigation overview or summary,
prefer short labeled sections such as: Investigation Summary, Key Indicators, Timeline,
Affected Assets/Data, Relevant Evidence, Priority Investigation Steps. Omit any section
that has nothing to say. For narrow, specific questions, just answer directly without
forcing this structure. Keep the overall response concise.

Temporal precision — every dated claim you make about a specific event must use
the exact date/timestamp that the EVIDENCE shows for that event, never a date
taken from the case description or other background context. Background context
(e.g. a resignation date, a hire date, an incident-report date) describes the
overall situation and is NOT the date any particular evidence event occurred on
— do not substitute it in. If evidence events span multiple dates, describe them
as a range ("between <first date> and <last date>") or list each date separately;
never compress a multi-day pattern into a single background-mentioned date.
Before writing a specific date next to a claim, check that the date is the one
actually attached to that claim in the evidence, not a date from elsewhere.

Do not infer unstated relationships between separate facts — this applies to
dates, employment status, identity, ownership, and causation alike. Two facts
that come from different sources (background context vs. evidence, or two
different evidence items) must be reported as what they are: separate facts,
not merged into a new claim unless the evidence or context explicitly states
that connection. For example, if background context gives a date for one thing
(e.g. a resignation) and evidence separately shows activity on other dates, do
not assert that the most recent evidence date IS the background date, or that
it "was" the day of the background event, unless something explicitly says so.
When you want to relate such facts without overstating the connection, use
hedged, neutral phrasing — e.g. "in the days leading up to her departure" or
"around the time of the resignation" — rather than asserting a specific inferred
date or status as fact.

Concretely: a phrase like "her last working day" asserts a specific, singular
fact (that a specific date was that person's final day of employment). Only use
phrasing like that if some evidence or the case description literally states
which date was their last working day. If all you actually know is a
resignation/departure date from background context plus some evidence activity
on nearby dates, do NOT call any of those evidence dates "her last working
day" — say the activity occurred "in the days/weeks leading up to her
departure" instead. This same caution applies to any other singular-sounding
inferred fact (e.g. "the day she was fired", "her final login", "the moment
she decided to leave") that isn't literally established by the evidence.
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
        '{"summary": "...", "key_findings": ["...", ...]}\n\n'
        "Each item in \"key_findings\" MUST be a single plain-text sentence (a string), "
        "never a nested object or dictionary. Do not invent or mention any person, "
        "account, username, device, or entity that is not literally present in the "
        "evidence above — if you have nothing more to add, return fewer findings "
        "rather than inventing one."
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
            key_findings=[_flatten_finding(f) for f in data.get("key_findings", [])],
            model_used=model or "",
        )
    except Exception as exc:
        logger.warning("Evidence summary generation failed: %s", exc)
        return None


def generate_case_summary(
    case_title: str,
    evidence_summaries: list[dict],
    entity_counts: dict,
    case_description: str | None = None,
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
    case_desc_block = (
        f"Case Description (investigator-provided background): {case_description}\n\n"
        if case_description
        else ""
    )
    context = (
        f"Case: {case_title}\n\n"
        f"{case_desc_block}"
        f"Entity counts: {_format_entities(entity_counts)}\n\n"
        f"Evidence summaries:\n{ev_text}"
    )
    prompt = (
        "Analyze this case and provide a structured intelligence summary. "
        "Format as JSON:\n"
        '{"summary": "...", "key_findings": ["..."], '
        '"potential_leads": ["..."], "missing_information": ["..."], '
        '"open_questions": ["..."]}\n\n'
        "Every item in every array MUST be a single plain-text sentence (a string), "
        "never a nested object or dictionary. Do not invent or mention any person, "
        "account, username, device, or entity that is not literally present in the "
        "evidence summaries above — if a field has nothing grounded to say, return "
        "an empty array for it rather than inventing content to fill it."
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
            key_findings=[_flatten_finding(f) for f in data.get("key_findings", [])],
            potential_leads=[_flatten_finding(f) for f in data.get("potential_leads", [])],
            missing_information=[_flatten_finding(f) for f in data.get("missing_information", [])],
            open_questions=[_flatten_finding(f) for f in data.get("open_questions", [])],
            model_used=model or "",
        )
    except Exception as exc:
        logger.warning("Case summary generation failed: %s", exc)
        return None


_FALLBACK_SENTENCE = "I don't have enough evidence to answer this."
_PAREN_CITATION_RE = re.compile(r"\((?:Evidence|File|Source):\s*([^)]+)\)")
_BULLET_CITATION_RE = re.compile(r"^(\s*[-*]\s*)(?:File|Source):\s*(.+)$", re.MULTILINE)
_NESTED_CITATION_RE = re.compile(r"\[Evidence:\s*\[([^\]]+)\]\]")
_BARE_TOKEN_LINE_RE = re.compile(r"^[0-9a-fA-F]{6,40}$")
_BYTES_RE = re.compile(r"\b(\d[\d,]{2,})\s+bytes?\b(?!\s*\(~)", re.IGNORECASE)
_CITATION_RE = re.compile(r"\[Evidence:\s*([^\]]+)\]")
_UNGROUNDED_LAST_DAY_RE = re.compile(
    r"\b(?:(?:on|during)\s+)?(?P<subj>her|his|their|its|the|"
    r"[a-z][\w.]*(?:\s[a-z][\w.]*){0,2}'s)\s+"
    r"(?:last|final)\s+(?:working day|day of work)\b",
    re.IGNORECASE,
)
_LAST_DAY_GROUNDING_RE = re.compile(
    r"\b(?:last|final)\s+(?:working day|day of work)\b", re.IGNORECASE
)
_DATE_NEAR_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _last_day_paired_with_a_date(grounding_text: str) -> bool:
    """True only if the "last/final working day" idiom appears with an actual
    date near it in the source text — i.e. the source itself pins the idiom to
    a specific date, not just uses the phrase in the abstract.
    """
    for m in _LAST_DAY_GROUNDING_RE.finditer(grounding_text):
        # Tight window: only counts as "pinned" if the date is in the same
        # clause (e.g. "on 2099-03-04, her last working day"), not just
        # somewhere earlier in the same paragraph/sentence.
        window = grounding_text[max(0, m.start() - 25) : m.end() + 25]
        if _DATE_NEAR_RE.search(window):
            return True
    return False


def _guard_unsupported_last_day_claims(content: str, grounding_text: str) -> str:
    """Neutralize an unfounded "her/his/their last working day" claim into
    hedged phrasing, unless the source text itself pins that idiom to a
    specific date. Case descriptions and evidence often use the phrase
    "last working day" in the abstract without ever stating which calendar
    date that was — a model that then attaches a concrete date to it (or to a
    specific evidence event) is inferring a fact nobody actually established.
    General pattern guard, not tied to any specific case, person, or date.
    """
    if _last_day_paired_with_a_date(grounding_text):
        return content  # the source itself ties the idiom to a real date — trust it

    def _sub(m: re.Match[str]) -> str:
        subj = m.group("subj")
        if subj.lower() in ("her", "his", "their", "its"):
            return f"in the days leading up to {subj.lower()} departure"
        if subj.lower() == "the":
            return "in the days leading up to the departure"
        return f"in the days leading up to {subj} departure"  # "<Name>'s" possessive form

    return _UNGROUNDED_LAST_DAY_RE.sub(_sub, content)


def _humanize_bytes(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f} GB"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f} MB"
    return f"{n / 1_000:.2f} KB"


def _annotate_byte_counts(text: str) -> str:
    def _sub(m: re.Match[str]) -> str:
        n = int(m.group(1).replace(",", ""))
        if n < 1_000:
            return m.group(0)
        return f"{n:,} bytes (~{_humanize_bytes(n)})"

    return _BYTES_RE.sub(_sub, text)


def _clean_ai_response(content: str) -> str:
    """General, case-agnostic cleanup applied to every chat reply.

    - Normalizes "(Evidence: x)" / "(File: x)" / "(Source: x)" citations to the
      preferred "[Evidence: x]" form, and collapses an accidental
      "[Evidence: [x]]" double-bracket.
    - Normalizes bulleted "- File: x" / "- Source: x" lines to "- [Evidence: x]"
      for the same reason.
    - Appends a human-readable size next to raw byte counts (pure arithmetic on a
      number the model already produced — never invents a figure).
    - Drops a trailing "insufficient evidence" sentence if the model already gave
      a substantive answer beforehand — the two are contradictory.
    - Drops trailing lines that consist of nothing but a bare hex/id-looking
      token, since an unlabeled raw identifier provides no investigative value.
    """
    text = _PAREN_CITATION_RE.sub(r"[Evidence: \1]", content)
    text = _BULLET_CITATION_RE.sub(r"\1[Evidence: \2]", text)
    text = _NESTED_CITATION_RE.sub(r"[Evidence: \1]", text).strip()
    text = _annotate_byte_counts(text)

    lines = text.splitlines()
    while lines and _BARE_TOKEN_LINE_RE.match(lines[-1].strip()):
        lines.pop()
    text = "\n".join(lines).rstrip()

    if text.lower().endswith(_FALLBACK_SENTENCE.lower()):
        before = text[: -len(_FALLBACK_SENTENCE)].rstrip()
        # Only strip the fallback if there's a substantive answer before it —
        # if it's the entire response, leave it as the genuine "no answer" case.
        if len(before) > 80:
            text = before

    return text or content


def chat(
    case_title: str,
    messages: list[dict],
    evidence_context: list[dict],
    case_description: str | None = None,
) -> AIChatResult | None:
    """Answer a question using only the provided evidence context."""
    client, model = _get_client()
    if not client:
        return None

    from app.core.config import settings
    ev_text = "\n\n---\n\n".join(
        f"File: {e['filename']}\n"
        f"Summary: {e.get('summary', 'No summary')}\n"
        f"Excerpt:\n{str(e.get('text', ''))[:1500]}"
        for e in evidence_context[:10]
    )
    case_desc_block = (
        f"=== Case Description (investigator-provided background — not a citable "
        f"evidence file) ===\n{case_description}\n\n"
        if case_description
        else ""
    )
    system_with_context = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"=== Case: {case_title} ===\n\n"
        f"{case_desc_block}"
        f"=== Available Evidence ===\n{ev_text or 'No processed evidence available yet.'}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_with_context}] + messages,
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
        )
        content = response.choices[0].message.content or "I was unable to generate a response."
        content = _clean_ai_response(content)
        content = _guard_unsupported_last_day_claims(
            content, f"{case_description or ''}\n{ev_text}"
        )

        # Surface evidence by filename (a human-readable, self-explanatory label),
        # never by raw internal ID. Prefer files the model actually cited in the
        # answer; fall back to every file it had access to if it cited none.
        cited = {m.strip() for m in _CITATION_RE.findall(content)}
        all_filenames = [e["filename"] for e in evidence_context if e.get("filename")]
        referenced = [f for f in all_filenames if f in cited] or all_filenames

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


_PREFERRED_FLATTEN_KEYS = (
    "description",
    "finding",
    "lead",
    "text",
    "summary",
    "detail",
    "information",
    "question",
)


def _flatten_finding(item: object) -> str:
    """Coerce a JSON list item into a single plain-text sentence.

    Small local models sometimes disobey a "return a list of strings"
    instruction and return a list of nested objects instead (e.g.
    ``{"Indicator": "X", "Description": "Y"}``). A blind ``str(item)`` would
    render that as literal Python-dict syntax in the UI. Instead, prefer a
    descriptive field if one exists; otherwise join every value into a
    readable sentence fragment.
    """
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in _PREFERRED_FLATTEN_KEYS:
            for actual_key, value in item.items():
                if actual_key.lower() == key and isinstance(value, str) and value.strip():
                    return value.strip()
        parts = [str(v).strip() for v in item.values() if str(v).strip()]
        return ": ".join(parts) if parts else str(item)
    return str(item)
