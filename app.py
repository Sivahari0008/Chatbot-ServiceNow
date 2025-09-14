import os
import json
import warnings
from flask import Flask, request, jsonify, send_from_directory
from transformers import pipeline
from langdetect import detect
from keybert import KeyBERT
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

app = Flask(__name__)

### Translation setup ###

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

def get_translator(lang_code):
    model_name = LANG_MODEL_MAP.get(lang_code)
    if not model_name:
        raise ValueError(f"No translation model for language code: {lang_code}")
    if model_name in model_cache:
        return model_cache[model_name]
    translator = pipeline("translation", model=model_name)
    model_cache[model_name] = translator
    return translator

def translate_to_english(text):
    try:
        lang = detect(text)
        if lang == "en":
            return text
        translator = get_translator(lang)
        result = translator(text)
        return result[0]['translation_text']
    except Exception as e:
        warnings.warn(f"Translation failed: {e}")
        return text  # fallback to original

### Keyword extraction and document search setup ###

DOCS_DIR = "./docs"
kw_model = KeyBERT()

def extract_keywords(text, top_n=4):
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 1), stop_words='english', top_n=top_n)
    return [kw[0] for kw in keywords]

def load_documents():
    docs = []
    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DOCS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                content = f"{data.get('description', '')}\n\n{data.get('fix', '')}"
                docs.append(Document(page_content=content, metadata={"source": filename}))
    return docs

def create_vector_db(documents):
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return FAISS.from_documents(documents, embedding_model)

### Flask routes ###

@app.route("/", methods=["GET"])
def home():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"error": "No message provided"}), 400

        # Step 1: Translate to English
        translated_text = translate_to_english(message)

        # Step 2: Extract keywords and search docs
        keywords = extract_keywords(translated_text)
        query = " ".join(keywords)

        docs = load_documents()
        vectordb = create_vector_db(docs)
        results = vectordb.similarity_search(query, k=1)

        if results:
            best = results[0]
            description, fix = best.page_content.split("\n\n") if "\n\n" in best.page_content else (best.page_content, "")
            return jsonify({
                "source": "local",
                "description": description,
                "fix": fix,
                "metadata_source": best.metadata.get("source", "")
            })
        else:
            return jsonify({
                "source": "none",
                "message": "No local fix found. Please provide more details to create a support ticket."
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
