from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from ..db import get_conn
from ..models import BatchCreate
from ..pipeline.recheck import recheck_transaction

router = APIRouter()

BATCH_SELECT = """
    SELECT b.id, b.name, b.is_favorite, b.created_at,
           MAX(t.updated_at) as last_edited,
           COUNT(t.id) as count, COALESCE(SUM(t.amount), 0) as total
    FROM batches b
    LEFT JOIN transactions t ON t.batch_id = b.id
"""

SORT_ORDER = {
    "favorite": "b.is_favorite DESC, b.created_at DESC",
    "created": "b.created_at DESC",
    "updated": "last_edited DESC",
    "name": "b.name COLLATE NOCASE ASC",
}


def _batch_summary(conn, batch_id: int) -> dict:
    row = conn.execute(f"{BATCH_SELECT} WHERE b.id = ? GROUP BY b.id", (batch_id,)).fetchone()
    return dict(row)


@router.get("/batches")
def list_batches(sort: str = "favorite"):
    order_by = SORT_ORDER.get(sort, SORT_ORDER["favorite"])
    with get_conn() as conn:
        rows = conn.execute(f"{BATCH_SELECT} GROUP BY b.id ORDER BY {order_by}").fetchall()
        return [dict(r) for r in rows]


@router.post("/batches")
async def save_batch(payload: BatchCreate):
    draft_slot = payload.draft_slot or 1

    with get_conn() as conn:
        unsaved = conn.execute(
            "SELECT id FROM transactions WHERE batch_id IS NULL AND draft_slot = ?", (draft_slot,)
        ).fetchall()
        if not unsaved:
            raise HTTPException(400, "No unsaved transactions to save")

        name = payload.name
        if not name:
            existing_count = conn.execute("SELECT COUNT(*) as c FROM batches").fetchone()["c"]
            name = f"Save Transactions {existing_count + 1}"

        cur = conn.execute("INSERT INTO batches (name) VALUES (?)", (name,))
        batch_id = cur.lastrowid
        conn.execute(
            "UPDATE transactions SET batch_id = ? WHERE batch_id IS NULL AND draft_slot = ?",
            (batch_id, draft_slot),
        )

    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM transactions WHERE batch_id = ?", (batch_id,)
        ).fetchall()]

    for row in rows:
        recheck_status, recheck_note = await run_in_threadpool(recheck_transaction, row)
        with get_conn() as conn:
            new_status = "needs_review" if recheck_status == "mismatch" else row["status"]
            conn.execute(
                """UPDATE transactions SET recheck_status = ?, recheck_note = ?, status = ?,
                       updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (recheck_status, recheck_note, new_status, row["id"]),
            )

    with get_conn() as conn:
        return _batch_summary(conn, batch_id)


@router.patch("/batches/{batch_id}")
def update_batch(batch_id: int, payload: BatchCreate):
    updates = {}
    if payload.name is not None:
        if not payload.name.strip():
            raise HTTPException(400, "Name cannot be empty")
        updates["name"] = payload.name.strip()
    if payload.is_favorite is not None:
        updates["is_favorite"] = 1 if payload.is_favorite else 0

    if not updates:
        raise HTTPException(400, "No fields to update")

    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM batches WHERE id = ?", (batch_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Batch not found")

        set_clause = ", ".join(f"{field} = ?" for field in updates)
        conn.execute(f"UPDATE batches SET {set_clause} WHERE id = ?", list(updates.values()) + [batch_id])
        return _batch_summary(conn, batch_id)


@router.delete("/batches/{batch_id}")
def delete_batch(batch_id: int):
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM batches WHERE id = ?", (batch_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Batch not found")
        conn.execute("DELETE FROM batches WHERE id = ?", (batch_id,))
        return {"deleted": batch_id}
