from brain.core_ai import process_command
from config.settings import APP_NAME, VERSION
from voice.text_to_speech import speak, stop_speaking
from voice.speech_to_text import listen

def start_goku():
    print(f"\n{'='*40}")
    print(f"  Welcome to {APP_NAME} v{VERSION}")
    print(f"  Your Personal AI Assistant")
    print(f"{'='*40}\n")
    print("Commands:")
    print("  'voice mode'  — talk to AURA")
    print("  'text mode'   — type to AURA")
    print("  'stop'        — stop speaking")
    print("  'read ...'    — read full response")
    print("  'bye'         — exit\n")

    speak("Hello! I am AURA, your Autonomous Universal Responsive Assistant. How can I help you?")

    voice_mode = False

    while True:
        try:
            if voice_mode:
                print("Listening...")
                user_input = listen()
            else:
                user_input = input("You: ").strip()

            if not user_input:
                continue

            # Stop speaking
            if user_input.lower().strip() in ["stop", "stop talking", "quiet", "silence", "shut up"]:
                stop_speaking()
                continue

            # Switch modes
            if user_input.lower() == "voice mode":
                voice_mode = True
                speak("Voice mode activated! I am listening.")
                continue

            if user_input.lower() == "text mode":
                voice_mode = False
                print("AURA: Text mode activated!")
                continue

            # Check if user wants full reading
            read_full = user_input.lower().startswith("read ")

            # Process command
            intent, response = process_command(user_input)
            speak(response, read_full=read_full)

            if intent == "shutdown":
                break

        except KeyboardInterrupt:
            speak("Goodbye!")
            break

if __name__ == "__main__":
    start_goku()