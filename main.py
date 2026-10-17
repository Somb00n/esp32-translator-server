from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
import io
import os
from pydub import AudioSegment
import imageio_ffmpeg

# ดึงตำแหน่ง ffmpeg อัตโนมัติ ป้องกันปัญหา 500 Internal Server Error
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

app = FastAPI()

@app.post("/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    src_lang: str = Form("th")
):
    audio_data = await file.read()
    temp_filename = "stt_temp.wav"
    with open(temp_filename, "wb") as f:
        f.write(audio_data)

    recognizer = sr.Recognizer()
    original_text = ""
    try:
        with sr.AudioFile(temp_filename) as source:
            audio = recognizer.record(source)
        original_text = recognizer.recognize_google(audio, language=src_lang)
        print(f"[STT Success] Recognized Text: {original_text}")
    except Exception as e:
        original_text = "ฟังไม่ชัด กรุณาพูดใหม่"
        print(f"[STT Error] {e}")

    if os.path.exists(temp_filename):
        os.remove(temp_filename)

    return JSONResponse(content={"text": original_text})


@app.post("/translate_tts")
async def translate_and_tts(
    text: str = Form(...),
    src_lang: str = Form("th"),
    target_lang: str = Form("my")
):
    print(f"[Translate] Processing: '{text}' ({src_lang} -> {target_lang})")
    try:
        translated_text = GoogleTranslator(source=src_lang, target=target_lang).translate(text)
        print(f"[Translated Result]: {translated_text}")
    except Exception as e:
        translated_text = text
        print(f"[Translate Error]: {e}")

    wav_buf = io.BytesIO()
    try:
        # 1. สร้างไฟล์เสียง MP3 จาก gTTS
        mp3_buf = io.BytesIO()
        tts = gTTS(text=translated_text, lang=target_lang)
        tts.write_to_fp(mp3_buf)
        mp3_buf.seek(0)

        # 2. แปลงไฟล์ MP3 เป็น PCM WAV (16-bit, 16000Hz, Mono) ส่งให้ ESP32
        sound = AudioSegment.from_file(mp3_buf, format="mp3")
        sound = sound.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        sound.export(wav_buf, format="wav")
        wav_buf.seek(0)
    except Exception as e:
        print(f"[TTS Error]: {e}")

    headers = {
        "X-Translated-Text": translated_text,
        "Access-Control-Expose-Headers": "X-Translated-Text"
    }
    return StreamingResponse(wav_buf, media_type="audio/wav", headers=headers)