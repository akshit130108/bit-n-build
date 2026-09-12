
import librosa
import numpy as np
import joblib
import json
from datetime import datetime

import os
import uuid
import httpx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "land_audio_model.joblib"
)
SUPPORTED_AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg", ".m4a")


# Load trained model
model = joblib.load(MODEL_PATH)


def extract_features(file_path):
    """
    Convert an audio file into the same 80-feature
    representation used during model training.
    """

    y, sr = librosa.load(
        file_path,
        sr=22050,
        mono=True
    )

    y = y / (np.max(np.abs(y)) + 1e-9)

    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=40
    )

    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_std = np.std(mfcc, axis=1)

    delta = librosa.feature.delta(mfcc)
    delta_mean = np.mean(delta, axis=1)

    features = np.hstack([
    mfcc_mean,
    mfcc_std,
    delta_mean
])

    return features


def classify_audio(file_path, sensor_id="S01", location=None):    
    """
    Take a raw audio file and return a normalized
    EcoSentinel land event.
    """
    if location is None:
        location = {"lat": 12.9716, "lon": 77.5946}

    # Extract features
    features = extract_features(file_path)

    # Model expects a batch of samples
    features = features.reshape(1, -1)

    # Predict event
    prediction = model.predict(features)[0]

    # Get confidence
    probabilities = model.predict_proba(features)[0]
    confidence = float(np.max(probabilities))
    dangerous = ["chainsaw", "gunshot"]

    if prediction in dangerous and confidence < 0.60:
        prediction = "unknown"

    # Create normalized event
    event = {
        "id": f"evt_audio_{uuid.uuid4().hex[:8]}",
        "domain": "land",
        "event_type": str(prediction),
        "confidence": round(confidence, 3),
        "sensor_id": sensor_id,
        "timestamp": datetime.now().isoformat(),
        "location": location,
        "metadata": {
            "source": "land_audio_ml",
            "dangerous_threat": prediction in dangerous,
            "raw_prediction": str(prediction),
        },
    }

    return json.dumps(event)


def post_to_person3(event, backend_url="http://localhost:8000/events", timeout_sec=5.0):
    """
    Send normalized land event to Person 3 reasoning pipeline.
    Accepts either a JSON string or dict.
    """
    payload = json.loads(event) if isinstance(event, str) else event
    response = httpx.post(backend_url, json=payload, timeout=timeout_sec)
    response.raise_for_status()
    return response.json()



if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 src/land_audio_adapter.py <audio_file>")
        sys.exit(1)

    audio_file = sys.argv[1]

    event = classify_audio(audio_file)

    print(event)
