import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty("voices")

for i, voice in enumerate(voices):

    print("=" * 50)

    print("INDEX:", i)

    print("ID:", voice.id)

    print("NAME:", voice.name)

    print("LANGUAGES:", voice.languages)

    print("=" * 50)
