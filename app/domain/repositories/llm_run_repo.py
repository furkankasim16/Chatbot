
# app/domain/repositories/llm_run_repo.py

from typing import Any, List, Dict, Optional

from app.core.db import app_cursor
from app.domain.schemas.llm_run import LLMRun


def add_llm_run(
    *,
    model_name: str,
    prompt_hash: Optional[str],
    latency_ms: int,
    token_input: Optional[int] = None,
    token_output: Optional[int] = None,
    is_success: bool = True,
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
        is_success=is_success
    )

    with app_cursor() as c:
        c.execute(
            """
            INSERT INTO llm_generation_runs (
                model_name, prompt_hash, latency_ms, token_input, token_output, is_success
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run.model_name,
                run.prompt_hash,
                run.latency_ms,
                run.token_input,
                run.token_output,
                1 if run.is_success else 0,
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
              token_input, token_output, created_at, is_success
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
                is_success_val,
            ) = row
            data = {
                "id": id_,
                "model_name": model_name,
                "prompt_hash": prompt_hash,
                "latency_ms": latency_ms,
                "token_input": token_input,
                "token_output": token_output,
                "created_at": created_at,
                "is_success": bool(is_success_val),
            }

        # Validate against schema (schema might need update if strict, but ignoring extra fields is default)
        # Assuming LLMRun schema update follows or handles it dynamic
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
                SUM(CASE WHEN is_success = 1 THEN 1 ELSE 0 END) as success_calls,
                AVG(latency_ms) AS avg_latency_ms,
                MIN(latency_ms) AS min_latency_ms,
                MAX(latency_ms) AS max_latency_ms,
                AVG(COALESCE(token_input, 0)) AS avg_input_tokens,
                AVG(COALESCE(token_output, 0)) AS avg_output_tokens
            FROM llm_generation_runs
            WHERE model_name IS NOT NULL
            GROUP BY model_name
            ORDER BY model_name;
            """
        )

        rows = cursor.fetchall()

        for row in rows:
            if hasattr(row, "keys"):
                model_name = row["model_name"]
                total_calls = row["total_calls"]
                success_calls = row["success_calls"]
                avg_latency = row["avg_latency_ms"]
                min_latency = row["min_latency_ms"]
                max_latency = row["max_latency_ms"]
                avg_input = row["avg_input_tokens"]
                avg_output = row["avg_output_tokens"]
            else:
                (
                    model_name,
                    total_calls,
                    success_calls,
                    avg_latency,
                    min_latency,
                    max_latency,
                    avg_input,
                    avg_output,
                ) = row

            success_rate = 0.0
            if total_calls > 0:
                success_rate = round((success_calls / total_calls) * 100, 1)

            result.append(
                {
                    "model_name": model_name,
                    "total_calls": total_calls,
                    "success_calls": success_calls,
                    "success_rate": success_rate,
                    "avg_latency_ms": float(avg_latency) if avg_latency is not None else None,
                    "min_latency_ms": min_latency,
                    "max_latency_ms": max_latency,
                    "avg_input_tokens": float(avg_input) if avg_input is not None else None,
                    "avg_output_tokens": float(avg_output) if avg_output is not None else None,
                }
            )

    return result
