import os
import requests
import streamlit as st
from pathlib import Path
from datetime import datetime

# ---------------------------
# Streamlit page config
# ---------------------------
st.set_page_config(
    page_title="Telegram Uploader Bot",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📦 Advanced Telegram Uploader Bot")
st.markdown(
    """
Upload files (≤ 2 GB) or provide a direct URL.  
Files are saved locally and sent to your Telegram bot.
"""
)

# ---------------------------
# Telegram bot configuration (private use)
# ---------------------------
TELEGRAM_BOT_TOKEN = "8432820657:AAHJTUIjxEuDEb647sZq8oYVUS5sdl23zdE"
TELEGRAM_CHAT_ID = "1599595167"
SEND_DOCUMENT_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
SEND_MESSAGE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# ---------------------------
# Local storage setup
# ---------------------------
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Max file size in bytes (2 GB)
MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024 * 1024

# ---------------------------
# Helper functions
# ---------------------------
def human_size(num_bytes):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:3.1f}{unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f}PB"

def save_uploaded_file(file_obj, save_path: Path):
    with open(save_path, "wb") as f:
        f.write(file_obj.getbuffer())
    return save_path

def download_file_from_url(url: str, save_path: Path):
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return save_path

def send_file_to_telegram(file_path: Path):
    with open(file_path, "rb") as f:
        files = {"document": (file_path.name, f)}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        resp = requests.post(SEND_DOCUMENT_URL, data=data, files=files, timeout=180)
    return resp

def send_message_to_telegram(text: str):
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    return requests.post(SEND_MESSAGE_URL, data=data, timeout=60)

# ---------------------------
# Sidebar - Upload Options
# ---------------------------
st.sidebar.header("Upload Options")
uploaded_file = st.sidebar.file_uploader(
    "Upload a file (≤ 2 GB)", accept_multiple_files=False
)
file_url = st.sidebar.text_input("Or provide a file URL")
custom_name = st.sidebar.text_input("Optional filename override")

# ---------------------------
# Main Action
# ---------------------------
if st.sidebar.button("Upload & Send"):
    if not uploaded_file and not file_url:
        st.error("Please upload a file or provide a URL.")
    else:
        try:
            if uploaded_file:
                filename = custom_name or uploaded_file.name
                save_path = UPLOAD_DIR / filename
                save_uploaded_file(uploaded_file, save_path)
            else:
                filename_from_url = custom_name or file_url.split("/")[-1].split("?")[0] or "downloaded_file"
                save_path = UPLOAD_DIR / filename_from_url
                with st.spinner("Downloading file from URL..."):
                    download_file_from_url(file_url, save_path)

            file_size = save_path.stat().st_size
            st.success(f"Saved {save_path.name} ({human_size(file_size)}) locally.")

            if file_size > MAX_UPLOAD_SIZE_BYTES:
                st.warning(f"File exceeds Telegram’s 2 GB limit. Sending info message instead.")
                msg = f"📦 File saved locally: {save_path.name} ({human_size(file_size)})"
                send_message_to_telegram(msg)
            else:
                with st.spinner("Sending file to Telegram..."):
                    resp = send_file_to_telegram(save_path)
                if resp.ok and resp.json().get("ok"):
                    st.success("✅ File sent successfully to Telegram!")
                else:
                    st.error(f"❌ Telegram upload failed: {resp.text}")
        except Exception as e:
            st.exception(e)

# ---------------------------
# Display uploaded files
# ---------------------------
st.markdown("---")
st.subheader("📂 Uploaded Files (Local Storage)")

files = sorted(UPLOAD_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
if files:
    for f in files:
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.write(f"{f.name} — {human_size(f.stat().st_size)} — {datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        with col2:
            if st.button(f"Send {f.name}", key=f"send_{f.name}"):
                try:
                    resp = send_file_to_telegram(f)
                    if resp.ok and resp.json().get("ok"):
                        st.success(f"Sent {f.name} to Telegram!")
                    else:
                        st.error(f"Failed to send {f.name}: {resp.text}")
                except Exception as e:
                    st.error(str(e))
        with col3:
            with open(f, "rb") as fh:
                st.download_button(f"Download", data=fh, file_name=f.name)
else:
    st.write("No files uploaded yet.")
