import os
import numpy as np
from land_audio_adapter import model, extract_features
CLASSES = [
    "chainsaw",
    "gunshot",
    "wildlife",
    "background"
]

correct = 0
total = 0

for true_label in CLASSES:

    folder = f"../data/{true_label}"
    print("\n" + "="*50)
    print("Testing:", true_label)
    print("="*50)

    class_correct = 0
    class_total = 0

    for file in os.listdir(folder):

        if not file.endswith(".wav"):
            continue

        path = os.path.join(folder, file)

        features = extract_features(path).reshape(1, -1)

        prediction = model.predict(features)[0]

        probs = model.predict_proba(features)[0]
        confidence = float(np.max(probs))

        print(
            f"{file[:20]:20s}",
            "->",
            prediction,
            round(confidence,3)
        )

        total += 1
        class_total += 1

        if prediction == true_label:
            correct += 1
            class_correct += 1

    acc = class_correct / class_total * 100

    print(
        f"\n{true_label} accuracy:",
        round(acc,2),
        "%"
    )

overall = correct / total * 100

print("\n" + "="*50)
print("OVERALL ACCURACY:", round(overall,2), "%")
print("="*50)