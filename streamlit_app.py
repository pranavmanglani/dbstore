import streamlit as st
import pandas as pd
import zipfile
import io
import os
import re
import base64
from supabase import create_client

# --- SUPABASE CONFIG ---
SUPABASE_URL = "https://tkmdbsrlybwluwnkqoxl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRrbWRic3JseWJ3bHV3bmtxb3hsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzOTUzMDUsImV4cCI6MjA4NDk3MTMwNX0.e15bef7tr20Zc5RqY5sopOC-oJYAFEqk9i52OlJsFHw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "uploads"

st.set_page_config(page_title="Private Cloud Link", layout="wide")

def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9.-]', '_', name)

def preview_file(file_data, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        base64_pdf = base64.b64encode(file_data).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    elif ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        st.image(file_data)
    elif ext in [".csv", ".xlsx"]:
        df = pd.read_csv(io.BytesIO(file_data)) if ext == ".csv" else pd.read_excel(io.BytesIO(file_data))
        st.dataframe(df, use_container_width=True)
    elif ext == ".zip":
        with zipfile.ZipFile(io.BytesIO(file_data)) as z:
            files = z.namelist()
            selected = st.selectbox("Files in ZIP:", files)
            if st.button("Unzip & View"):
                with z.open(selected) as f:
                    try:
                        st.code(f.read().decode())
                    except:
                        st.write("Cannot preview this format as text.")
    else:
        try:
            st.code(file_data.decode(errors='ignore'))
        except:
            st.info("No preview available.")

# --- ROUTING ---
params = st.query_params
if "file" in params:
    file_id = params["file"]
    st.title(f"📥 {file_id}")
    try:
        file_bytes = supabase.storage.from_(BUCKET_NAME).download(file_id)
        col1, col2 = st.columns([1, 4])
        with col1:
            st.download_button("💾 Download", file_bytes, file_name=file_id)
            if st.button("➕ Upload New"):
                st.query_params.clear()
                st.rerun()
        with col2:
            preview_file(file_bytes, file_id)
    except:
        st.error("File not found.")
    st.stop()

# --- PRIVATE UPLOADER ---
st.title("📂 Private Link Generator")
uploaded_file = st.file_uploader("Upload", type=None)

if uploaded_file:
    if st.button("🚀 Generate Link"):
        with st.spinner("Uploading..."):
            name = clean_filename(uploaded_file.name)
            try:
                # FIX: Stringify headers, keep 'upsert' logic clean
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=name, 
                    file=uploaded_file.getvalue(), 
                    file_options={
                        "x-upsert": "true", # Using the header string variant
                        "content-type": str(uploaded_file.type)
                    }
                )
                
                host = st.context.headers.get("host")
                protocol = "https" if "streamlit.app" in host else "http"
                share_url = f"{protocol}://{host}/?file={name}"
                
                # Save metadata
                supabase.table("file_shares").upsert({"file_name": name, "file_url": share_url}).execute()
                
                st.success("Private Link Created!")
                st.code(share_url)
            except Exception as e:
                st.error(f"Error: {e}")
