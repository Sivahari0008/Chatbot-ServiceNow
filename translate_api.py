from flask import Flask, request, jsonify
from transformers import pipeline
from langdetect import detect
import warnings

app = Flask(__name__)

# Language → Model mapping
LANG_MODEL_MAP = {
    'de': 'Helsinki-NLP/opus-mt-de-en',
    'fr': 'Helsinki-NLP/opus-mt-fr-en',
    'es': 'Helsinki-NLP/opus-mt-es-en',
    'it': 'Helsinki-NLP/opus-mt-it-en',
    'ru': 'Helsinki-NLP/opus-mt-ru-en',
    'ar': 'Helsinki-NLP/opus-mt-ar-en',
    'nl': 'Helsinki-NLP/opus-mt-nl-en',
    'ja': 'Helsinki-NLP/opus-mt-ja-en',
    'zh-cn': 'Helsinki-NLP/opus-mt-zh-en',
    # Add more languages if needed
}

# Cache loaded models
model_cache = {}

def get_translator(lang_code):
    model_name = LANG_MODEL_MAP.get(lang_code)
    if not model_name:
        raise ValueError(f"❌ No model available for language: {lang_code}")
    
    # Use cached model if available
    if model_name in model_cache:
        return model_cache[model_name]

    # Load and cache the model
    translator = pipeline("translation", model=model_name)
    model_cache[model_name] = translator
    return translator

@app.route("/translate", methods=["POST"])
def translate():
    try:
        data = request.get_json()
        text = data.get("text", "").strip()

        if not text:
            return jsonify({"error": "Missing or empty 'text' parameter"}), 400

        # Detect language
        detected_lang = detect(text)
        print(f" Detected language: {detected_lang}")

        # Translate using appropriate model
        translator = get_translator(detected_lang)
        result = translator(text)
        translated_text = result[0]['translation_text']

        return jsonify({
            "input_language": detected_lang,
            "original_text": text,
            "translated_text": translated_text
        })

    except Exception as e:
        warnings.warn(f"Translation failed: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
