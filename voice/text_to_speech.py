import pyttsx3
import json
import os
import re
import threading

VOICE_SETTINGS_FILE = "memory/voice_settings.json"
_engine = None
_speaking_thread = None

def load_settings():
    if os.path.exists(VOICE_SETTINGS_FILE):
        with open(VOICE_SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"voice_index": 0, "speed": 170}

def save_settings(settings):
    with open(VOICE_SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

def set_voice_preference(voice=None, speed=None):
    settings = load_settings()
    if voice == "male":
        settings["voice_index"] = 1
    elif voice == "female":
        settings["voice_index"] = 0
    if speed == "slow":
        settings["speed"] = 130
    elif speed == "normal":
        settings["speed"] = 170
    elif speed == "fast":
        settings["speed"] = 210
    save_settings(settings)
    print(f"Saved — Voice index: {settings['voice_index']} | Speed: {settings['speed']}")

def get_voice_preference():
    settings = load_settings()
    return settings["voice_index"], settings["speed"]

def clean_text(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+', '', text)
    text = re.sub(r'`+', '', text)
    text = re.sub(r'\-\-+', '', text)
    text = re.sub(r'\[|\]|\(|\)', '', text)
    text = re.sub(r'>\s*', '', text)
    text = re.sub(r'\|', '', text)
    text = re.sub(r'_{2,}', '', text)
    text = re.sub(r'\n+', '. ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def stop_speaking():
    global _engine
    try:
        if _engine:
            _engine.stop()
            print("AURA: Stopped.")
    except:
        pass

def _speak_worker(text, settings):
    global _engine
    try:
        _engine = pyttsx3.init()
        voices = _engine.getProperty('voices')
        _engine.setProperty('voice', voices[settings["voice_index"]].id)
        _engine.setProperty('rate', settings["speed"])
        _engine.setProperty('volume', 1.0)
        _engine.say(text)
        _engine.runAndWait()
    except:
        pass
    finally:
        _engine = None

def speak(text, read_full=False):
    global _speaking_thread

    print(f"AURA: {text}")

    try:
        settings = load_settings()
        clean = clean_text(text)
        sentences = split_sentences(clean)

        if read_full:
            speak_text = clean
        else:
            speak_text = " ".join(sentences[:3])

        stop_speaking()

        _speaking_thread = threading.Thread(
            target=_speak_worker,
            args=(speak_text, settings),
            daemon=True
        )
        _speaking_thread.start()

    except Exception as e:
        print(f"Voice error: {e}")