import streamlit as st
import pandas as pd
import zipfile
import io
import os
from supabase import create_client

# --- SUPABASE CONFIG ---
SUPABASE_URL = "https://tkmdbsrlybwluwnkqoxl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRrbWRic3JseWJ3bHV3bmtxb3hsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzOTUzMDUsImV4cCI6MjA4NDk3MTMwNX0.e15bef7tr20Zc5RqY5sopOC-oJYAFEqk9i52OlJsFHw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "uploads"

st.set_page_config(page_title="Permanent File Share", layout="wide")

## --- HELPER FUNCTIONS ---
def get_public_url(file_path):
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_path}"

def upload_to_supabase(file):
    # Upload file to storage
    file_bytes = file.getvalue()
    supabase.storage.from_(BUCKET_NAME).upload(file.name, file_bytes, {"upsert": "true"})
    
    # Save metadata to DB
    public_url = get_public_url(file.name)
    supabase.table("file_shares").insert({
        "file_name": file.name,
        "file_url": public_url,
        "file_type": file.type
    }).execute()
    return public_url

## --- UI INTERFACE ---
st.title("📂 All-in-One Permanent Share")

tab1, tab2 = st.tabs(["Upload & Preview", "Shared History"])

with tab1:
    uploaded_file = st.file_uploader("Upload any file", type=None)

    if uploaded_file:
        if st.button("🚀 Upload & Generate Permanent Link"):
            with st.spinner("Uploading..."):
                url = upload_to_supabase(uploaded_file)
                st.success(f"File uploaded! Permanent Link: {url}")
                st.code(url)

        # --- UNIVERSAL OPENER LOGIC ---
        st.divider()
        st.subheader("👀 File Preview")
        ext = os.path.splitext(uploaded_file.name)[1].lower()

        if ext == ".zip":
            with zipfile.ZipFile(uploaded_file) as z:
                st.write("Contents of ZIP:", z.namelist())
                sub_file = st.selectbox("Select file inside ZIP to open", z.namelist())
                if st.button("Unzip & View"):
                    with z.open(sub_file) as f:
                        st.text(f.read().decode(errors='ignore'))

        elif ext in [".csv", ".xlsx", ".xls"]:
            df = pd.read_csv(uploaded_file) if ext == ".csv" else pd.read_excel(uploaded_file)
            st.dataframe(df)

        elif ext in [".txt", ".json", ".py", ".md"]:
            st.text(uploaded_file.getvalue().decode())

        elif ext in [".png", ".jpg", ".jpeg"]:
            st.image(uploaded_file)
        
        else:
            st.warning("Preview not supported for this format, but the link will work!")

with tab2:
    st.subheader("🔗 All Permanent Links")
    res = supabase.table("file_shares").select("*").order("created_at", desc=True).execute()
    if res.data:
        df_history = pd.DataFrame(res.data)
        st.table(df_history[["file_name", "file_url", "created_at"]])
    else:
        st.write("No files shared yet.")
