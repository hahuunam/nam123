import streamlit as st
import os
import json
import io
from datetime import datetime
from PyPDF2 import PdfReader
import docx
import networkx as nx
import matplotlib.pyplot as plt
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# ================== CẤU HÌNH ==================
st.set_page_config(page_title="AI Ngữ Văn", page_icon="📚", layout="wide")
st.title("📚 AI Hỗ trợ Ngữ Văn (ChatGPT + Lưu Drive)")

# ================== GOOGLE DRIVE ==================
def get_drive_service():
    service_account_info = json.loads(st.secrets["GDRIVE_SERVICE_ACCOUNT"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=credentials)

def upload_to_drive(uploaded_file):
    service = get_drive_service()

    file_metadata = {
        "name": uploaded_file.name,
        "parents": [st.secrets["FOLDER_ID"]]
    }

    media = MediaIoBaseUpload(
        io.BytesIO(uploaded_file.getvalue()),
        resumable=True
    )

    service.files().create(
        body=file_metadata,
        media_body=media
    ).execute()

def load_files_from_drive():
    service = get_drive_service()

    results = service.files().list(
        q=f"'{st.secrets['FOLDER_ID']}' in parents",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])
    docs = {}

    for file in files:
        request = service.files().get_media(fileId=file["id"])
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_stream.seek(0)
        filename = file["name"].lower()

        try:
            if filename.endswith(".pdf"):
                docs[file["name"]] = read_pdf(file_stream)
            elif filename.endswith(".docx"):
                docs[file["name"]] = read_docx(file_stream)
            elif filename.endswith(".txt"):
                docs[file["name"]] = file_stream.read().decode("utf-8", errors="ignore")
        except:
            docs[file["name"]] = ""

    return docs

# ================== ĐỌC FILE ==================
def read_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

# ================== LƯU CHAT ==================
def save_chat_history(question, answer):
    service = get_drive_service()

    content = f"""
Thời gian: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
Câu hỏi: {question}
Trả lời:
{answer}
---------------------------------------
"""

    media = MediaIoBaseUpload(
        io.BytesIO(content.encode("utf-8")),
        mimetype="text/plain",
        resumable=True
    )

    file_metadata = {
        "name": "chat_history.txt",
        "parents": [st.secrets["FOLDER_ID"]]
    }

    service.files().create(
        body=file_metadata,
        media_body=media
    ).execute()

# ================== SƠ ĐỒ TƯ DUY ==================
def tao_so_do_tu_duy(text):
    y_chinh = [y.strip() for y in text.replace("–", "-").split("-") if y.strip()]
    if len(y_chinh) < 2:
        y_chinh = [y.strip() for y in text.split(".") if len(y.strip()) > 5]

    if not y_chinh:
        st.warning("Không đủ ý chính để tạo sơ đồ.")
        return

    G = nx.Graph()
    G.add_node("Chủ đề")

    for y in y_chinh[:10]:
        G.add_node(y)
        G.add_edge("Chủ đề", y)

    pos = nx.spring_layout(G, seed=42)

    plt.figure(figsize=(9, 7))
    nx.draw(G, pos, with_labels=True,
            node_size=2500,
            node_color="lightblue",
            font_size=9)

    st.pyplot(plt)

# ================== ADMIN ==================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

st.sidebar.title("🔐 Quản lý")
mode = st.sidebar.radio("Chọn chế độ:", ["Người dùng", "Admin"])

if mode == "Admin":
    password = st.sidebar.text_input("Nhập mật khẩu:", type="password")
    if st.sidebar.button("Đăng nhập"):
        if password == "12345":
            st.session_state.is_admin = True
            st.sidebar.success("Đăng nhập thành công")
        else:
            st.sidebar.error("Sai mật khẩu")
else:
    st.session_state.is_admin = False

docs = load_files_from_drive()

col1, col2 = st.columns([1.2, 1])

# ================== UPLOAD ==================
with col2:
    if st.session_state.is_admin:
        st.subheader("📂 Tải tài liệu")

        uploaded_files = st.file_uploader(
            "Tải lên nhiều file",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True
        )

        if uploaded_files:
            for file in uploaded_files:
                upload_to_drive(file)
            st.success("Upload thành công!")
            st.rerun()

        st.write("📚 Tổng số tài liệu:", len(docs))
        for name in docs.keys():
            st.write("•", name)

# ================== HỎI ĐÁP ==================
with col1:
    st.subheader("📝 Hỏi đáp bằng ChatGPT")

    api_key = st.text_input("Nhập OpenAI API Key", type="password")

    question = st.text_area("Nhập câu hỏi:")

    if st.button("💡 Hỏi AI"):
        if not api_key:
            st.warning("Nhập API key trước")
        elif not question.strip():
            st.warning("Nhập câu hỏi trước")
        elif not docs:
            st.warning("Chưa có tài liệu")
        else:
            client = OpenAI(api_key=api_key)

            context = "\n\n".join(docs.values())[:12000]

            prompt = f"""
Chỉ trả lời dựa trên nội dung tài liệu sau.
Nếu không có thông tin, trả lời: "Không có trong tài liệu."

--- TÀI LIỆU ---
{context}
----------------

Câu hỏi: {question}
"""

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Bạn là trợ lý AI Ngữ văn."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )

                answer = response.choices[0].message.content
                st.session_state.answer = answer

                save_chat_history(question, answer)

            except Exception as e:
                st.error(f"Lỗi API: {e}")

    st.subheader("📖 Kết quả")
    st.text_area("Trả lời:",
                 value=st.session_state.get("answer", ""),
                 height=300)

    if st.session_state.get("answer"):
        if st.button("🌳 Tạo sơ đồ tư duy"):
            tao_so_do_tu_duy(st.session_state.answer)
