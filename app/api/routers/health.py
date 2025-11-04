from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.options("/__cors_test__")
def cors_preflight():
    return {"ok": True}
