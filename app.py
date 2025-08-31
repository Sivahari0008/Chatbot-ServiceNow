import os
import json
from flask import Flask, request, jsonify, send_from_directory
import openai
import requests
from requests.auth import HTTPBasicAuth
import re

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



# def extract_keywords(question):
#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": "Extract 2–4 single-word keywords (separated by commas) related to the error or issue from the user's input. Respond only with keywords."},
#                 {"role": "user", "content": f"Extract keywords from: {question}"}
#             ],
#             temperature=0.2
#         )
#         content = response.choices[0].message['content']
#         content = re.sub(r'(?i)^keywords?:', '', content)  # Remove "Keywords:" prefix
#         return [kw.strip().lower() for kw in re.split(r",|\n", content) if kw.strip()]
#         #content = response.choices[0].message['content']
#         #print("Extracted raw keyword content:", content)
        
#         # Extract words using regex
#         #return [kw.strip().lower() for kw in re.split(r",|\n", content) if kw.strip()]
#     except Exception as e:
#         print(f"OpenAI error: {e}")
#         return []

def extract_keywords(question):
    """Local fallback keyword extractor using basic NLP."""
    stopwords = {
        "i", "am", "have", "has", "had", "having", "is", "was", "are", "were",
        "the", "a", "an", "to", "in", "on", "for", "with", "of", "and", "or",
        "it", "this", "that", "my", "your", "you", "me", "we", "us", "do", "does",
        "did", "at", "by", "as", "from", "but", "not", "be", "can", "could", "will",
        "would", "should"
    }

    words = re.findall(r'\b\w+\b', question.lower())
    keywords = [word for word in words if word not in stopwords]
    return keywords[:4]  # Limit to top 4 keywords for matching



def find_fix(keywords, repo_path="./docs"):
    """Looks for a fix in the local /fixes folder."""
    for filename in os.listdir(repo_path):
        if filename.endswith(".json"):
            filepath = os.path.join(repo_path, filename)
            with open(filepath, "r") as f:
                data = json.load(f)
                error_keywords = [k.lower() for k in data.get("error_keywords", [])]
                error_keywords = ["database","connection","timeout"]
                print(f"Checking {filename} with error_keywords: {error_keywords}")
                if set(keywords) & set(error_keywords):
                #if any(k in error_keywords for k in keywords):
                    print(" Match found with:", keywords)
                    return data
    print("No match found with keywords:", keywords)
    return None

@app.route("/create_servicenow_ticket", methods=["POST"])    
def create_servicenow_ticket(description):


try:
        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        short_desc = data.get("short_description")
        long_desc = data.get("description")

        full_description = f"{long_desc}\n\nReported by: {name} ({email})"

        url = f"https://{SERVICENOW_INSTANCE}.service-now.com/api/now/table/incident"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        payload = {
            "short_description": short_desc,
            "description": full_description
        }

        response = requests.post(
            url,
            auth=HTTPBasicAuth(SERVICENOW_USER, SERVICENOW_PASSWORD),
            headers=headers,
            json=payload
        )

        response.raise_for_status()
        result = response.json()
        return jsonify({
            "number": result["result"]["number"],
            "sys_id": result["result"]["sys_id"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === ROUTES ===

@app.route("/", methods=["GET"])
def home():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        question = data.get("message", "")
        
        if not question:
            return jsonify({"error": "No message provided"}), 400

        keywords = extract_keywords(question)
        fix_data = find_fix(keywords)

        if fix_data:
            # Fix found in local JSON
            return jsonify({
                "source": "local",
                "description": fix_data.get("description"),
                "fix": fix_data.get("fix")
            })
        else:
            # No fix found; create a ServiceNow ticket
            ticket_response = create_servicenow_ticket(description=question)
            return jsonify({
                "source": "servicenow",
                "message": "No local fix found. Created ServiceNow ticket.",
                "ticket": ticket_response
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



    



# === MAIN ===

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
