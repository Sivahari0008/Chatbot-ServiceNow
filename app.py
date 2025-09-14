import json
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

TRANSLATE_URL = "http://localhost:5000/translate"
SEARCH_URL = "http://localhost:6000/search"

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

        # Step 1: Translate input to English
        translate_res = requests.post(TRANSLATE_URL, json={"text": message})
        translation_data = translate_res.json()
        translated_text = translation_data.get("translated_text", message)

        # Step 2: Search for a fix using the translated text
        search_res = requests.post(SEARCH_URL, json={"text": translated_text})
        search_result = search_res.json()

        if search_result.get("found"):
            return jsonify({
                "source": "local",
                "description": search_result.get("description"),
                "fix": search_result.get("fix")
            })
        else:
            return jsonify({
                "source": "none",
                "message": "No local fix found. Please provide more details to create a support ticket."
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
