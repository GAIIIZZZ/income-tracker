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

import re
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

import pipeline
import supabase_client as db

st.set_page_config(page_title="Income Tracker (Cloud)", page_icon="\U0001f4b8", layout="wide")

# Small CSS polish on top of .streamlit/config.toml's theme - Streamlit still controls the
# underlying layout/components, this just tightens up spacing/accents a bit.
st.markdown(
    """
    <style>
    div[data-testid="stStatusWidget"] { visibility: visible; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #4f8cff; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "processed_names" not in st.session_state:
    st.session_state.processed_names = set()
if "active_slot" not in st.session_state:
    st.session_state.active_slot = 1

STATUS_OPTIONS = ["pending", "needs_review"]

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _parse_transaction_date(date_str):
    """transaction_date is stored as Buddhist Era 'YYYY-MM-DD' (per pipeline.py's prompt) -
    pandas Timestamp can't hold years past ~2262, so convert to Gregorian first or every BE
    date (2568, 2569, ...) silently becomes NaT via pd.to_datetime(errors="coerce")."""
    match = _DATE_RE.match(str(date_str or "").strip())
    if not match:
        return pd.NaT
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if year >= 2400:
        year -= 543
    try:
        return pd.Timestamp(year=year, month=month, day=day)
    except ValueError:
        return pd.NaT

st.title("Income Tracker — Cloud")
st.caption(
    "Bank slip OCR (local EasyOCR) -> AI structuring (Groq, free tier) -> Supabase. "
    "See cloud/README.md for how this differs from the fully-local version."
)

tab_upload, tab_gallery, tab_saved, tab_chart = st.tabs(
    ["Upload & Review", "Gallery", "Saved batches", "Income graph"]
)


def _process_uploaded_files(files, draft_slot):
    new_files = [f for f in (files or []) if f.name not in st.session_state.processed_names]
    if not new_files:
        return
    progress = st.progress(0.0, text="Processing slips...")
    for i, f in enumerate(new_files):
        with tempfile.NamedTemporaryFile(suffix=Path(f.name).suffix, delete=False) as tmp:
            tmp.write(f.getvalue())
            tmp_path = tmp.name

        result = pipeline.process_image(tmp_path)
        image_url = db.upload_image(f.getvalue(), f.name)
        db.insert_transaction({**result, "image_url": image_url, "batch_name": None}, draft_slot)

        st.session_state.processed_names.add(f.name)
        progress.progress((i + 1) / len(new_files), text=f"Processed {f.name}")
    progress.empty()
    st.rerun()


def _editable_table(rows, key):
    """Shows an editable table; changes are staged and only written on 'Save edits'."""
    df = pd.DataFrame(rows)[
        ["id", "sender_name", "transaction_date", "transaction_time", "amount", "status"]
    ]
    edited = st.data_editor(
        df,
        disabled=["id", "status"],
        hide_index=True,
        use_container_width=True,
        key=f"edit_{key}",
    )
    total = pd.to_numeric(edited["amount"], errors="coerce").sum()
    st.markdown(f"**Total: ฿{total:,.2f}**")
    if st.button("Save edits", key=f"save_{key}"):
        changes = 0
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
                changes += 1
        if changes:
            st.success(f"Saved {changes} edited row(s).")
            st.rerun()
        else:
            st.info("No changes to save.")


with tab_upload:
    slots = db.distinct_draft_slots()
    slot_labels = [f"Set {s}" for s in slots]
    col_tabs, col_add = st.columns([5, 1])
    with col_add:
        if st.button("+ Add another set"):
            st.session_state.active_slot = max(slots) + 1 if slots else 1
            st.rerun()

    if st.session_state.active_slot not in slots:
        slots = sorted(set(slots) | {st.session_state.active_slot})

    slot_tabs = st.tabs([f"Set {s}" for s in slots])
    for slot, slot_tab in zip(slots, slot_tabs):
        with slot_tab:
            files = st.file_uploader(
                "Drop bank slip screenshots here",
                type=["jpg", "jpeg", "png", "webp", "bmp"],
                accept_multiple_files=True,
                key=f"uploader_{slot}",
            )
            _process_uploaded_files(files, slot)

            status_filter = st.multiselect(
                "Filter by status", STATUS_OPTIONS, default=STATUS_OPTIONS, key=f"status_filter_{slot}"
            )
            current = db.list_transactions(batch_name=None, draft_slot=slot)
            current = [r for r in current if r["status"] in status_filter]

            if not current:
                st.info("Upload slips above to get started.")
            else:
                _editable_table(current, key=f"current_{slot}")

                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    batch_name = st.text_input("Batch name", placeholder="e.g. July slips", key=f"batchname_{slot}")
                with col2:
                    st.write("")
                    st.write("")
                    if st.button("Save Transactions", type="primary", disabled=not batch_name, key=f"savebatch_{slot}"):
                        db.save_batch([row["id"] for row in current], batch_name)
                        st.session_state.processed_names.clear()
                        st.success(f"Saved as '{batch_name}'")
                        st.rerun()
                with col3:
                    st.write("")
                    st.write("")
                    if st.button("Clear shown", key=f"clear_{slot}"):
                        for row in current:
                            db.delete_transaction(row["id"])
                        st.session_state.processed_names.clear()
                        st.rerun()

with tab_gallery:
    st.subheader("Gallery")
    all_rows = db.list_all_saved_transactions() + db.list_transactions(batch_name=None)
    if not all_rows:
        st.info("No processed slips yet.")
    else:
        cols = st.columns(4)
        for i, row in enumerate(all_rows):
            with cols[i % 4]:
                if row.get("image_url"):
                    st.image(row["image_url"], use_column_width=True)
                st.caption(
                    f"**{row.get('sender_name') or '—'}**\n\n"
                    f"{row.get('transaction_date') or '—'} {row.get('transaction_time') or ''}\n\n"
                    f"฿{row.get('amount') if row.get('amount') is not None else '—'}  ·  {row.get('status')}"
                )

with tab_saved:
    batches = db.list_batches()
    if not batches:
        st.info("No saved batches yet.")
    else:
        names = [b["name"] for b in batches]
        labels = [("⭐ " if b["is_favorite"] else "") + b["name"] for b in batches]
        selected_idx = st.selectbox("Batch", range(len(names)), format_func=lambda i: labels[i])
        selected = names[selected_idx]
        selected_batch = batches[selected_idx]

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            new_name = st.text_input("Rename to", value=selected, key="rename_input")
            if st.button("Rename") and new_name and new_name != selected:
                db.rename_batch(selected, new_name)
                st.rerun()
        with col2:
            fav_label = "Unfavorite" if selected_batch["is_favorite"] else "⭐ Favorite"
            if st.button(fav_label):
                db.set_batch_favorite(selected, not selected_batch["is_favorite"])
                st.rerun()
        with col3:
            if st.button("Delete batch", type="secondary"):
                db.delete_batch(selected)
                st.rerun()

        status_filter = st.multiselect("Filter by status", STATUS_OPTIONS, default=STATUS_OPTIONS, key="saved_status")
        rows = [r for r in db.list_transactions(batch_name=selected) if r["status"] in status_filter]
        st.dataframe(
            pd.DataFrame(rows)[
                ["sender_name", "transaction_date", "transaction_time", "amount", "status"]
            ] if rows else pd.DataFrame(columns=["sender_name", "transaction_date", "transaction_time", "amount", "status"]),
            use_container_width=True,
        )
        total = sum(r["amount"] for r in rows if r.get("amount") is not None)
        st.markdown(f"**Total: ฿{total:,.2f}**")

with tab_chart:
    all_rows = db.list_all_saved_transactions()
    if not all_rows:
        st.info("Save at least one batch to see the income graph.")
    else:
        chart_df = pd.DataFrame(all_rows)
        chart_df = chart_df.dropna(subset=["transaction_date", "amount"])
        chart_df["transaction_date"] = chart_df["transaction_date"].apply(_parse_transaction_date)
        chart_df = chart_df.dropna(subset=["transaction_date"])

        if chart_df.empty:
            st.info("No transactions with a valid, parseable date yet.")
        else:
            min_date, max_date = chart_df["transaction_date"].min(), chart_df["transaction_date"].max()
            date_range = st.date_input(
                "Date range", value=(min_date.date(), max_date.date()),
                min_value=min_date.date(), max_value=max_date.date(),
            )
            status_filter = st.multiselect("Status", STATUS_OPTIONS, default=STATUS_OPTIONS, key="chart_status")

            filtered = chart_df[chart_df["status"].isin(status_filter)]
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
                filtered = filtered[
                    (filtered["transaction_date"].dt.date >= start) & (filtered["transaction_date"].dt.date <= end)
                ]

            if filtered.empty:
                st.info("No data in this range/filter.")
            else:
                daily = filtered.groupby(filtered["transaction_date"].dt.date)["amount"].sum()
                st.line_chart(daily)
                st.metric("Total in range", f"฿{filtered['amount'].sum():,.2f}")
