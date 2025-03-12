import streamlit as st
from PyPDF2 import PdfReader
from transformers import pipeline, AutoTokenizer

# Load pre-trained models
classification_model = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")

# Function to extract text from PDF
def extract_text_from_pdf(uploaded_file):
    text = ""
    pdf_reader = PdfReader(uploaded_file)
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:  # Check if text extraction worked
            text += page_text + "\n"
    return text

# Function to truncate long text
def truncate_text(text, max_tokens=512):
    tokens = tokenizer.encode(text, truncation=True, max_length=max_tokens)
    return tokenizer.decode(tokens)

# Streamlit UI
st.title("AI Resume Analyzer")
uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

if uploaded_file:
    text = extract_text_from_pdf(uploaded_file)

    # Truncate text if too long
    text = truncate_text(text)

    # Classify the job role
    classification_result = classification_model(text)

    # Display results
    st.write(f"**Predicted Job Role:** {classification_result[0]['label']}")
