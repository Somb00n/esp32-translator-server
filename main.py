@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...), src_lang: str = Form(...)):
    # บันทึกไฟล์ที่รับมาจาก ESP32
    temp_wav = "temp_rec.wav"
    with open(temp_wav, "wb") as f:
        f.write(await file.read())

    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(temp_wav) as source:
            # 1. วิเคราะห์และตัดเสียงพัดลม/เสียงบรรยากาศรอบข้างอัตโนมัติ (0.3 วินาทีแรก)
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            
            # 2. อ่านข้อมูลเสียงหลังจากตัด Noise ออกแล้ว
            audio_data = recognizer.record(source)

        # 3. ส่งไปถอดความที่ Google STT
        lang_code = "th-TH" if src_lang == "th" else "my-MM"
        text = recognizer.recognize_google(audio_data, language=lang_code)
        
        return {"text": text}

    except sr.UnknownValueError:
        return {"text": None} # จับคำพูดไม่ได้
    except Exception as e:
        return {"error": str(e)}
