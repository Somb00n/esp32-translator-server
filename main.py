import os
from fastapi import FastAPI, UploadFile, File, Form, Response
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
from pydub import AudioSegment
import imageio_ffmpeg

# กำหนดให้ pydub เรียกใช้ ffmpeg จาก imageio_ffmpeg เพื่อแปลงไฟล์ audio บน Cloud
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "online", "message": "ESP32 Translator Server is running"}

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...), src_lang: str = Form(...)):
    temp_wav = "temp_rec.wav"
    try:
        contents = await file.read()
        with open(temp_wav, "wb") as f:
            f.write(contents)

        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav) as source:
            # ตัดเสียงรบกวนบรรยากาศ/พัดลม 0.3 วินาทีแรก
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio_data = recognizer.record(source)

        lang_code = "th-TH" if src_lang == "th" else "my-MM"
        text = recognizer.recognize_google(audio_data, language=lang_code)

        if os.path.exists(temp_wav):
            os.remove(temp_wav)

        return {"text": text}

    except sr.UnknownValueError:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        return {"text": None}
    except Exception as e:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        return {"error": str(e), "text": None}

@app.post("/translate_tts")
async def translate_and_tts(text: str = Form(...), src_lang: str = Form(...), target_lang: str = Form(...)):
    out_mp3 = "temp_out.mp3"
    out_wav = "temp_out.wav"
    try:
        # 1. แปลภาษา
        translated_text = GoogleTranslator(source=src_lang, target=target_lang).translate(text)

        # 2. แปลงข้อความแปลเป็นเสียง (gTTS)
        tts = gTTS(text=translated_text, lang=target_lang)
        tts.save(out_mp3)

        # 3. แปลง MP3 เป็น WAV (16kHz Mono) สำหรับลำโพง ESP32
        sound = AudioSegment.from_mp3(out_mp3)
        sound = sound.set_frame_rate(16000).set_channels(1)
        sound.export(out_wav, format="wav")

        with open(out_wav, "rb") as f:
            wav_bytes = f.read()

        if os.path.exists(out_mp3): os.remove(out_mp3)
        if os.path.exists(out_wav): os.remove(out_wav)

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={"X-Translated-Text": translated_text}
        )

    except Exception as e:
        if os.path.exists(out_mp3): os.remove(out_mp3)
        if os.path.exists(out_wav): os.remove(out_wav)
        return Response(content=str(e), status_code=500)
