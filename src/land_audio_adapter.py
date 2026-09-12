try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    librosa = None
    HAS_LIBROSA = False

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


def get_or_create_model():
    """Load trained model or initialize baseline if missing."""
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except Exception:
            pass

    # Baseline fallback model with 4 EcoSentinel land audio classes
    from sklearn.ensemble import RandomForestClassifier
    classes = ["chainsaw", "gunshot", "wildlife", "background"]
    np.random.seed(42)
    X = []
    y = []
    for idx, cls in enumerate(classes):
        cluster_center = np.zeros(80)
        cluster_center[idx * 20 : (idx + 1) * 20] = 1.5 + idx
        samples = np.random.normal(loc=cluster_center, scale=0.5, size=(30, 80))
        X.append(samples)
        y.extend([cls] * 30)

    fallback_model = RandomForestClassifier(n_estimators=30, random_state=42)
    fallback_model.fit(np.vstack(X), y)
    try:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(fallback_model, MODEL_PATH)
    except Exception:
        pass
    return fallback_model


# Initialize model
model = get_or_create_model()


def extract_features(file_path):
    """
    Convert an audio file into the 80-feature representation
    (MFCC mean, MFCC std, delta mean) used during model training.
    """
    if HAS_LIBROSA:
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
    else:
        # Resilient fallback using scipy when librosa C-libraries are absent
        try:
            from scipy.io import wavfile
            sr, data = wavfile.read(file_path)
            if data.ndim > 1:
                data = data.mean(axis=1)
            data = data.astype(np.float32) / (np.max(np.abs(data)) + 1e-9)
            fft_vals = np.abs(np.fft.rfft(data[: min(len(data), 22050)]))
            fft_bins = np.array_split(fft_vals, 40)
            mean_bins = np.array([float(np.mean(b)) if len(b) > 0 else 0.0 for b in fft_bins])
            std_bins = np.array([float(np.std(b)) if len(b) > 0 else 0.0 for b in fft_bins])
            return np.hstack([mean_bins, std_bins])
        except Exception:
            # Fallback 80-dim feature vector
            return np.zeros(80)


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
