"""Local filesystem storage backend.

Architecture note: This class implements the same interface that an S3 /
Azure Blob / MinIO backend would implement.  Future backends need only satisfy
the same methods; no call sites change.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO


class LocalStorageBackend:
    """Store files on the local filesystem under a configurable base directory."""

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _resolve(self, path: str) -> Path:
        return self._base / path

    # ── Public interface ───────────────────────────────────────────────────────

    def save(self, path: str, stream: BinaryIO) -> tuple[int, str]:
        """Write *stream* to *path*; return ``(bytes_written, sha256_hex)``."""
        dest = self._resolve(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        hasher = hashlib.sha256()
        size = 0
        with open(dest, "wb") as fp:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                fp.write(chunk)
                hasher.update(chunk)
                size += len(chunk)
        return size, hasher.hexdigest()

    def open(self, path: str) -> BinaryIO:
        return open(self._resolve(path), "rb")  # type: ignore[return-value]

    def delete(self, path: str) -> None:
        p = self._resolve(path)
        if p.exists():
            p.unlink()

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def size(self, path: str) -> int:
        return self._resolve(path).stat().st_size

    def absolute_path(self, path: str) -> str:
        return str(self._resolve(path).resolve())

    def compute_sha256(self, path: str) -> str:
        """Re-compute SHA-256 of an already-stored file (for integrity checks)."""
        hasher = hashlib.sha256()
        with self.open(path) as fp:
            while True:
                chunk = fp.read(65536)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
