from land_audio_adapter import classify_audio
import sounddevice as sd
import soundfile as sf
import sys
import time

SAMPLE_RATE = 22050
DURATION = 5
TEMP_FILE = "data/live_test.wav"


def print_event(event):
    print("\n🌱 EcoSentinel Land Event:")
    print(event)
    print("\n" + "-" * 45 + "\n")


# TEST FILE MODE
if len(sys.argv) >= 2:
    audio_file = sys.argv[1]

    print("\n🧪 EcoSentinel Test Audio Mode")
    print("=" * 45)
    print(f"Audio file: {audio_file}")
    print("🔎 Classifying...")

    event = classify_audio(
        audio_file,
        sensor_id="LAND-01",
        location={
            "lat": 12.2958,
            "lon": 76.6394
        }
    )

    print_event(event)
    sys.exit(0)


# LIVE MICROPHONE MODE
print("\n🎤 EcoSentinel Live Land Audio Detection")
print("=" * 45)
print("The system will listen for 5 seconds at a time.")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        print("🎙️ Listening for 5 seconds...")

        audio = sd.rec(
            int(DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32"
        )

        sd.wait()

        sf.write(TEMP_FILE, audio, SAMPLE_RATE)

        print("🔎 Classifying...")

        event = classify_audio(
            TEMP_FILE,
            sensor_id="LAND-01",
            location={
                "lat": 12.2958,
                "lon": 76.6394
            }
        )

        print_event(event)

        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Live detection stopped.")