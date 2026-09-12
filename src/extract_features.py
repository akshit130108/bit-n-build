import os
import numpy as np
import librosa

DATA_DIR = "data"

CLASSES = [
    "chainsaw",
    "gunshot",
    "wildlife",
    "background"
]


def extract_features(file_path):
    y, sr = librosa.load(file_path, sr=22050, mono=True)

    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=40
    )

    features = np.mean(mfcc, axis=1)

    return features


X = []
y = []

for label in CLASSES:

    folder = os.path.join(DATA_DIR, label)

    print(f"\nProcessing {label}...")

    for filename in os.listdir(folder):

        if not filename.lower().endswith(".wav"):
            continue

        file_path = os.path.join(folder, filename)

        try:
            features = extract_features(file_path)

            X.append(features)
            y.append(label)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")


X = np.array(X)
y = np.array(y)

print("\nFeature extraction complete!")
print("Feature matrix shape:", X.shape)
print("Labels shape:", y.shape)

np.save("data/features.npy", X)
np.save("data/labels.npy", y)

print("Saved:")
print("  data/features.npy")
print("  data/labels.npy")