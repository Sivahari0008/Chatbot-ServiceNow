from flask import Flask, request, jsonify
import os
import requests
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth


load_dotenv()

app = Flask(__name__)

# Load documents once
docs = SimpleDirectoryReader("docs").load_data()
index = VectorStoreIndex.from_documents(docs)
query_engine = index.as_query_engine()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_query = data.get("message")
    email = data.get("email")
    resolved = data.get("resolved", False)

    response = query_engine.query(user_query)
    answer = str(response)

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
