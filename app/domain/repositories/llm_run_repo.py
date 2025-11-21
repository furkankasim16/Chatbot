# app/domain/repositories/llm_run_repo.py

from typing import List, Optional
from app.core.db import app_cursor
from app.domain.schemas.llm_run import LLMRun


def add_llm_run(
    *,
    model_name: str,
    prompt_hash: Optional[str],
    latency_ms: int,
    token_input: Optional[int] = None,
    token_output: Optional[int] = None,
) -> LLMRun:
    """
    Bir LLM çağrısının performans kaydını veritabanına yazar.
    """
    run = LLMRun(
        model_name=model_name,
        prompt_hash=prompt_hash,
        latency_ms=latency_ms,
        token_input=token_input,
        token_output=token_output,
    )

    with app_cursor() as c:
        c.execute(
            """
            INSERT INTO llm_generation_runs (
                model_name, prompt_hash, latency_ms, token_input, token_output
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run.model_name,
                run.prompt_hash,
                run.latency_ms,
                run.token_input,
                run.token_output,
            ),
        )
        run.id = c.lastrowid

    return run


def list_llm_runs(limit: int = 100) -> List[LLMRun]:
    """
    Son LLM çağrısı kayıtlarını döner.
    """
    items: List[LLMRun] = []
    with app_cursor() as c:
        rows = c.execute(
            """
            SELECT
              id, model_name, prompt_hash, latency_ms,
              token_input, token_output, created_at
            FROM llm_generation_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    for row in rows:
        # sqlite3.Row ise dict'e çevirelim
        if hasattr(row, "keys"):
            data = dict(row)
        else:
            (
                id_,
                model_name,
                prompt_hash,
                latency_ms,
                token_input,
                token_output,
                created_at,
            ) = row
            data = {
                "id": id_,
                "model_name": model_name,
                "prompt_hash": prompt_hash,
                "latency_ms": latency_ms,
                "token_input": token_input,
                "token_output": token_output,
                "created_at": created_at,
            }

        items.append(LLMRun(**data))

    return items
