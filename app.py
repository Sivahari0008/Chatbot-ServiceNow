from flask import Flask, request, jsonify
import os
import requests
import openai
import time
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core import Document
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import openai

load_dotenv()
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)

# Load documents once
docs = [Document(text="If VPN fails, restart your client or check your credentials.")]
index = VectorStoreIndex.from_documents(docs)
query_engine = index.as_query_engine()

# --- Helper: Rate-friendly query wrapper ---
from openai import OpenAI
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="<OPENAI_API_KEY>",
)
completion = client.chat.completions.create(
  extra_headers={
    "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
  },
  model="openai/gpt-4o",
  messages=[
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
)
print(completion.choices[0].message.content)

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
