# genai_utils.py

import os
import re
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def translate_to_english(text):
    """
    Uses GPT-4 to translate non-English input (e.g., German) to English.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Translate the following text to English."},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )
        translated = response.choices[0].message['content'].strip()
        return translated
    except Exception as e:
        print(f"[Translation Error]: {e}")
        return text  # Fallback to original if translation fails

def extract_keywords_gpt(text):
    """
    Extracts 2–4 single-word keywords using GPT-4.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Extract 2–4 single-word keywords (comma-separated) related to the issue from the user's input. Respond with only the keywords."},
                {"role": "user", "content": f"Extract keywords from: {text}"}
            ],
            temperature=0.2
        )
        content = response.choices[0].message['content']
        content = re.sub(r'(?i)^keywords?:', '', content)
        return [kw.strip().lower() for kw in re.split(r",|\n", content) if kw.strip()]
    except Exception as e:
        print(f"[Keyword Extraction Error]: {e}")
        return []
