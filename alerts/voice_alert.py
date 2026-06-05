from gtts import gTTS
from playsound import playsound

import threading
import time
import os


# COOLDOWN

last_warning_time = 0
warning_delay = 8


# TEMP FILE

TEMP_AUDIO = "temp_warning.mp3"



# PLAY VOICE

def play_voice(text):

    try:

        # xóa file cũ
        if os.path.exists(TEMP_AUDIO):

            try:
                os.remove(TEMP_AUDIO)
            except:
                pass

        # tạo voice tiếng Việt
        tts = gTTS(text=text, lang="vi", slow=False)

        tts.save(TEMP_AUDIO)

        playsound(TEMP_AUDIO)

        try:
            os.remove(TEMP_AUDIO)
        except:
            pass

    except Exception as e:

        print("Voice Error:", e)



# SPEAK WARNING

def speak_warning(text):

    global last_warning_time

    current_time = time.time()

    # chống spam
    if current_time - last_warning_time < warning_delay:
        return

    try:

        thread = threading.Thread(target=play_voice, args=(text,))

        thread.daemon = True

        thread.start()

        last_warning_time = current_time

    except Exception as e:

        print("Speak Error:", e)

