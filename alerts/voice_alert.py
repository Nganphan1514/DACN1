import hashlib
import os
import queue
import threading
import time

from gtts import gTTS

try:
    import pygame

    pygame.mixer.init()
    _HAS_PYGAME = True
except Exception:
    _HAS_PYGAME = False

try:
    from playsound import playsound
except Exception:
    playsound = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_CACHE_DIR = os.path.join(BASE_DIR, "assets", "audio")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

# Hang doi phat am thanh tuan tu, tranh xung dot file tam va spam
_speech_queue = queue.Queue(maxsize=4)
_worker_started = False
_worker_lock = threading.Lock()

last_warning_time = 0.0
warning_delay = 3.0


def _cache_path_for_text(text):
    digest = hashlib.md5(text.strip().encode("utf-8")).hexdigest()
    return os.path.join(AUDIO_CACHE_DIR, f"{digest}.mp3")


def _play_mp3(file_path):
    if _HAS_PYGAME:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
        return

    if playsound is not None:
        playsound(file_path)


def _speak_offline_fallback(text):
    if pyttsx3 is None:
        return
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print("Offline TTS Error:", e)


def play_voice(text):
    """
    Phat giong noi tu cache MP3 cuc bo.
    Neu chua co cache -> tao bang gTTS va luu lai de dung offline lan sau.
    Neu mat mang -> fallback sang pyttsx3.
    """
    try:
        cache_file = _cache_path_for_text(text)

        if not os.path.exists(cache_file):
            tmp_file = f"{cache_file}.{threading.get_ident()}.tmp"
            try:
                tts = gTTS(text=text, lang="vi", slow=False)
                tts.save(tmp_file)
                os.replace(tmp_file, cache_file)
            except Exception as e:
                print("gTTS offline/error, fallback pyttsx3:", e)
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except OSError:
                        pass
                _speak_offline_fallback(text)
                return

        _play_mp3(cache_file)

    except Exception as e:
        print("Voice Error:", e)
        _speak_offline_fallback(text)


def _speech_worker():
    while True:
        text = _speech_queue.get()
        try:
            if text:
                play_voice(text)
        finally:
            _speech_queue.task_done()


def _ensure_worker_running():
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            thread = threading.Thread(target=_speech_worker, daemon=True)
            thread.start()
            _worker_started = True


def speak_warning(text):
    global last_warning_time

    if not text:
        return

    current = time.time()
    if current - last_warning_time < warning_delay:
        return

    _ensure_worker_running()

    try:
        _speech_queue.put_nowait(text)
        last_warning_time = current
    except queue.Full:
        # Bo qua neu hang doi da day de khong bi tre canh bao cu
        pass
