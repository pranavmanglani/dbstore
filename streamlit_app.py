
import streamlit as st
import pandas as pd
import zipfile
import io
import os
import re
from supabase import create_client

st.set_page_config(
    page_title="Private Cloud Gallery",
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


# --- SERVER-SIDE SUPABASE CONFIG ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
BUCKET_NAME = st.secrets.get("BUCKET_NAME", "uploads")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def clean_filename(name):
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


def list_all_files():
    """List files in the bucket, including nested folders."""
    result = []
    folders = [""]
    visited = set()

    while folders:
        folder = folders.pop()

        if folder in visited:
            continue
        visited.add(folder)

        offset = 0
        while True:
            response = supabase.storage.from_(BUCKET_NAME).list(
                folder,
                {
                    "limit": 100,
                    "offset": offset,
                    "sortBy": {
                        "column": "name",
                        "order": "asc"
                    }
                }
            )

            if not response:
                break

            for item in response:
                name = item.get("name", "")
                if not name:
                    continue

                path = f"{folder}/{name}".lstrip("/")

                # Folders usually have no file ID; files have metadata.
                if item.get("id") is None and item.get("metadata") is None:
                    folders.append(path)
                else:
                    result.append({
                        "name": name,
                        "path": path,
                        "size": (item.get("metadata") or {}).get("size")
                    })

            if len(response) < 100:
                break

            offset += len(response)

    return sorted(result, key=lambda f: f["path"].lower())


def preview_file(data, filename):
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        # Inline preview only; this does not prevent saving the PDF.
        import base64

        encoded = base64.b64encode(data).decode("ascii")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{encoded}" '
            'width="100%" height="700" '
            'style="border:0"></iframe>',
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

                if names:
                    selected = st.selectbox(
                        "Choose a file to preview",
                        names,
                        key=f"zip_{filename}"
                    )

                    # Only display text-like files.
                    if st.button("Preview selected file"):
                        if os.path.splitext(selected)[1].lower() in {
                            ".txt", ".md", ".json", ".csv",
                            ".html", ".css", ".js", ".py", ".xml"
                        }:
                            content = archive.read(selected)
                            st.code(
                                content.decode("utf-8", errors="replace")
                            )
                        else:
                            st.info(
                                "This file type is not supported "
                                "for ZIP preview."
                            )
                else:
                    st.info("This ZIP archive contains no files.")
        except (zipfile.BadZipFile, OSError):
            st.error("Unable to read this ZIP archive.")

    elif ext in {".txt", ".md", ".json", ".html", ".css",
                 ".js", ".py", ".xml", ".log"}:
        st.code(data.decode("utf-8", errors="replace"))

    else:
        st.info(
            "No inline preview is available for this file type."
        )


# --- HEADER ---
st.title("📂 Private Cloud Gallery")
st.caption("Browse and preview files stored in the cloud.")

# --- OPEN A FILE ---
params = st.query_params
requested_file = params.get("file")

if requested_file:
    requested_file = str(requested_file).lstrip("/")

    # Check that the requested path exists in the bucket.
    try:
        files = list_all_files()
        known_paths = {item["path"] for item in files}

        if requested_file not in known_paths:
            st.error("File not found.")
            st.stop()

        st.subheader(os.path.basename(requested_file))

        with st.spinner("Loading preview..."):
            data = supabase.storage.from_(BUCKET_NAME).download(
                requested_file
            )

        preview_file(data, requested_file)

        if st.button("← Back to gallery"):
            st.query_params.clear()
            st.rerun()

    except Exception:
        st.error("Unable to open this file. Check the storage permissions.")

    st.stop()


# --- PUBLIC GALLERY ---
try:
    with st.spinner("Loading files..."):
        files = list_all_files()

    if not files:
        st.info("No files found in the storage bucket.")
        st.stop()

    search = st.text_input(
        "🔎 Search files",
        placeholder="Search by filename or folder..."
    )

    filtered = [
        item for item in files
        if search.lower() in item["path"].lower()
    ]

    st.caption(f"{len(filtered)} file(s)")

    for item in filtered:
        with st.container(border=True):
            col1, col2 = st.columns([5, 1])

            with col1:
                st.write("📄 **" + item["name"] + "**")
                st.caption(item["path"])

            with col2:
                if st.button(
                    "Open",
                    key="open_" + item["path"]
                ):
                    st.query_params["file"] = item["path"]
                    st.rerun()

except Exception:
    st.error(
        "Unable to list files. Verify the bucket name, "
        "server-side key and Storage permissions."
    )
