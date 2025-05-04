import streamlit as st
import pdfplumber
from PIL import Image
import io
import re
import google.generativeai as genai
from google.generativeai.types import content_types

# --- Gemini API Key ---
genai.configure(api_key="AIzaSyDYi9P3LnloOy4AUmkwysF4VlQqaObL-ws")  # Replace with your API key

st.set_page_config(page_title="DocuMind AI", layout="centered")
st.title("📄 DocuMind AI")
st.caption("Extract info from documents & locate where it appears!")

# Upload file
uploaded_file = st.file_uploader("Upload a PDF or Image", type=["pdf"])
question = st.text_input("Ask a question about the document")


# --- Extract from PDF ---
def extract_from_pdf(file):
    page_texts = []
    with pdfplumber.open(file) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                page_texts.append((f"Page {i + 1}", text.strip()))
    return page_texts


# --- Ask Gemini using text ---
def ask_gemini_with_text(context_text, question):
    try:
        model = genai.GenerativeModel("models/gemini-1.5-pro")
        response = model.generate_content([
            f"You are analyzing a document. Here's its text:\n\n{context_text}\n\nNow answer the question:",
            question
        ])
        return response.text.strip()
    except Exception as e:
        st.error(f"❌ Gemini error (text): {e}")
        return None


# --- Ask Gemini using image ---
def ask_gemini_with_image(image_bytes, question):
    try:
        model = genai.GenerativeModel("models/gemini-1.5-pro")

        # Directly send the image without the content_types.Image wrapper
        image = Image.open(io.BytesIO(image_bytes))
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        response = model.generate_content([question, img_bytes])  # Send image bytes directly
        return response.text.strip()
    except Exception as e:
        st.error(f"❌ Gemini error (image): {e}")
        return None


# --- Find Source Location ---
def find_source(answer, document_parts):
    important_phrases = re.findall(r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', answer)
    found_sources = []
    for section, text in document_parts:
        for phrase in important_phrases:
            if phrase.lower() in text.lower():
                found_sources.append(section)
                break
    return list(set(found_sources))


# --- Main Logic ---
if uploaded_file:
    filename = uploaded_file.name
    file_bytes = uploaded_file.read()

    st.success(f"✅ Uploaded: {filename}")

    if filename.lower().endswith(".pdf"):
        with open("temp.pdf", "wb") as f:
            f.write(file_bytes)
        doc_parts = extract_from_pdf("temp.pdf")
        full_context = "\n\n".join([text for _, text in doc_parts])
    else:
        doc_parts = [("Image", "Uploaded image")]
        full_context = None

    if question:
        with st.spinner("🤖 Thinking..."):
            if filename.lower().endswith(".pdf"):
                answer = ask_gemini_with_text(full_context, question)
            else:
                answer = ask_gemini_with_image(file_bytes, question)

        if answer:
            st.subheader("🧠 Answer:")
            st.success(answer)

            if filename.lower().endswith(".pdf"):
                st.subheader("📍 Found In:")
                locations = find_source(answer, doc_parts)
                if locations:
                    for loc in locations:
                        st.markdown(f"- **{loc}**")
                else:
                    st.info("Couldn't pinpoint the source.")
            else:
                st.subheader("📍 Based on image analysis.")

        else:
            st.warning("❌ Gemini couldn't answer your question.")
    else:
        st.info("Enter a question to ask about the document.")
