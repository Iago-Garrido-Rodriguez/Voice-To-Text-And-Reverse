import pyaudio
import wave
import requests
import pygame
import os
import numpy as np
import time

# Configuración
SERVER_URL = "http://192.168.1.148:8000/process_audio/"  # Cambia esto por la IP del servidor
AUDIO_FILE = "recorded_audio.wav"
RESPONSE_FILE = "response.mp3"

# Configuración de audio
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
SILENCE_THRESHOLD = 500  # Nivel de silencio aceptable
SILENCE_DURATION = 2  # Segundos de silencio para detener la grabación

# Inicializar PyAudio
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

print("Listo para grabar... Habla cuando quieras.")

while True:
    frames = []
    silent_chunks = 0
    is_recording = False

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

        # Convertir los datos de audio a un array de numpy para calcular el volumen
        audio_array = np.frombuffer(data, dtype=np.int16)
        volume = np.abs(audio_array).mean()

        if volume > SILENCE_THRESHOLD:
            silent_chunks = 0
            if not is_recording:
                print("Detectando voz... Iniciando grabación.")
                is_recording = True
        else:
            silent_chunks += 1

        # Si ha habido suficiente silencio, detener la grabación
        if is_recording and silent_chunks > (SILENCE_DURATION * RATE / CHUNK):
            print("Silencio detectado. Deteniendo grabación.")
            break

    # Guardar el audio grabado
    with wave.open(AUDIO_FILE, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

    print("Enviando audio al servidor...")

    # Enviar el archivo de audio al servidor y PAUSAR la grabación mientras se procesa
    with open(AUDIO_FILE, 'rb') as f:
        files = {'file': f}
        response = requests.post(SERVER_URL, files=files)

    # SOLO CONTINUAR SI EL SERVIDOR RESPONDE BIEN
    if response.status_code == 200:
        print("Procesando respuesta... Pausando grabación.")
        
        # Guardar la respuesta de audio
        with open(RESPONSE_FILE, "wb") as f:
            f.write(response.content)

        print("Respuesta recibida. Reproduciendo...")

        # Reproducir el audio recibido
        pygame.mixer.init()
        pygame.mixer.music.load(RESPONSE_FILE)
        pygame.mixer.music.play()

        # ESPERAR HASTA QUE TERMINE LA REPRODUCCIÓN
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)  # Pequeña espera para no saturar la CPU

        print("\nRespuesta reproducida. Volviendo a escuchar...\n")
    
    else:
        print("Error al recibir la respuesta del servidor.")

    print("\nEsperando nueva grabación...\n")
