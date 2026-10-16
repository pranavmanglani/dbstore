import streamlit as st

st.title("Sorry we are closed")
st.caption("Author of dbstore, pranav manglani has closed this web app due to increased storage prices and server overload, we grief for yourr inconvinience the uplooaded files are still acessible if u have there url ")


import streamlit as st
import pandas as pd
import zipfile
import io
import os
import re
import base64
from supabase import create_client

# --- CONFIG ---
st.set_page_config(
    page_title="Private Cloud",
    page_icon="📂",
    layout="wide"
)


# Discourage right-click and common save shortcuts.
# This is a deterrent, not a security boundary.
st.markdown("""
<script>
(function () {
  document.addEventListener('contextmenu', function (e) {
    if (e.target.closest('.gallery-protected')) {
      e.preventDefault();
    }
  }, true);

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) &&
        ['s', 'u'].includes(e.key.toLowerCase())) {
      e.preventDefault();
    }
  }, true);
})();
</script>
""", unsafe_allow_html=True)


SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
BUCKET_NAME = st.secrets.get("BUCKET_NAME", "uploads")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def clean_filename(name):
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


def preview_file(data, filename):
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        encoded = base64.b64encode(data).decode("ascii")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{encoded}" '
            'width="100%" height="650" style="border:0"></iframe>',
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
            st.error("Unable to preview this spreadsheet.")

    elif ext == ".zip":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = [
                    n for n in archive.namelist()
                    if not n.endswith("/")
                ]

                if not names:
                    st.info("This ZIP archive is empty.")
                    return

                selected = st.selectbox(
                    "Files inside archive",
                    names,
                    key=f"zip_{filename}"
                )

                if st.button("Preview selected file"):
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
                        st.info("Preview is unavailable for this file type.")
        except (zipfile.BadZipFile, OSError):
            st.error("Unable to read this ZIP archive.")

    elif ext in {
        ".txt", ".md", ".json", ".html", ".css",
        ".js", ".py", ".xml", ".log"
    }:
        st.code(data.decode("utf-8", errors="replace"))

    else:
        st.info("No inline preview is available for this file type.")
