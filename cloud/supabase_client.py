"""Thin wrapper around the Supabase Python client - all DB + image storage calls for the
Streamlit cloud alt live here. Mirrors what backend/app/db.py + upload.py do locally with
SQLite + local folders, but against Supabase's free-tier Postgres + Storage instead.
"""

import os
import uuid

import streamlit as st
from supabase import create_client

TRANSACTIONS = "transactions"
BATCHES = "batches"
BUCKET = "slip-images"


@st.cache_resource
def get_client():
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_KEY not set. Add them to .streamlit/secrets.toml (local) "
            "or the app's Secrets settings (Streamlit Community Cloud)."
        )
    return create_client(url, key)


def upload_image(file_bytes: bytes, filename: str) -> str:
    """Uploads to the 'slip-images' Storage bucket, returns its public URL."""
    client = get_client()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    storage_path = f"{uuid.uuid4().hex}.{ext}"
    client.storage.from_(BUCKET).upload(
        storage_path, file_bytes, {"content-type": f"image/{ext}"}
    )
    return client.storage.from_(BUCKET).get_public_url(storage_path)


def insert_transaction(record: dict, draft_slot: int = 1) -> dict:
    client = get_client()
    result = client.table(TRANSACTIONS).insert({**record, "draft_slot": draft_slot}).execute()
    return result.data[0]


def update_transaction(transaction_id: int, fields: dict) -> None:
    client = get_client()
    client.table(TRANSACTIONS).update(fields).eq("id", transaction_id).execute()


def delete_transaction(transaction_id: int) -> None:
    client = get_client()
    client.table(TRANSACTIONS).delete().eq("id", transaction_id).execute()


def list_transactions(batch_name: str | None, draft_slot: int | None = None, status: str | None = None) -> list[dict]:
    client = get_client()
    query = client.table(TRANSACTIONS).select("*").order("created_at", desc=True)
    if batch_name is None:
        query = query.is_("batch_name", "null")
    else:
        query = query.eq("batch_name", batch_name)
    if draft_slot is not None:
        query = query.eq("draft_slot", draft_slot)
    if status is not None:
        query = query.eq("status", status)
    return query.execute().data


def distinct_draft_slots() -> list[int]:
    """Draft slots currently in use among unsaved (batch_name is null) transactions."""
    client = get_client()
    result = (
        client.table(TRANSACTIONS)
        .select("draft_slot")
        .is_("batch_name", "null")
        .execute()
    )
    slots = {row["draft_slot"] for row in result.data}
    return sorted(slots) or [1]


# --- Batches -----------------------------------------------------------------

def save_batch(transaction_ids: list[int], batch_name: str) -> None:
    client = get_client()
    client.table(BATCHES).upsert({"name": batch_name}).execute()
    client.table(TRANSACTIONS).update({"batch_name": batch_name}).in_("id", transaction_ids).execute()


def list_batches() -> list[dict]:
    """Returns batches sorted favorites-first, then newest first."""
    client = get_client()
    result = (
        client.table(BATCHES)
        .select("*")
        .order("is_favorite", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def rename_batch(old_name: str, new_name: str) -> None:
    client = get_client()
    client.table(BATCHES).update({"name": new_name}).eq("name", old_name).execute()
    client.table(TRANSACTIONS).update({"batch_name": new_name}).eq("batch_name", old_name).execute()


def set_batch_favorite(name: str, is_favorite: bool) -> None:
    client = get_client()
    client.table(BATCHES).update({"is_favorite": is_favorite}).eq("name", name).execute()


def delete_batch(name: str) -> None:
    """Deletes the batch and all its transactions (+ their images stay in Storage, harmless)."""
    client = get_client()
    client.table(TRANSACTIONS).delete().eq("batch_name", name).execute()
    client.table(BATCHES).delete().eq("name", name).execute()


def list_all_saved_transactions() -> list[dict]:
    client = get_client()
    result = (
        client.table(TRANSACTIONS)
        .select("*")
        .not_.is_("batch_name", "null")
        .execute()
    )
    return result.data
