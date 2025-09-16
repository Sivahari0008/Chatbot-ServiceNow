import os
import json
import warnings
from flask import Flask, request, jsonify, send_from_directory
from transformers import pipeline
from langdetect import detect
import yake
from langchain_community.vectorstores import FAISS

from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings

# Use a lightweight model


app = Flask(__name__)

### --- Keyword extractor (lightweight) --- ###
kw_extractor = yake.KeywordExtractor(n=1, top=4)

def extract_keywords(text, top_n=4):
    keywords = kw_extractor.extract_keywords(text)
    return [kw[0] for kw in keywords[:top_n]]

### --- Translation --- ###
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

current_translator = None
current_lang = None

def get_translator(lang_code):
    global current_translator, current_lang
    model_name = LANG_MODEL_MAP.get(lang_code)
    if not model_name:
        raise ValueError(f"No translation model for language code: {lang_code}")
    if current_lang != lang_code:
        current_translator = pipeline("translation", model=model_name)
        current_lang = lang_code
    return current_translator

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
        return text

### --- Document & FAISS Setup --- ###
DOCS_DIR = "./docs"
FAISS_INDEX_PATH = "faiss_index"
#embedding_model = HuggingFaceEmbeddings(model_name="paraphrase-MiniLM-L3-v2")
#embedding_model = HuggingFaceEmbeddings(model_name="intfloat/e5-small-v2")
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-MiniLM-L3-v2",
    model_kwargs={"device": "cpu"}  # optional: avoid GPU memory issues
)


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

# Build or load FAISS
_vectordb = None

def get_vectordb():
    global _vectordb

    if _vectordb is None:
        if os.path.exists(FAISS_INDEX_PATH):
            try:
                _vectordb = FAISS.load_local(FAISS_INDEX_PATH, embedding_model)
                print("✅ FAISS index loaded from disk.")
            except Exception as e:
                raise RuntimeError("❌ Failed to load FAISS index.") from e
        else:
            print("⚠️ FAISS index not found. Building now...")
            docs = load_documents()
            _vectordb = FAISS.from_documents(docs, embedding_model)
            _vectordb.save_local(FAISS_INDEX_PATH)
            print("✅ FAISS index built and saved.")
    
    return _vectordb

    

### --- Routes --- ###
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

        translated_text = translate_to_english(message)
        keywords = extract_keywords(translated_text)
        query = " ".join(keywords)

        results = vectordb.similarity_search(query, k=1)

        if results:
            best = results[0]
            parts = best.page_content.split("\n\n", 1)
            description = parts[0]
            fix = parts[1] if len(parts) > 1 else ""
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
