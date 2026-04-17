import torch
import json
import os
from transformers import AutoTokenizer, BertForSequenceClassification

# Config
MODEL_PATH = r"C:\Users\Aradhya\Desktop\workviser\ml\saved_model\saved_model"

MAX_LENGTH = 128
THRESHOLD = 0.3

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found at: {MODEL_PATH}")

print(f"Loading emotion model from: {MODEL_PATH}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = BertForSequenceClassification.from_pretrained(MODEL_PATH)
model.eval()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

with open(os.path.join(MODEL_PATH, "labels.json"), "r") as f:
    LABELS = json.load(f)

print(f"Emotion model loaded — {len(LABELS)} labels — Device: {device}")


def predict_emotions(text: str) -> dict:
    if not text or len(text.strip()) == 0:
        return {}

    inputs = tokenizer(
        text,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt"
    )

    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)

    with torch.no_grad():
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

    probs = torch.sigmoid(outputs.logits).squeeze().cpu().numpy()

    result = {}
    for label, score in zip(LABELS, probs):
        score_float = float(score)
        if score_float >= THRESHOLD:
            result[label] = round(score_float, 4)

    result = dict(
        sorted(result.items(), key=lambda x: x[1], reverse=True)
    )

    return result


def get_dominant_emotion(text: str) -> str:
    emotions = predict_emotions(text)
    if not emotions:
        return "none"
    return max(emotions, key=emotions.get)


def is_needs_help(text: str) -> bool:
    emotions = predict_emotions(text)
    help_signals = ["needassistance", "giveup", "confused", "stressed"]

    for signal in help_signals:
        if emotions.get(signal, 0) > 0.5:
            return True

    return False
# MODEL_PATH

# Points to your saved model folder
# Uses relative path so it works on any machine

# THRESHOLD = 0.3

# Only return emotions with score above 30%
# Filters out noise — weak signals ignored

# predict_emotions()

# Main function — takes text, returns emotion scores
# Returns only emotions above threshold
# Sorted by score so highest emotion comes first

# get_dominant_emotion()

# Returns just the top emotion as a string
# Used for quick checks

# is_needs_help()

# Returns True/False
# Checks if any of 4 key help signals are above 50%
# This is what triggers the help popup automatically   C:\Users\Aradhya\Desktop\workviser\ml\saved_model