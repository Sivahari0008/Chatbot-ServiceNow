import os
import time
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from openai import OpenAI
from llama_index.core import VectorStoreIndex, Document

from llama_index.embeddings import HuggingFaceEmbedding


# Load environment variables
load_dotenv()

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Use HuggingFace for local embeddings
embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Flask app setup
app = Flask(__name__)

# Load documents once (replace with your actual docs)
docs = [Document(text="If VPN fails, restart your client or check your credentials.")]

# Use local embedding model when building index
index = VectorStoreIndex.from_documents(docs, embed_model=embed_model)
query_engine = index.as_query_engine()

def safe_query_engine(prompt, max_retries=5, backoff_factor=2):
    """
    Calls the LlamaIndex query engine with exponential backoff on errors.
    """
    for attempt in range(max_retries):
        try:
            response = query_engine.query(prompt)
            return str(response)
        except Exception as e:
            wait_time = backoff_factor * (2 ** attempt)
            print(f"Error querying engine: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
    return "Sorry, the service is currently busy. Please try again later."

def create_incident(short_desc, description, email):
    url = f"{os.getenv('SERVICENOW_INSTANCE')}/api/now/table/incident"
    payload = {
        "short_description": short_desc,
        "description": description,
        "caller_id": email,
        "category": "inquiry"
    }
    response = requests.post(
        url,
        auth=HTTPBasicAuth(
            os.getenv("SERVICENOW_USERNAME"),
            os.getenv("SERVICENOW_PASSWORD")
        ),
        headers={"Content-Type": "application/json"},
        json=payload
    )
    if response.status_code == 201:
        return response.json()['result']['number']
    else:
        return f"Error creating incident: {response.status_code}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_query = data.get("message")
    email = data.get("email")
    resolved = data.get("resolved", False)

    answer = safe_query_engine(user_query)

    if not resolved:
        incident = create_incident(user_query, answer, email)
        return jsonify({
            "solution": answer,
            "incident": incident
        })

    return jsonify({
        "solution": answer,
        "message": "Glad it helped!"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
