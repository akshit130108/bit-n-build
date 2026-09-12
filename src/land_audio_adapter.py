
import librosa
import numpy as np
import joblib
import json
from datetime import datetime


MODEL_PATH = "models/land_audio_model.joblib"
SUPPORTED_AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg", ".m4a")


# Load trained model
model = joblib.load(MODEL_PATH)


def extract_features(file_path):
    """
    Convert an audio file into the same 40 MFCC features
    used during model training.
    """

    y, sr = librosa.load(
        file_path,
        sr=22050,
        mono=True
    )

    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=40
    )

    features = np.mean(mfcc, axis=1)

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
    if confidence < 0.60:
        prediction = "unknown"

    # Create normalized event
    event = {
    "domain": "land",
    "event_type": str(prediction),
    "confidence": round(confidence, 3),
    "sensor_id": sensor_id,
    "timestamp": datetime.now().isoformat(),
    "location": location
}

    return json.dumps(event)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 src/land_audio_adapter.py <audio_file>")
        sys.exit(1)

    audio_file = sys.argv[1]

    event = classify_audio(audio_file)

    print(event)
