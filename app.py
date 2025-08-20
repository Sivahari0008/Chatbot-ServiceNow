from flask import Flask, request, jsonify
import os
import requests
import openai
import time
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core import Document
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from openai.error import RateLimitError, OpenAIError

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# Load documents once
docs = [Document(text="If VPN fails, restart your client or check your credentials.")]
index = VectorStoreIndex.from_documents(docs)
query_engine = index.as_query_engine()

# --- Helper: Rate-friendly query wrapper ---
def safe_query_engine(query, max_retries=5, backoff_factor=5):
    for attempt in range(max_retries):
        try:
            response = query_engine.query(query)
            return str(response)
        except RateLimitError:
            wait_time = backoff_factor * (2 ** attempt)  # Exponential backoff
            print(f"[RateLimitError] Retry in {wait_time} seconds...")
            time.sleep(wait_time)
        except OpenAIError as e:
            print(f"[OpenAIError] {e}")
            break  # Non-retriable OpenAI error
        except Exception as e:
            print(f"[Unknown error] {e}")
            break
    return "We're experiencing high demand. Please try again later."

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
            os.getenv("SERVICENOW_PASSWORD")),
        headers={"Content-Type": "application/json"},
        json=payload
    )

    if response.status_code == 201:
        return response.json()['result']['number']
    else:
        return f"Error: {response.status_code}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
