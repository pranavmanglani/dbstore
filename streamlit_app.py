st.title("Sorry we are closed")
st.caption("Author of dbstore, pranav manglani has closed this web app due to increased storage prices and server overload, we grief for yourr inconvinience the uplooaded files are still acessible if u have there url ")


'''import streamlit as st
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


def list_all_files():
    """List objects in the bucket, including nested folders."""
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
                    "sortBy": {"column": "name", "order": "asc"}
                }
            )

            if not response:
                break

            for item in response:
                name = item.get("name", "")
                if not name or name in {".", ".."}:
                    continue

                path = f"{folder}/{name}".lstrip("/")
                metadata = item.get("metadata")

                if metadata is None and item.get("id") is None:
                    folders.append(path)
                else:
                    result.append({
                        "name": name,
                        "path": path,
                        "size": (metadata or {}).get("size")
                    })

            if len(response) < 100:
                break
            offset += len(response)

    return sorted(result, key=lambda x: x["path"].lower())


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


def make_share_url(path):
    # Preserve the current app host and HTTPS on Streamlit Community Cloud.
    host = st.context.headers.get("host", "")
    if not host:
        return None

    protocol = (
        "https"
        if host.endswith("streamlit.app")
        or st.context.headers.get("x-forwarded-proto") == "https"
        else "http"
    )

    from urllib.parse import urlencode
    return f"{protocol}://{host}/?{urlencode({'file': path})}"


# --- HEADER ---
st.title("📂 Private Cloud")
st.caption("Upload files, share preview links, and browse stored files.")

# --- FILE ROUTING ---
requested_file = st.query_params.get("file")

if requested_file:
    requested_file = str(requested_file).lstrip("/")

    try:
        # Verify that this exact path exists in the bucket.
        files = list_all_files()
        if requested_file not in {f["path"] for f in files}:
            st.error("File not found.")
            st.stop()

        st.subheader(f"📄 {os.path.basename(requested_file)}")

        with st.spinner("Loading preview..."):
            file_bytes = supabase.storage.from_(BUCKET_NAME).download(
                requested_file
            )

        preview_file(file_bytes, requested_file)

        if st.button("← Back to gallery"):
            st.query_params.clear()
            st.rerun()

    except Exception:
        st.error("Unable to open this file. Check storage permissions.")

    st.stop()


# --- UPLOADER: PRESERVED ---
st.header("⬆️ Upload a file")

uploaded_file = st.file_uploader("Choose a file", type=None)

if uploaded_file and st.button("🚀 Generate Link"):
    name = clean_filename(uploaded_file.name)

    with st.spinner("Uploading file..."):
        try:
            # Upload under a sanitized filename.
            supabase.storage.from_(BUCKET_NAME).upload(
                path=name,
                file=uploaded_file.getvalue(),
                file_options={
                    "content-type": uploaded_file.type
                    or "application/octet-stream",
                    "upsert": "true"
                }
            )

            share_url = make_share_url(name)

            # Store metadata if the optional table exists.
            if share_url:
                try:
                    supabase.table("file_shares").upsert(
                        {
                            "file_name": name,
                            "file_url": share_url
                        },
                        on_conflict="file_name"
                    ).execute()
                except Exception:
                    # Upload and link generation do not depend on this table.
                    pass

            st.success("File uploaded successfully!")

            if share_url:
                st.write("Preview link:")
                st.code(share_url)
                st.link_button("Open preview", share_url)
            else:
                st.info(
                    "Upload succeeded, but the app host was unavailable "
                    "for generating a link."
                )

        except Exception as e:
            st.error(f"Upload failed: {e}")


st.divider()

# --- GALLERY: ALL EXISTING FILES ---
st.header("🗂️ Stored Files")

col_refresh, col_count = st.columns([1, 4])

with col_refresh:
    refresh = st.button("🔄 Refresh")

try:
    with st.spinner("Loading stored files..."):
        files = list_all_files()

    if not files:
        st.info("No files found in the storage bucket yet.")
    else:
        search = st.text_input(
            "🔎 Search files",
            placeholder="Search by filename or folder..."
        )

        filtered = [
            f for f in files
            if search.lower() in f["path"].lower()
        ]

        st.caption(f"{len(filtered)} file(s) found")

        for item in filtered:
            with st.container(border=True):
                left, right = st.columns([5, 1])

                with left:
                    st.write(f"📄 **{item['name']}**")
                    st.caption(item["path"])

                with right:
                    if st.button("Open", key=f"open_{item['path']}"):
                        st.query_params["file"] = item["path"]
                        st.rerun()

except Exception as e:
    st.error(f"Unable to list files: {e}")
'''

