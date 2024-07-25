import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
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

            postprocessed_text = postprocess_text(transcription)
            return jsonify({"transcription": postprocessed_text}), 200
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500


def postprocess_text(text: str) -> dict:
    completion = client.chat.completions.create(
        model="gpt-4o",  # gpt-3.5-turbo, gpt-4-turbo-preview
        response_format={"type": "json_object"},
        temperature=0.3,
        messages=[
            {"role": "system", "content": """
__ASK__
You are a professional copywriter tasked with correcting misspellings and grammatical errors in a text containing an ophthalmologist's diagnosis. The text may include technical terms and recommendations. Your goal is to produce a corrected version of the text and extract any recommendations mentioned. 

__CONTEXT__
The text is in Czech language and is produced by speech to text conversion. The conversion is not entirely precise and thus there are some mistakes. It is your task to correct these mistakes. It is important to consider the fact that it is an ophtalmologist diagnosis that is included in the provided text so correct this mistakes in such a way that the diagnosis makes sense.

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
"""},
            {"role": "user", "content": "Prosím oprav podle instrukcí tento text: " + text}
        ]
    )
    response = completion.choices[0].message.content
    response = json.loads(response)
    if response.get("recommendations") == []:
        response_text = response.get("text")
    else:
        response_text = response.get(
            "text") + "\nDoporučuji:\n" + "\n".join([f"• {rec}" for rec in response.get("recommendations")])
    return response_text


if __name__ == '__main__':
    app.run(debug=True)
