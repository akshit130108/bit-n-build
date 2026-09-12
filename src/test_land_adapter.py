from land_audio_adapter import classify_audio

audio_file = "data/gunshot/" + __import__("os").listdir("data/gunshot")[0]
event = classify_audio(
    audio_file,
    sensor_id="S01",
    location={
        "lat": 12.2958,
        "lon": 76.6394
    }
)

print(event)