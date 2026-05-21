from gtts import gTTS
from playsound import playsound
import os
import time
import threading

# ==========================
# COOLDOWN
# ==========================
last_warning_time = 0
warning_delay = 8


def play_audio(file_name):

    try:

        playsound(file_name)

    except Exception as e:

        print("Play Error:", e)

    finally:

        if os.path.exists(file_name):

            try:

                os.remove(file_name)

            except:
                pass


def speak_warning(text):

    global last_warning_time

    current_time = time.time()

    # chống spam
    if current_time - last_warning_time < warning_delay:
        return

    try:

        tts = gTTS(text=text, lang="vi", slow=False)

        file_name = f"temp_" f"{int(time.time())}.mp3"

        tts.save(file_name)

        thread = threading.Thread(target=play_audio, args=(file_name,))

        thread.daemon = True
        thread.start()

    except Exception as e:

        print("Voice Error:", e)

    last_warning_time = current_time
