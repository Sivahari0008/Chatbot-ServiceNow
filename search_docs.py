import os
import json
from langdetect import detect
from transformers import pipeline
from keybert import KeyBERT
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

# === CONFIG ===
DOCS_DIR = "./docs"

# === Setup translation pipeline ===
LANG_MODEL_MAP = {
    'de': 'Helsinki-NLP/opus-mt-de-en',
    'fr': 'Helsinki-NLP/opus-mt-fr-en',
    'es': 'Helsinki-NLP/opus-mt-es-en',
    'it': 'Helsinki-NLP/opus-mt-it-en',
    'ru': 'Helsinki-NLP/opus-mt-ru-en',
    'ar': 'Helsinki-NLP/opus-mt-ar-en',
    'nl': 'Helsinki-NLP/opus-mt-nl-en',
    'zh-cn': 'Helsinki-NLP/opus-mt-zh-en',
    'ja': 'Helsinki-NLP/opus-mt-ja-en',
}

model_cache = {}

def translate_to_english(text):
    lang = detect(text)
    print(f"🌐 Detected Language: {lang}")
    model_name = LANG_MODEL_MAP.get(lang)
    if not model_name:
        raise ValueError(f"No model available for language '{lang}'")

    if model_name not in model_cache:
        model_cache[model_name] = pipeline("translation", model=model_name)
    translator = model_cache[model_name]
    return translator(text)[0]['translation_text']


# === Keyword extractor using KeyBERT ===
kw_model = KeyBERT()

def extract_keywords(text, top_n=4):
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 1), stop_words='english', top_n=top_n)
    return [kw[0] for kw in keywords]


# === Load documents and prepare embeddings ===
def load_documents():
    docs = []
    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DOCS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                text = f"{data.get('description', '')}\n\n{data.get('fix', '')}"
                docs.append(Document(page_content=text, metadata={"source": filename}))
    return docs


# === Build vector index ===
def create_vector_db(documents):
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectordb = FAISS.from_documents(documents, embedding_model)
    return vectordb


# === Main search function ===
def search_docs(user_input):
    translated = translate_to_english(user_input)
    keywords = extract_keywords(translated)

    print(f"Translated: {translated}")
    print(f"Keywords: {keywords}")

    # Rebuild vector DB (you can cache it later for speed)
    docs = load_documents()
    vectordb = create_vector_db(docs)

    # Use keyword string for search
    query = " ".join(keywords)
    results = vectordb.similarity_search(query, k=3)

    for i, res in enumerate(results, 1):
        print(f"\n🔎 Match #{i}")
        print("📄 Source:", res.metadata["source"])
        print("📚 Content:\n", res.page_content[:500], "...")


# === Entry Point ===
if __name__ == "__main__":
    user_input = input("📝 Enter your question or error message: ")
    search_docs(user_input)
