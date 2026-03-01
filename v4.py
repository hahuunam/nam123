import streamlit as st
import openai
import os
from PyPDF2 import PdfReader
import docx
import networkx as nx
import matplotlib.pyplot as plt

# ------------------- Cấu hình -------------------
st.set_page_config(page_title="AI Hỗ trợ Ngữ Văn", page_icon="📚", layout="wide")
st.title("📚 AI Hỗ trợ Dạy & Học Ngữ Văn")

openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------- Hàm tiện ích -------------------
def read_pdf(file):
    """Đọc nội dung từ file PDF."""
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def read_docx(file):
    """Đọc nội dung từ file Word."""
    doc = docx.Document(file)
    text = "\n".join([p.text for p in doc.paragraphs])
    return text

def tao_so_do_tu_duy(text):
    """Tạo và hiển thị sơ đồ tư duy đẹp hơn từ nội dung văn bản."""
    try:
        # Cắt ý chính
        y_chinh = [y.strip() for y in text.replace("–", "-").split("-") if y.strip()]
        if len(y_chinh) < 2:
            y_chinh = [y.strip() for y in text.split(".") if len(y.strip()) > 5]

        if not y_chinh:
            st.warning("⚠️ Không đủ ý chính để tạo sơ đồ tư duy.")
            return

        # Tạo đồ thị
        G = nx.Graph()
        G.add_node("Chủ đề", color='skyblue', size=2000)

        for y in y_chinh[:10]:
            G.add_node(y, color='lightgreen', size=1500)
            G.add_edge("Chủ đề", y)

        colors = [nx.get_node_attributes(G, 'color')[n] for n in G.nodes()]
        sizes = [nx.get_node_attributes(G, 'size')[n] for n in G.nodes()]
        pos = nx.spring_layout(G, seed=42)

        # Vẽ sơ đồ
        plt.figure(figsize=(9, 7))
        nx.draw(G, pos, with_labels=True, node_color=colors, node_size=sizes, font_size=10, font_weight='bold', edge_color='gray')
        plt.title("🧠 Sơ đồ tư duy", fontsize=15, fontweight='bold')
        st.pyplot(plt)

        # Nút lưu ảnh
        save_path = "so_do_tu_duy.png"
        plt.savefig(save_path, bbox_inches='tight')
        st.success("✅ Đã tạo sơ đồ tư duy thành công!")
        with open(save_path, "rb") as f:
            st.download_button("📥 Tải sơ đồ tư duy (PNG)", data=f, file_name="so_do_tu_duy.png", mime="image/png")

    except Exception as e:
        st.error(f"❌ Lỗi khi tạo sơ đồ: {e}")

# ------------------- Quản lý quyền Admin -------------------
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

st.sidebar.title("🔐 Quản lý")
st.sidebar.image("2.jpg", use_container_width=True)
st.sidebar.markdown(
    "<h4 style='text-align: center; color: red;'>Trường THPT Võ Chí Công - Đà Nẵng</h4>",
    unsafe_allow_html=True
)

admin_tab = st.sidebar.radio("Chọn chế độ:", ["Người dùng", "Admin"])

if admin_tab == "Admin":
    password = st.sidebar.text_input("Nhập mật khẩu admin:", type="password")
    if st.sidebar.button("Đăng nhập"):
        if password == "12345":
            st.session_state.is_admin = True
            st.sidebar.success("✅ Đăng nhập thành công!")
        else:
            st.sidebar.error("❌ Sai mật khẩu!")
else:
    st.session_state.is_admin = False

# ------------------- Bộ nhớ tài liệu -------------------
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = {}

# ------------------- Giao diện chính -------------------
col1, col2 = st.columns([1.2, 1])

# --------- CỘT PHẢI: Quản lý tài liệu (Admin) ---------
with col2:
    if st.session_state.is_admin:
        st.subheader("📂 Tài liệu học tập")

        uploaded_file = st.file_uploader("📤 Tải lên tài liệu mới", type=["pdf", "docx", "txt"])
        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                text = read_pdf(uploaded_file)
            elif uploaded_file.type in [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword"
            ]:
                text = read_docx(uploaded_file)
            else:
                text = uploaded_file.read().decode("utf-8", errors="ignore")

            # Xóa tài liệu cũ khi thêm mới
            st.session_state.uploaded_docs.clear()
            st.session_state.uploaded_docs[uploaded_file.name] = text
            st.success(f"✅ Đã tải lên: {uploaded_file.name} (các tài liệu cũ đã bị xóa)")

        if st.session_state.uploaded_docs:
            st.subheader("📘 Danh sách tài liệu")
            doc_name = st.selectbox("📄 Chọn tài liệu để xem hoặc xóa:", list(st.session_state.uploaded_docs.keys()))
            st.text_area("📖 Xem trước nội dung", value=st.session_state.uploaded_docs[doc_name][:2000], height=250)

            if st.button("🗑️ Xóa tài liệu này"):
                if st.checkbox("Tôi xác nhận muốn xóa tài liệu này."):
                    del st.session_state.uploaded_docs[doc_name]
                    st.success(f"🗑️ Đã xóa tài liệu: {doc_name}")
                    st.rerun()
                else:
                    st.warning("⚠️ Vui lòng tick xác nhận trước khi xóa.")
        else:
            st.info("📭 Chưa có tài liệu nào được tải lên.")
    else:
        st.info("👤 Bạn đang ở chế độ người dùng. Chỉ Admin mới tải tài liệu.")

# --------- CỘT TRÁI: Hỏi đáp và Sơ đồ tư duy ---------
with col1:
    st.subheader("📝 Đặt câu hỏi (AI chỉ trả lời nếu có trong tài liệu)")
    question = st.text_area("Nhập câu hỏi:", height=100)

    api_key_input = st.text_input("🔑 Nhập OpenAI API Key (nếu chưa có trong môi trường)", type="password")
    if api_key_input:
        openai.api_key = api_key_input

    if st.button("💡 Hỏi AI"):
        if not question.strip():
            st.warning("❗ Vui lòng nhập câu hỏi trước.")
        elif not st.session_state.uploaded_docs:
            st.warning("📭 Chưa có tài liệu nào. Hãy để admin tải lên trước.")
        else:
            with st.spinner("🤖 AI đang xử lý..."):
                context = "\n\n".join([v for v in st.session_state.uploaded_docs.values()])[:6000]
                prompt = f"""
                Bạn là trợ lý AI chỉ được phép trả lời dựa trên nội dung sau:
                Nếu câu hỏi không có trong tài liệu, hãy trả lời chính xác: "Câu hỏi không có trong tài liệu."

                --- TÀI LIỆU ---
                {context}
                -----------------

                Câu hỏi: {question}
                """

                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Bạn là trợ lý AI đọc hiểu tài liệu Ngữ văn Việt Nam."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    answer = response.choices[0].message.content.strip()
                    st.session_state.answer = answer
                except Exception as e:
                    st.error(f"❌ Lỗi OpenAI API: {e}")

    # Hiển thị kết quả
    st.subheader("📖 Câu trả lời từ AI")
    st.text_area("Kết quả:", value=st.session_state.get("answer", ""), height=300)

    # --------- Sơ đồ tư duy ---------
    if st.session_state.get("answer"):
        if st.button("🌳 Tạo sơ đồ tư duy từ câu trả lời"):
            st.info("🧠 Đang tạo sơ đồ tư duy...")
            tao_so_do_tu_duy(st.session_state.answer)
