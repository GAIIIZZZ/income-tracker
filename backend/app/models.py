from typing import Optional

from pydantic import BaseModel


class TransactionOut(BaseModel):
    id: int
    batch_id: Optional[int] = None
    source_image_path: Optional[str] = None
    processed_image_path: Optional[str] = None
    sender_name: Optional[str] = None
    transaction_date: Optional[str] = None
    transaction_time: Optional[str] = None
    amount: Optional[float] = None
    notes: Optional[str] = None
    raw_ocr_text: Optional[str] = None
    llm_raw_response: Optional[str] = None
    confidence: Optional[float] = None
    status: str
    recheck_status: Optional[str] = None
    recheck_note: Optional[str] = None
    created_at: str
    updated_at: str


class TransactionUpdate(BaseModel):
    sender_name: Optional[str] = None
    transaction_date: Optional[str] = None
    transaction_time: Optional[str] = None
    amount: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class TransactionCreate(BaseModel):
    sender_name: Optional[str] = None
    transaction_date: Optional[str] = None
    transaction_time: Optional[str] = None
    amount: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = "corrected"
    draft_slot: Optional[int] = 1


class BatchCreate(BaseModel):
    name: Optional[str] = None
    is_favorite: Optional[bool] = None
    draft_slot: Optional[int] = 1


class BatchOut(BaseModel):
    id: int
    name: str
    is_favorite: bool
    created_at: str
    last_edited: Optional[str] = None
    count: int
    total: float
