import os
import json
from flask import Flask, request, jsonify, send_from_directory
import openai
import requests
from requests.auth import HTTPBasicAuth

# === CONFIGURATION ===
openai.api_key = os.getenv("OPENAI_API_KEY")

#SERVICENOW_INSTANCE = os.getenv("SERVICENOW_INSTANCE")  
#SERVICENOW_USER = os.getenv("SERVICENOW_USER")
SERVICENOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD")
SERVICENOW_INSTANCE = "dev183670" 
SERVICENOW_USER = "admin"


# === FLASK APP SETUP ===
app = Flask(__name__)

# === UTILITY FUNCTIONS ===

def extract_keywords(question):
    """Uses OpenAI to extract relevant error keywords."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Extract 2–4 keywords related to error or issue from user input."},
                {"role": "user", "content": f"Extract keywords from: {question}"}
            ],
            temperature=0.2
        )
        content = response.choices[0].message['content']
        return [kw.strip().lower() for kw in content.split(",")]
    except Exception as e:
        print(f"OpenAI error: {e}")
        return []

def find_fix(keywords, repo_path="./docs"):
    """Looks for a fix in the local /fixes folder."""
    for filename in os.listdir(repo_path):
        if filename.endswith(".json"):
            filepath = os.path.join(repo_path, filename)
            with open(filepath, "r") as f:
                data = json.load(f)
                error_keywords = [k.lower() for k in data.get("error_keywords", [])]
                if any(k in error_keywords for k in keywords):
                    return data
    return None
    
def create_servicenow_ticket(description):
    url = f"https://{SERVICENOW_INSTANCE}.service-now.com/api/now/table/incident"

#    headers = {
#        "Content-Type": "application/json",
#        "Accept": "application/json"
#    }
    headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}

    payload = {
        "short_description": "Issue auto-created by chatbot",
        "description": description,
        "category": "inquiry"
    }

    try:
        print("Sending request to ServiceNow...")
        print("URL:", url)
        print("Payload:", payload)
        print("User:", SERVICENOW_USER)

        response = requests.post(
            url,
            auth=HTTPBasicAuth(SERVICENOW_USER, SERVICENOW_PASSWORD),
            headers=headers,
            json=payload,
            timeout=10  # optional timeout
        )

        print("Response Status:", response.status_code)
        print("Response Body:", response.text)

        if response.status_code == 201:
            return response.json()["result"]["number"]
        else:
            return f"ServiceNow error: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        print("Request Exception:", e)
        return f"Exception during ticket creation: {str(e)}"



# === ROUTES ===

@app.route("/", methods=["GET"])
def home():
    return send_from_directory(".", "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_question = data.get("question", "")
    
    if not user_question:
        return jsonify({"error": "Missing 'question' in request."}), 400

    keywords = extract_keywords(user_question)
    fix = find_fix(keywords)

    if fix:
        return jsonify({
            "status": "found",
            "message": "Fix found for your issue.",
            "fix": fix["fix"]
        })
    else:
        ticket_id = create_servicenow_ticket(user_question)
        return jsonify({
            "status": "ticket_created",
            "message": "No solution found. A ticket has been created.",
            "ticket_number": ticket_id
        })

# === MAIN ===

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
