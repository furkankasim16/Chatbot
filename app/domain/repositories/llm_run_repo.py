
# app/domain/repositories/llm_run_repo.py

from typing import Any, List,Dict, Optional

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

def get_llm_stats_summary() -> List[Dict[str, Any]]:
    """
    llm_generation_runs tablosundan model bazlı latency ve token istatistikleri döner.
    """
    result: List[Dict[str, Any]] = []

    with app_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                model_name,
                COUNT(*) AS total_calls,
                AVG(latency_ms) AS avg_latency_ms,
                MIN(latency_ms) AS min_latency_ms,
                MAX(latency_ms) AS max_latency_ms,
                AVG(COALESCE(token_input, 0)) AS avg_input_tokens,
                AVG(COALESCE(token_output, 0)) AS avg_output_tokens
            FROM llm_generation_runs
            GROUP BY model_name
            ORDER BY model_name;
            """
        )

        rows = cursor.fetchall()

        for row in rows:
            result.append(
                {
                    "model_name": row["model_name"],
                    "total_calls": row["total_calls"],
                    "avg_latency_ms": float(row["avg_latency_ms"]) if row["avg_latency_ms"] is not None else None,
                    "min_latency_ms": row["min_latency_ms"],
                    "max_latency_ms": row["max_latency_ms"],
                    "avg_input_tokens": float(row["avg_input_tokens"]) if row["avg_input_tokens"] is not None else None,
                    "avg_output_tokens": float(row["avg_output_tokens"]) if row["avg_output_tokens"] is not None else None,
                }
            )

    return result
