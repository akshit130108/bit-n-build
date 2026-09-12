from land_audio_adapter import classify_audio
import sys


if len(sys.argv) < 2:
    print("Usage: python3 src/demo_land.py <audio_file>")
    sys.exit(1)


audio_file = sys.argv[1]

event = classify_audio(
    audio_file,
    sensor_id="LAND-01",
    location={
        "lat": 12.2958,
        "lon": 76.6394
    }
)

print("\nEcoSentinel Land Event:")
print(event)