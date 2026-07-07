from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..db import get_conn
from ..models import TransactionCreate, TransactionUpdate

router = APIRouter()


@router.get("/transactions")
def list_transactions(
    batch_id: Optional[str] = "unsaved",
    draft_slot: Optional[int] = None,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(500, le=2000),
):
    clauses = []
    params: list = []

    if batch_id is None or batch_id == "unsaved":
        clauses.append("batch_id IS NULL")
        if draft_slot is not None:
            clauses.append("draft_slot = ?")
            params.append(draft_slot)
    elif batch_id != "all":
        clauses.append("batch_id = ?")
        params.append(int(batch_id))

    if transaction_type:
        clauses.append("transaction_type = ?")
        params.append(transaction_type)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if search:
        clauses.append("sender_name LIKE ?")
        params.append(f"%{search}%")
    if date_from:
        clauses.append("transaction_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("transaction_date <= ?")
        params.append(date_to)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM transactions {where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Transaction not found")
        return dict(row)


@router.post("/transactions")
def create_transaction(payload: TransactionCreate):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO transactions
                (batch_id, draft_slot, transaction_type, sender_name, transaction_date, transaction_time, amount, notes, status)
               VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payload.draft_slot or 1,
                payload.transaction_type or "income",
                payload.sender_name,
                payload.transaction_date,
                payload.transaction_time,
                payload.amount,
                payload.notes,
                payload.status,
            ),
        )
        transaction_id = cur.lastrowid
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        return dict(row)


@router.patch("/transactions/{transaction_id}")
def update_transaction(transaction_id: int, payload: TransactionUpdate):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "No fields to update")

    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Transaction not found")

        changed = False
        for field, new_value in updates.items():
            old_value = existing[field]
            if str(old_value) != str(new_value):
                changed = True
                conn.execute(
                    "INSERT INTO corrections (transaction_id, field, old_value, new_value) VALUES (?, ?, ?, ?)",
                    (transaction_id, field, str(old_value) if old_value is not None else None, str(new_value)),
                )

        if not changed:
            return dict(existing)

        if "status" not in updates:
            updates["status"] = "corrected"

        set_clause = ", ".join(f"{field} = ?" for field in updates)
        params = list(updates.values()) + [transaction_id]
        conn.execute(
            f"UPDATE transactions SET {set_clause}, updated_at = datetime('now', 'localtime') WHERE id = ?",
            params,
        )

        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        return dict(row)


@router.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int):
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Transaction not found")
        conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        return {"deleted": transaction_id}
