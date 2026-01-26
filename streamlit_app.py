import streamlit as st
from supabase import create_client

# --- CREDENTIALS ---
URL = "https://bsrvgmcvdckqveggganc.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJzcnZnbWN2ZGNrcXZlZ2dnYW5jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk0MTU2NTQsImV4cCI6MjA4NDk3MTY1NH0.PPwzd06bYw4DEBLTCGB2jBWr9xDtfLSdrqjZNv9yasw"
supabase = create_client(URL, KEY)

st.set_page_config(page_title="OS Remote Control", layout="wide")

st.title("🖥️ Home Server Controller")

# Simple Auth
password = st.sidebar.text_input("Access Key", type="password")
if password != "admin": # CHANGE THIS
    st.warning("Enter key to access.")
    st.stop()

# Helper to send commands
def send_cmd(type, payload=""):
    try:
        supabase.table("remote_commands").insert({
            "command_type": type,
            "command_payload": payload,
            "status": "pending"
        }).execute()
        st.success(f"Sent: {type}")
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- UI CONTROLS ---
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📸 Screenshot"):
        send_cmd("screenshot")
with col2:
    if st.button("🔔 Ping PC"):
        send_cmd("terminal", "echo 'Ping from Web'")
with col3:
    if st.button("📁 List Root"):
        send_cmd("terminal", "dir" if st.sidebar.checkbox("Windows", True) else "ls")

st.divider()

# Custom Terminal
cmd_input = st.text_input("Remote Terminal (Type any CMD command)")
if st.button("Execute"):
    if cmd_input:
        send_cmd("terminal", cmd_input)

st.divider()

# --- LOGS / HISTORY ---
st.subheader("📜 Execution Logs")
try:
    res = supabase.table("remote_commands").select("*").order("created_at", desc=True).limit(5).execute()
    if res.data:
        for l in res.data:
            with st.expander(f"{l['command_type']} - {l['status']} ({l['created_at']})"):
                st.text("Payload: " + str(l['command_payload']))
                st.code(l['output'] if l['output'] else "Waiting for Agent...")
                if st.button(f"Delete Log {l['id']}", key=f"del_{l['id']}"):
                    supabase.table("remote_commands").delete().eq("id", l['id']).execute()
                    st.rerun()
    else:
        st.info("No commands found in history.")
except Exception as e:
    st.error("Error reading logs. Make sure you ran the SQL script in Supabase.")
