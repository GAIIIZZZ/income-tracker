from typing import Optional

from fastapi import APIRouter, HTTPException

from ..db import get_conn

router = APIRouter()

# transaction_date is stored in Buddhist Era (พ.ศ.). created_at is a real system timestamp
# (Gregorian), so when transaction_date is missing we synthesize a BE-equivalent string from
# it, keeping every date in this endpoint on the same era for consistent grouping/filtering.
BE_DATE_EXPR = (
    "COALESCE(transaction_date, "
    "(CAST(strftime('%Y', created_at) AS INTEGER) + 543) || '-' || strftime('%m-%d', created_at))"
)

PERIOD_EXPR = {
    "day": BE_DATE_EXPR,
    "month": f"substr({BE_DATE_EXPR}, 1, 7)",
    "year": f"substr({BE_DATE_EXPR}, 1, 4)",
}


@router.get("/income-summary")
def income_summary(
    period: str = "month",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type: str = "income",
):
    if period not in PERIOD_EXPR:
        raise HTTPException(400, f"invalid period, must be one of {list(PERIOD_EXPR)}")

    clauses = ["amount IS NOT NULL", "transaction_type = ?"]
    params: list = [type]
    if date_from:
        clauses.append(f"({BE_DATE_EXPR}) >= ?")
        params.append(date_from)
    if date_to:
        clauses.append(f"({BE_DATE_EXPR}) <= ?")
        params.append(date_to)
    where = " AND ".join(clauses)

    query = f"""
        SELECT {PERIOD_EXPR[period]} as period,
               SUM(CASE WHEN status = 'corrected' THEN amount ELSE 0 END) as correct,
               SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END) as pending,
               SUM(CASE WHEN status = 'needs_review' THEN amount ELSE 0 END) as needs_review,
               SUM(amount) as all_total,
               COUNT(*) as count
        FROM transactions
        WHERE {where}
        GROUP BY period
        HAVING period IS NOT NULL
        ORDER BY period
    """
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
