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
        model="gpt-4-turbo-preview",  # gpt-3.5-turbo, gpt-4-turbo-preview
        response_format={"type": "json_object"},
        temperature=0.0,
        messages=[
            {"role": "system", "content": """Jsi profesionální copywriter a tvůj úkol je opravit překlepy a gramatické chyby v následujícím textu.
             Text obsahuje diagnózu od oftalmologa a obsahuje odborné výrazy.
             Pokud v textu bude zmínka o doporučeních, chci aby jsi vrátil v jsonu také klíč "recommendations" a hodnotou s polem jednotlivých doporučení.
             Vracej json ve formátu {"text": "opravený text", "recommendations": [doporučení]. Pokud v textu nebude žádná zmínka
             o doporučeních, vracej pro klíč recommendations prázdné pole. V případě, že se v textu zmínka o doporučení vyskytne, neuváděj
             tuto část ve výsledné hodnotě pro klíč "text".} V případě, že si u některého slova jistý, může ho nechat nezměněné. Odpovídej POUZE V ČEŠTINĚ."""},
            {"role": "user", "content": "Zde je zmíněný text: " + text}
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
