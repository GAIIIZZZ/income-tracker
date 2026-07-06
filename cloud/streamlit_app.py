"""Income Tracker - cloud alternative.

Same idea as the local app (OCR bank slips -> AI-structure -> review -> track income) but
built to run for free on Streamlit Community Cloud, using Supabase (Postgres + Storage)
instead of local SQLite/folders, and Groq's free hosted LLM API instead of local Ollama
(a free host has no way to run Ollama itself). OCR (EasyOCR) still runs locally to the
server process - it's the LLM step (Ollama specifically) that can't be self-hosted for free.

Known limitation vs. the local app: no Zone Profile calibration tool here (that's a custom
canvas-drawing UI that doesn't have a simple Streamlit equivalent) - extraction relies on
OCR + the LLM prompt only. See cloud/README.md for setup and deploy steps.
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

import pipeline
import supabase_client as db

st.set_page_config(page_title="Income Tracker (Cloud)", page_icon="\U0001f4b8", layout="wide")

if "processed_names" not in st.session_state:
    st.session_state.processed_names = set()

st.title("Income Tracker — Cloud")
st.caption(
    "Bank slip OCR (local EasyOCR) -> AI structuring (Groq, free tier) -> Supabase. "
    "See cloud/README.md for how this differs from the fully-local version."
)

tab_upload, tab_saved, tab_chart = st.tabs(["Upload & Review", "Saved batches", "Income graph"])

with tab_upload:
    files = st.file_uploader(
        "Drop bank slip screenshots here",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        accept_multiple_files=True,
    )

    new_files = [f for f in (files or []) if f.name not in st.session_state.processed_names]
    if new_files:
        progress = st.progress(0.0, text="Processing slips...")
        for i, f in enumerate(new_files):
            with tempfile.NamedTemporaryFile(suffix=Path(f.name).suffix, delete=False) as tmp:
                tmp.write(f.getvalue())
                tmp_path = tmp.name

            result = pipeline.process_image(tmp_path)
            image_url = db.upload_image(f.getvalue(), f.name)
            db.insert_transaction({**result, "image_url": image_url, "batch_name": None})

            st.session_state.processed_names.add(f.name)
            progress.progress((i + 1) / len(new_files), text=f"Processed {f.name}")
        progress.empty()
        st.rerun()

    st.subheader("Current (unsaved)")
    current = db.list_transactions(batch_name=None)
    if not current:
        st.info("Upload slips above to get started.")
    else:
        df = pd.DataFrame(current)[
            ["id", "sender_name", "transaction_date", "transaction_time", "amount", "status"]
        ]
        edited = st.data_editor(
            df, disabled=["id", "status"], hide_index=True, use_container_width=True, key="edit_current"
        )
        for _, row in edited.iterrows():
            original = df[df["id"] == row["id"]].iloc[0]
            if not row.equals(original):
                db.update_transaction(
                    row["id"],
                    {
                        "sender_name": row["sender_name"],
                        "transaction_date": row["transaction_date"],
                        "transaction_time": row["transaction_time"],
                        "amount": row["amount"],
                    },
                )

        col1, col2 = st.columns([3, 1])
        with col1:
            batch_name = st.text_input("Batch name", placeholder="e.g. July slips")
        with col2:
            st.write("")
            st.write("")
            if st.button("Save Transactions", type="primary", disabled=not batch_name):
                db.save_batch([row["id"] for row in current], batch_name)
                st.session_state.processed_names.clear()
                st.success(f"Saved as '{batch_name}'")
                st.rerun()

        if st.button("Clear shown"):
            for row in current:
                db.delete_transaction(row["id"])
            st.session_state.processed_names.clear()
            st.rerun()

with tab_saved:
    batch_names = db.list_batch_names()
    if not batch_names:
        st.info("No saved batches yet.")
    else:
        selected = st.selectbox("Batch", batch_names)
        rows = db.list_transactions(batch_name=selected)
        st.dataframe(
            pd.DataFrame(rows)[
                ["sender_name", "transaction_date", "transaction_time", "amount", "status"]
            ],
            use_container_width=True,
        )

with tab_chart:
    all_names = db.list_batch_names()
    all_rows = []
    for name in all_names:
        all_rows.extend(db.list_transactions(batch_name=name))
    if not all_rows:
        st.info("Save at least one batch to see the income graph.")
    else:
        chart_df = pd.DataFrame(all_rows)
        chart_df = chart_df.dropna(subset=["transaction_date", "amount"])
        chart_df["transaction_date"] = pd.to_datetime(chart_df["transaction_date"], errors="coerce")
        daily = chart_df.groupby(chart_df["transaction_date"].dt.date)["amount"].sum()
        st.line_chart(daily)
