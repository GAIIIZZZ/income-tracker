from fastapi import APIRouter

from ..db import get_conn

router = APIRouter()


@router.post("/clear")
def clear_unsaved(draft_slot: int = 1):
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM transactions WHERE batch_id IS NULL AND draft_slot = ?", (draft_slot,)
        )
        return {"deleted": cur.rowcount}
