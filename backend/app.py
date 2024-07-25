import os
import json
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from langsmith import traceable
from medications import medications
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file.filename:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        return jsonify({"message": "File uploaded successfully",
                        "path": filepath}), 200


@app.route('/transcribe', methods=['GET'])
def transcribe_audio():
    filename = 'recording.webm'
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    try:
        with open(filepath, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="cs",
                prompt=medications
            )

            postprocessed_text = run_pipeline(transcription)
            return jsonify({"transcription": postprocessed_text}), 200
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500


@traceable
def format_prompt(text: str) -> list:
    return [
        {
            "role": "system",
            "content": """
__ASK__
You are a professional copywriter tasked with correcting misspellings and grammatical errors in a text containing an ophthalmologist's diagnosis. The text may include technical terms and recommendations. Your goal is to produce a corrected version of the text and extract any recommendations mentioned. 

__CONTEXT__
The text is in Czech language and is produced by speech to text conversion. The conversion is not entirely precise and thus there are some mistakes. It is your task to correct these mistakes. It is important to consider the fact that it is an ophthalmologist diagnosis that is included in the provided text so correct these mistakes in such a way that the diagnosis makes sense.

__CONSTRAINTS__
Follow these steps to complete the task:

1. Carefully read through the entire text.

2. Correct any misspellings and grammatical errors you find in the text. Pay close attention to sentence structure, punctuation, and word usage.

3. When encountering technical terms related to ophthalmology, do not alter them unless you are absolutely certain they are misspelled. If you are unsure about a technical term, leave it unchanged.

4. As you review the text, look for any mentions of recommendations. These might be introduced with phrases like "I recommend," "it is advised," or "the patient should."

5. If you find any recommendations, extract them and prepare to list them separately.

6. If there are no recommendations mentioned in the text, include an empty array for the "recommendations" key, like this:

{
  "text": "Your corrected version of the text goes here",
  "recommendations": []
}

7. If you encounter any words that you are unsure about, especially if they might be technical terms, leave them unchanged in the corrected text.

8. Ensure that the corrected text in the "text" field does not include the recommendations you've extracted. The recommendations should only appear in the "recommendations" array.

9. Answer purely in Czech language!
__OUTPUT_FORMAT__
After correcting the text and identifying any recommendations, prepare your output in the following JSON format:

{
  "text": "Your corrected version of the text goes here, excluding any recommendations",
  "recommendations": ["Recommendation 1", "Recommendation 2", "etc."]
}
"""
        },
        {
            "role": "user",
            "content": f"Prosím oprav podle instrukcí tento text: {text}"
        }
    ]

@traceable(run_type="llm")
def invoke_llm(messages: list) -> dict:
    return openai.chat.completions.create(
        messages=messages, model="gpt-4o", temperature=0.7, response_format={"type": "json_object"}
    )

@traceable
def parse_output(response: dict) -> str:
    response_content = response.choices[0].message.content
    response_json = json.loads(response_content)
    
    if response_json.get("recommendations") == []:
        response_text = response_json.get("text")
    else:
        recommendations = "\nDoporučení:\n" + "\n".join([f"• {rec}" for rec in response_json.get("recommendations")])
        response_text = response_json.get("text") + recommendations
    
    return response_text

@traceable
def run_pipeline(text: str) -> str:
    messages = format_prompt(text)
    response = invoke_llm(messages)
    return parse_output(response)


if __name__ == '__main__':
    app.run(debug=True)
