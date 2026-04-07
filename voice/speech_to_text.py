import speech_recognition as sr

recognizer = sr.Recognizer()

def listen():
    try:
        with sr.Microphone() as source:
            print("🎤 Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        print("Could not understand audio")
        return ""
    except sr.RequestError:
        print("Speech service unavailable")
        return ""
    except Exception as e:
        print(f"Microphone error: {e}")
        return ""