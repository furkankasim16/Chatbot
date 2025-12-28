# app/api/routers/admin.py

from __future__ import annotations

from typing import Optional, List, Dict, Any

from fastapi import  APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response
from pydantic import BaseModel

from app.api.deps import (
    on_start_app_db,
    on_start_questions_db,
    get_current_user,
)
from app.domain.repositories.llm_run_repo import get_llm_stats_summary
from app.domain.schemas.llm_run import LLMStatsSummary
from app.domain.services.llm_service import LLMModel
from app.domain.services.question_service import (
    pick_random_topic_and_level,
    generate_question,  # bizim facade (async → generate_question_from_llm)
)
from app.domain.repositories.quesitons_repo import (
    get_all_questions,
    update_question_review,
    delete_question,
)
from app.domain.repositories.quiz_repo import user_activity
from app.domain.services.audit_service import log_action, get_recent_logs
from app.domain.repositories.audit_repo import get_audit_stats
from app.domain.schemas.question import QuestionModel
from app.domain.schemas.audit import AuditLog
from app.domain.schemas.audit import AuditLog
# from app.core.rag import rag_client  <-- REMOVED
from app.domain.services.rag_service import rag_service, clear_collection

from app.services.pdf_service import pdf_service
from starlette.concurrency import run_in_threadpool
import hashlib

router = APIRouter(prefix="/admin", tags=["admin"])


class ReviewQuestionRequest(BaseModel):
    status: str  # "approved" | "rejected"
    notes: str | None = None


def _map_level_to_difficulty(level: str) -> str:
    """
    Eski admin UI 'beginner/intermediate/advanced' kullanıyorsa,
    bunları unified difficulty ('easy/medium/hard') ile eşliyoruz.
    Zaten doğru geliyorsa olduğu gibi döner.
    """
    level = (level or "").lower()
    mapping = {
        "beginner": "easy",
        "intermediate": "medium",
        "advanced": "hard",
    }
    return mapping.get(level, level or "medium")


# --------------------------------------------------------------------
#  SORU ÜRETİMİ (MODEL SEÇİMLİ + LOGGING)
# --------------------------------------------------------------------
@router.post("/generate-question", response_model=QuestionModel)
async def gen_question(
    topic: str,
    level: str,
    qtype: str = "mcq",  # "mcq", "true_false", "short_answer", "open_ended", "scenario"
    model: str = "ollama:default",
    dry_run: bool = False,
    use_rag: bool = False,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Seçilen LLM modeliyle yeni soru üretir, DB'ye kaydeder ve audit log atar.
    Yeni unified QuestionModel yapısını ve generate_question pipeline'ını kullanır.
    dry_run=True ise DB'ye kaydetmez, id=0 döner.
    use_rag=True ise Knowledge Base'den konuyla ilgili bağlam çeker.
    """

    difficulty = _map_level_to_difficulty(level)

    context = None
    if use_rag:
        try:
            # Topic tabanlı arama
            # n_results=3 genelde yeterli context oluşturur
            context = rag_service.retrieve_context(topic, collection_name="knowledge-base", n_results=3)
            if context:
                print(f"[RAG] Context found for topic '{topic}' ({len(context)} chars)")
            else:
                print(f"[RAG] No context found for topic '{topic}'")
        except Exception as e:
            print(f"[RAG] Error fetching context: {e}")

    params: Dict[str, Any] = {
        "question_type": qtype,
        "topic": topic,
        "difficulty": difficulty,
    }
    
    if context:
        params["context"] = context

    # Yeni pipeline: LLM → JSON → QuestionModel → DB
    q: QuestionModel = await generate_question(
        model_name=model,  # LLMModel enum → string
        params=params,
        save=not dry_run,
    )

    if getattr(q, "id", None) is None:
        # Normalde generate_question_from_llm içerisinde id set ediliyor
        raise HTTPException(status_code=500, detail="Question ID not set after generation")

    # Audit
    log_action(
        user_id=current_user["id"],
        action="ADMIN_GENERATE_QUESTION",
        entity_type="question",
        entity_id=q.id,
        details={
            "topic": topic,
            "level": level,
            "difficulty": difficulty,
            "qtype": qtype,
            "model": model,
            "dry_run": dry_run,
        },
    )

    return q


# --------------------------------------------------------------------
#  RANDOM SORU ÜRETİMİ (MODEL SEÇİMLİ)
# --------------------------------------------------------------------
@router.post("/generate-random-question", response_model=QuestionModel)
async def generate_random_question(
    model: LLMModel = LLMModel.OLLAMA_LOCAL,
    dry_run: bool = False,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Rastgele topic/level seçerek soru üretir.
    Yeni unified QuestionModel + generate_question pipeline kullanır.
    """

    topic, level = pick_random_topic_and_level()
    difficulty = _map_level_to_difficulty(level)

    params: Dict[str, Any] = {
        "question_type": "mcq",  # random üretimi şimdilik mcq ile sınırlandırıyoruz
        "topic": topic,
        "difficulty": difficulty,
    }

    q: QuestionModel = await generate_question(
        model_name=model.value,
        params=params,
        save=not dry_run,
    )

    if getattr(q, "id", None) is None:
        raise HTTPException(status_code=500, detail="Question ID not set after generation")

    log_action(
        user_id=current_user["id"],
        action="ADMIN_GENERATE_RANDOM_QUESTION",
        entity_type="question",
        entity_id=q.id,
        details={
            "topic": topic,
            "level": level,
            "difficulty": difficulty,
            "qtype": "mcq",
            "model": model.value,
            "dry_run": dry_run,
        },
    )

    return q


# --------------------------------------------------------------------
#  SORU LİSTELEME
# --------------------------------------------------------------------
@router.get("/questions", response_model=List[QuestionModel])
def list_questions(
    limit: int = 100,
    offset: int = 0,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_QUESTIONS",
        details={"limit": limit, "offset": offset},
    )
    return get_all_questions(limit=limit, offset=offset)


# --------------------------------------------------------------------
#  KULLANICI AKTİVİTESİ — QUIZ PERFORMANSI
# --------------------------------------------------------------------
@router.get("/user-activity")
def get_user_activity(
    limit: int = 100,
    _=Depends(on_start_app_db),
    current_user: dict = Depends(get_current_user),
):
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_USER_ACTIVITY",
        details={"limit": limit},
    )

    return user_activity(limit=limit)


# --------------------------------------------------------------------
#  AUDIT LOG LİSTELEME — TEK VE DOĞRU ENDPOINT
# --------------------------------------------------------------------
@router.get("/audit-logs", response_model=List[AuditLog])
def list_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    _=Depends(on_start_app_db),
    current_user: dict = Depends(get_current_user),
):
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_AUDIT_LOGS",
        details={"limit": limit},
    )

    return get_recent_logs(limit=limit)


@router.get("/audit-stats")
def audit_stats_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """
    Dashboard için görselleştirme verileri.
    """
    # Loglamak istersek loglarız ama "View Dashboard" gibi çok sık çağrılan bir şey log kirliliği yaratabilir.
    # Şimdilik loglamayalım veya 'verbose' bir aksiyon olarak loglayalım.
    return get_audit_stats()


@router.get("/llm-stats/summary", response_model=List[LLMStatsSummary])
def llm_stats_summary(
    current_user: dict = Depends(get_current_user),
) -> List[LLMStatsSummary]:
    """
    LLM model bazlı performans özeti:
    - total_calls
    - avg/min/max latency
    - avg input/output tokens
    """
    log_action(
        user_id=current_user["id"],
        action="ADMIN_VIEW_LLM_STATS",
        details={},
    )
    stats = get_llm_stats_summary()
    return [LLMStatsSummary(**row) for row in stats]


@router.post("/questions/{question_id}/review")
def review_question(
    question_id: int,
    body: ReviewQuestionRequest,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Geçersiz status")

    # DB güncelle
    update_question_review(
        question_id=question_id,
        status=body.status,
        notes=body.notes,
        reviewer_id=current_user["id"],
    )

    # Audit log
    log_action(
        user_id=current_user["id"],
        action="ADMIN_REVIEW_QUESTION",
        entity_type="question",
        entity_id=question_id,
        details={
            "status": body.status,
            "notes": body.notes,
        },
    )

    return {"ok": True}


@router.delete("/questions/{question_id}", status_code=204)
def delete_question_endpoint(
    question_id: int,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Admin: ID'ye göre soruyu siler (reddetme butonu).
    Soru yoksa 404 döner.
    """
    deleted = delete_question(question_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Question not found")

    log_action(
        user_id=current_user["id"],
        action="ADMIN_DELETE_QUESTION",
        entity_type="question",
        entity_id=question_id,
        details={},
    )

    # 204 No Content
    return Response(status_code=204)

def require_admin(current=Depends(get_current_user)):
    if not getattr(current, "is_admin", False) and not current.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    return current

@router.post("/generate-from-pdf", response_model=QuestionModel)
async def generate_from_pdf(
    topic: str = Form(...),
    level: str = Form("beginner"),
    qtype: str = Form("mcq"),
    model: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    # Log the attempt first
    log_action(
        user_id=current_user["id"],
        action="ADMIN_GENERATE_FROM_PDF",
        details={
            "filename": file.filename,
            "topic": topic,
            "level": level,
            "qtype": qtype,
            "model": model,
        },
    )

    try:
        content = await file.read()
        
        # 1. Chunking and Indexing
        # We use a user-specific 'session' topic or just index globally with robust metadata
        # For this feature, we want to index the PDF and immediately use it.
        # Let's assume we add it to the global knowledge base but filtered by file name or just retrieve relevant chunks.
        
        chunks, metadatas, ids = await pdf_service.extract_and_chunk(
            file_content=content,
            filename=file.filename,
            topic=topic
        )
        
        if not chunks:
             raise HTTPException(status_code=400, detail="PDF'ten metin çıkarılamadı.")

        # Indexing (Blocking call, but fast for single PDF usually)
        # Note: If valid IDs conflict, it might error or update depending on Chroma version.
        # We can append a timestamp or random hash to IDs if versioning is needed.
        # Indexing (Blocking call, but fast for single PDF usually)
        # Note: If valid IDs conflict, it might error or update depending on Chroma version.
        # We can append a timestamp or random hash to IDs if versioning is needed.
        rag_service.add_documents(chunks, metadatas, ids, collection_name="knowledge-base")
        
        # 2. Retrieve Context relevant to the *topic* from this PDF
        # We filter by filename to ensure we only generate from THIS PDF
        context = rag_service.retrieve_context(topic, collection_name="knowledge-base", n_results=5)
        
        # Unpack results
        # results['documents'] is list of list of strings
        context_list = results.get("documents", [[]])[0]
        context = "\n\n".join(context_list)
        
        if not context:
             # Fallback: Use random chunks from this file if topic-based retrieval failed
             context = "\n\n".join(chunks[:5])

        difficulty = _map_level_to_difficulty(level)
        
        params: Dict[str, Any] = {
            "question_type": qtype,
            "topic": topic,
            "difficulty": difficulty,
            "context": context
        }

        # Use the selected model or default to OLLAMA_LOCAL
        model_enum = LLMModel.OLLAMA_LOCAL
        if model:
            try:
                # Try to match string to enum
                model_enum = LLMModel(model)
            except ValueError:
                # Fallback or keep default if invalid
                pass

        q: QuestionModel = await generate_question(
            model_name=model_enum.value,
            params=params,
        )

        if getattr(q, "id", None) is None:
            raise HTTPException(status_code=500, detail="Question ID not set after generation")
        
        # Add source file info to tags
        if q.tags:
            q.tags.append(f"source:{file.filename}")
        else:
            q.tags = [f"source:{file.filename}"]

        return q

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF işleme hatası: {str(e)}")

from app.domain.repositories.users_repo import get_all_students_stats

@router.get("/students")
def list_students(
    current_user: dict = Depends(require_admin),
):
    """
    Returns statistics for all students (non-admins).
    """
    return get_all_students_stats()


from app.domain.repositories.users_repo import get_student_details

@router.get("/students/{user_id}/details")
def get_student_details_endpoint(
    user_id: int,
    current_user: dict = Depends(require_admin),
):
    """
    Returns details for a specific student.
    """
    details = get_student_details(user_id)
    if not details:
        raise HTTPException(status_code=404, detail="Student not found")
    return details
