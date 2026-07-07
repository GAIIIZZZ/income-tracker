from typing import Optional

from fastapi import APIRouter

from ..db import get_conn

router = APIRouter()


@router.post("/clear")
def clear_unsaved(draft_slot: int = 1, transaction_type: Optional[str] = None):
    query = "DELETE FROM transactions WHERE batch_id IS NULL AND draft_slot = ?"
    params: list = [draft_slot]
    if transaction_type:
        query += " AND transaction_type = ?"
        params.append(transaction_type)
    with get_conn() as conn:
        cur = conn.execute(query, params)
        return {"deleted": cur.rowcount}
