"""Storage abstraction layer.

The storage backend is accessed through ``get_storage()``.  Swapping to S3,
Azure Blob, or MinIO requires only a new backend class that satisfies
``StorageBackend`` — the rest of the application is unchanged.
"""

from __future__ import annotations

from app.storage.local import LocalStorageBackend

_backend: LocalStorageBackend | None = None


def get_storage() -> LocalStorageBackend:
    """Return the (lazily initialised) storage singleton."""
    global _backend
    if _backend is None:
        from app.core.config import settings
        _backend = LocalStorageBackend(base_dir=settings.upload_dir)
    return _backend
