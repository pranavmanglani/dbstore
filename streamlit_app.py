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

st.set_page_config(page_title="Cloud Drive Share", layout="wide")

# --- UTILS ---
def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9.-]', '_', name)

def get_viewer_link(filename):
    # This creates the link that points back to YOUR Streamlit app
    base_url = "https://your-app-url.streamlit.app" # UPDATE THIS after you deploy
    return f"{base_url}/?file={filename}"

def preview_file(file_data, filename, mime_type):
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == ".pdf":
        base64_pdf = base64.b64encode(file_data).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    elif ext in [".png", ".jpg", ".jpeg", ".gif"]:
        st.image(file_data)
    elif ext in [".csv", ".xlsx"]:
        df = pd.read_csv(io.BytesIO(file_data)) if ext == ".csv" else pd.read_excel(io.BytesIO(file_data))
        st.dataframe(df)
    else:
        try:
            st.code(file_data.decode(errors='ignore'))
        except:
            st.info("No preview available for this file type.")

# --- ROUTING LOGIC (The "Google Drive" Part) ---
query_params = st.query_params
if "file" in query_params:
    target_file = query_params["file"]
    st.title(f"📥 Download: {target_file}")
    
    try:
        # Fetch file from Supabase
        file_bytes = supabase.storage.from_(BUCKET_NAME).download(target_file)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.download_button(label="💾 Download Now", data=file_bytes, file_name=target_file)
            if st.button("⬅️ Upload New File"):
                st.query_params.clear()
                st.rerun()
        
        with col2:
            st.subheader("Preview")
            preview_file(file_bytes, target_file, "application/octet-stream")
            
    except Exception as e:
        st.error("File not found or link expired.")
    st.stop() # Prevents the rest of the app from loading if viewing a specific file

# --- MAIN UPLOAD UI ---
st.title("📂 All-in-One Permanent Share")
uploaded_file = st.file_uploader("Upload a file to get a permanent share link", type=None)

if uploaded_file:
    if st.button("🚀 Generate Share Link"):
        with st.spinner("Processing..."):
            name = clean_filename(uploaded_file.name)
            # Upload to Supabase
            supabase.storage.from_(BUCKET_NAME).upload(path=name, file=uploaded_file.getvalue(), file_options={"upsert": "true"})
            
            # Save to Table
            share_link = get_viewer_link(name)
            supabase.table("file_shares").upsert({"file_name": name, "file_url": share_link}).execute()
            
            st.success("Link Created!")
            st.code(share_link)
            st.info("Anyone with this link can now download or preview this file on this site.")

# History Tab
st.divider()
st.subheader("📜 Recent Uploads")
res = supabase.table("file_shares").select("*").order("created_at", desc=True).limit(10).execute()
if res.data:
    for item in res.data:
        st.write(f"🔗 {item['file_name']} — [View/Download]({item['file_url']})")
        
