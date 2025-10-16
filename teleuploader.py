import os
import requests
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Streamlit & app configuration
# -------------------------------------------------------------------
# ⚠️ Do NOT set st.set_option("server.maxUploadSize") here
# Set via CLI: --server.maxUploadSize=5000
st.title("Advanced Streamlit Uploader → Telegram Bot (5 GB Limit)")
st.write(
    "Upload a file or provide a URL. Files up to 5 GB are saved locally. "
    "Telegram only allows uploads ≤ 2 GB, so larger files will send as links instead."
)

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    st.warning("⚠️ Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in a .env file or environment variables.")
    st.stop()

# Telegram API endpoints
SEND_DOCUMENT_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
SEND_MESSAGE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Local upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Telegram’s official file size limit for bots
TELEGRAM_MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB in bytes

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def save_uploaded_file(streamlit_file, save_path: Path):
    with open(save_path, "wb") as f:
        f.write(streamlit_file.getbuffer())
    return save_path

def download_url_to_file(url: str, save_path: Path):
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

def human_size(num_bytes):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:3.1f}{unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f}PB"

# -------------------------------------------------------------------
# UI: Upload or URL
# -------------------------------------------------------------------
uploaded_file = st.file_uploader("Choose a file to upload (≤ 5 GB)", accept_multiple_files=False)
st.write("---")
st.subheader("Or provide a direct file URL")
file_url = st.text_input("File URL (http/https)")
custom_name = st.text_input("Optional: Save as (filename.ext)")

if st.button("Save and Send to Telegram"):
    if not uploaded_file and not file_url:
        st.error("Please upload a file or provide a URL.")
    else:
        try:
            # Determine filename and save
            if uploaded_file:
                name = custom_name or uploaded_file.name
                save_path = UPLOAD_DIR / name
                save_uploaded_file(uploaded_file, save_path)
                st.success(f"Saved {name} locally.")
            else:
                url_name = custom_name or file_url.split("/")[-1].split("?")[0] or "downloaded_file"
                save_path = UPLOAD_DIR / url_name
                with st.spinner("Downloading file..."):
                    download_url_to_file(file_url, save_path)
                st.success(f"Downloaded {url_name} and saved locally.")

            file_size = save_path.stat().st_size
            st.write(f"File size: {human_size(file_size)}")

            if file_size > TELEGRAM_MAX_SIZE:
                st.warning("File exceeds Telegram’s 2 GB limit. Sending info message instead.")
                msg = f"📦 File saved locally: **{save_path.name}** ({human_size(file_size)})"
                send_message_to_telegram(msg)
                st.info("File info message sent to Telegram.")
            else:
                with st.spinner("Sending file to Telegram..."):
                    resp = send_file_to_telegram(save_path)
                if resp.ok and resp.json().get("ok"):
                    st.success("✅ File sent successfully to Telegram!")
                else:
                    st.error(f"❌ Telegram upload failed: {resp.text}")
        except Exception as e:
            st.exception(e)

# -------------------------------------------------------------------
# List saved files
# -------------------------------------------------------------------
st.write("---")
st.subheader("Saved Files (local uploads/ directory)")

files = sorted(UPLOAD_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
if files:
    for f in files:
        st.write(f"- {f.name} — {human_size(f.stat().st_size)}")
else:
    st.write("No files saved yet.")
