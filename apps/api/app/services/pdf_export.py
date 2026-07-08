"""Tiny, dependency-free PDF writer for tabular/text exports.

Produces a valid PDF 1.4 document using the built-in Courier font, so no fonts
need to be embedded and no third-party library is required. Intended for simple
paginated text reports (e.g. a timeline export), not rich layout.
"""

from __future__ import annotations

from datetime import datetime, timezone

_PAGE_W = 612  # US Letter, points
_PAGE_H = 792
_MARGIN = 48
_FONT_SIZE = 9
_LEADING = 12
_LINES_PER_PAGE = int((_PAGE_H - 2 * _MARGIN) / _LEADING)
_MAX_CHARS = 110  # Courier 9pt fits comfortably on Letter


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap(line: str) -> list[str]:
    line = line.replace("\t", "    ").rstrip("\n")
    if len(line) <= _MAX_CHARS:
        return [line]
    out: list[str] = []
    while len(line) > _MAX_CHARS:
        out.append(line[:_MAX_CHARS])
        line = line[_MAX_CHARS:]
    out.append(line)
    return out


def render_text_pdf(title: str, lines: list[str]) -> bytes:
    """Render *lines* into a paginated PDF, returning raw bytes."""
    header = [
        title,
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * _MAX_CHARS,
    ]
    wrapped: list[str] = []
    for raw in header + lines:
        wrapped.extend(_wrap(raw) or [""])

    # Paginate
    pages: list[list[str]] = [
        wrapped[i : i + _LINES_PER_PAGE]
        for i in range(0, max(len(wrapped), 1), _LINES_PER_PAGE)
    ] or [[""]]

    objects: list[bytes] = []

    def add_object(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font_id = add_object(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"
    )

    page_ids: list[int] = []
    content_ids: list[int] = []
    for page_lines in pages:
        stream_parts = [b"BT", f"/F1 {_FONT_SIZE} Tf".encode(), f"{_LEADING} TL".encode()]
        stream_parts.append(f"{_MARGIN} {_PAGE_H - _MARGIN} Td".encode())
        first = True
        for ln in page_lines:
            if first:
                stream_parts.append(f"({_escape(ln)}) Tj".encode())
                first = False
            else:
                stream_parts.append(f"T* ({_escape(ln)}) Tj".encode())
        stream_parts.append(b"ET")
        stream = b"\n".join(stream_parts)
        content_body = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )
        content_ids.append(add_object(content_body))
        page_ids.append(0)  # placeholder, filled after pages object id known

    pages_obj_id = len(objects) + len(pages) + 1  # reserve page object ids first

    # Now create page objects (their ids follow current objects list)
    real_page_ids: list[int] = []
    for content_id in content_ids:
        body = (
            f"<< /Type /Page /Parent {pages_obj_id} 0 R "
            f"/MediaBox [0 0 {_PAGE_W} {_PAGE_H}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode()
        real_page_ids.append(add_object(body))

    kids = " ".join(f"{pid} 0 R" for pid in real_page_ids)
    pages_body = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(real_page_ids)} >>".encode()
    )
    actual_pages_id = add_object(pages_body)
    catalog_id = add_object(f"<< /Type /Catalog /Pages {actual_pages_id} 0 R >>".encode())

    # Assemble file with xref
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_pos = len(out)
    n = len(objects) + 1
    out += f"xref\n0 {n}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {n} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
    )
    return bytes(out)
