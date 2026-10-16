
import streamlit as st
import os
import io
import base64
import zipfile
import pandas as pd
from supabase import create_client

st.set_page_config(
    page_title="DBStore — Closed",
    page_icon="📁",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
BUCKET_NAME = st.secrets.get("BUCKET_NAME", "uploads")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FILE PREVIEW ---
def preview_file(data, filename):
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        encoded = base64.b64encode(data).decode("ascii")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{encoded}" '
            'width="100%" height="700" style="border:0"></iframe>',
            unsafe_allow_html=True
        )

    elif ext in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        st.image(data, use_container_width=True)

    elif ext in {".csv", ".xlsx"}:
        try:
            df = (
                pd.read_csv(io.BytesIO(data))
                if ext == ".csv"
                else pd.read_excel(io.BytesIO(data))
            )
            st.dataframe(df, use_container_width=True)
        except Exception:
            st.error("Unable to preview this file.")

    elif ext == ".zip":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = [
                    name for name in archive.namelist()
                    if not name.endswith("/")
                ]

                if not names:
                    st.info("This archive is empty.")
                    return

                selected = st.selectbox("Choose a file to view", names)

                allowed = {
                    ".txt", ".md", ".json", ".csv", ".html",
                    ".css", ".js", ".py", ".xml", ".log"
                }

                if os.path.splitext(selected)[1].lower() in allowed:
                    st.code(
                        archive.read(selected).decode(
                            "utf-8", errors="replace"
                        )
                    )
                else:
                    st.info("Preview unavailable for this file type.")
        except (zipfile.BadZipFile, OSError):
            st.error("Unable to read this archive.")

    elif ext in {
        ".txt", ".md", ".json", ".html", ".css",
        ".js", ".py", ".xml", ".log"
    }:
        st.code(data.decode("utf-8", errors="replace"))

    else:
        st.info("Preview unavailable for this file type.")


# --- URL ROUTING ---
file_path = st.query_params.get("file")

if file_path:
    file_path = str(file_path).lstrip("/")

    # Reject suspicious paths.
    if (
        not file_path
        or ".." in file_path.split("/")
        or "\\" in file_path
    ):
        st.error("Invalid file URL.")
        st.stop()

    try:
        with st.spinner("Opening file..."):
            data = supabase.storage.from_(BUCKET_NAME).download(
                file_path
            )

        st.title(os.path.basename(file_path))
        preview_file(data, file_path)

    except Exception:
        st.error(
            "This file could not be opened. "
            "It may have been removed or the link may be invalid."
        )

    st.stop()


# --- CLOSED HOMEPAGE ---
st.title("Sorry, we are closed")

st.caption(
    "The author of DBStore, Pranav Manglani, has closed this web "
    "app due to increased storage costs and server overload. "
    "We regret the inconvenience. Previously uploaded files may "
    "still be accessible if you have their URLs."
)
