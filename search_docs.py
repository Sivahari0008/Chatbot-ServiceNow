import os
import json
from flask import Flask, request, jsonify
from keybert import KeyBERT
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

DOCS_DIR = "./docs"

app = Flask(__name__)
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

@app.route("/search", methods=["POST"])
def search():
    try:
        data = request.get_json()
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"found": False, "message": "Empty input"}), 400

        keywords = extract_keywords(text)
        query = " ".join(keywords)

        docs = load_documents()
        vectordb = create_vector_db(docs)
        results = vectordb.similarity_search(query, k=1)

        if results:
            best = results[0]
            return jsonify({
                "found": True,
                "description": best.page_content.split("\n\n")[0],
                "fix": best.page_content.split("\n\n")[1],
                "source": best.metadata["source"]
            })
        else:
            return jsonify({"found": False, "message": "No match found"})

    except Exception as e:
        return jsonify({"found": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
