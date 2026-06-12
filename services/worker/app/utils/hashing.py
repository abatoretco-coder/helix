import hashlib


def hash_content(text: str) -> str:
    """SHA-256 of the text content (used for dedup)."""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def hash_url(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()
