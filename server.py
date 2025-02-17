from fastapi import FastAPI, File, UploadFile
import uvicorn
import os
import wave
import json
from vosk import Model, KaldiRecognizer
from gtts import gTTS
import ollama
from fastapi.responses import FileResponse

# Configuración del servidor y modelos
app = FastAPI()
VOSK_PATH = "C:\\vosk-model-es-0.42"
AUDIO_RESPONSE_PATH = "response.mp3"

# Verificar que el modelo de Vosk existe
if not os.path.exists(VOSK_PATH):
    raise ValueError(f"Vosk model not found in {VOSK_PATH}")

model = Model(VOSK_PATH)
recognizer = KaldiRecognizer(model, 16000)

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    # Guardar el archivo temporalmente
    file_path = f"uploads/{file.filename}"
    os.makedirs("uploads", exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Procesar el audio con Vosk (Speech-to-Text)
    with wave.open(file_path, "rb") as wf:
        rec = KaldiRecognizer(model, wf.getframerate())

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            rec.AcceptWaveform(data)

        result = json.loads(rec.FinalResult())

    recognized_text = result.get("text", "").lower()
    print(f"Texto reconocido: {recognized_text}")

    # Enviar el texto a Ollama 
    ollama_response = get_local_llm_response(recognized_text)

    # Convertir la respuesta en voz con gTTS
    tts = gTTS(ollama_response, lang="es")
    tts.save(AUDIO_RESPONSE_PATH)

    print(f"Respuesta generada: {ollama_response}")

    # Enviar el archivo de audio de vuelta a la Raspberry Pi
    return FileResponse(AUDIO_RESPONSE_PATH, media_type="audio/mpeg")


def get_local_llm_response(user_input):
    """
    Envía el texto del usuario a un modelo LLM local usando Ollama.
    """
    try:
        response = ollama.chat(
            model="llama3.2",  # Asegúrate de que este es el modelo correcto en Ollama
            messages=[{"role": "user", "content": user_input}]
        )
        return response["message"]["content"]

    except Exception as e:
        print("⚠ ERROR en la solicitud a Ollama:", str(e))
        return "No pude conectarme al servidor de IA."


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)