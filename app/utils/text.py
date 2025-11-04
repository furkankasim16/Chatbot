import json, hashlib

def json_hash(d: dict) -> str:
    """id/hash alanlarını hariç tutup stabil bir sha256 üretir."""
    clean = {k: v for k, v in d.items() if k not in ("id", "hash")}
    payload = json.dumps(clean, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def normalize_whitespace(s: str) -> str:
    return " ".join((s or "").split())
