"""Thin wrapper around the Supabase Python client - all DB + image storage calls for the
Streamlit cloud alt live here. Mirrors what backend/app/db.py + upload.py do locally with
SQLite + local folders, but against Supabase's free-tier Postgres + Storage instead.
"""

import os
import uuid

import streamlit as st
from supabase import create_client

TABLE = "transactions"
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


def insert_transaction(record: dict) -> dict:
    client = get_client()
    result = client.table(TABLE).insert(record).execute()
    return result.data[0]


def update_transaction(transaction_id: int, fields: dict) -> None:
    client = get_client()
    client.table(TABLE).update(fields).eq("id", transaction_id).execute()


def list_batch_names() -> list[str]:
    client = get_client()
    result = (
        client.table(TABLE)
        .select("batch_name")
        .not_.is_("batch_name", "null")
        .execute()
    )
    return sorted({row["batch_name"] for row in result.data})


def list_transactions(batch_name: str | None) -> list[dict]:
    client = get_client()
    query = client.table(TABLE).select("*").order("created_at", desc=True)
    if batch_name is None:
        query = query.is_("batch_name", "null")
    else:
        query = query.eq("batch_name", batch_name)
    return query.execute().data


def save_batch(transaction_ids: list[int], batch_name: str) -> None:
    client = get_client()
    client.table(TABLE).update({"batch_name": batch_name}).in_("id", transaction_ids).execute()


def delete_transaction(transaction_id: int) -> None:
    client = get_client()
    client.table(TABLE).delete().eq("id", transaction_id).execute()
