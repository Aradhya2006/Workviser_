from transformers import BertTokenizer, BertForSequenceClassification
import torch
import json
import os

#  Path to your trained model
MODEL_PATH = "ml/saved_model/saved_model"   

# Check path exists
if not os.path.exists(MODEL_PATH):
    raise Exception(f"Model path not found: {MODEL_PATH}")

print(f" Loading model from: {MODEL_PATH}")

#  FIX: Load tokenizer from base model (since yours missing)
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

#  Load trained model
model = BertForSequenceClassification.from_pretrained(MODEL_PATH)

#  Load labels
with open(os.path.join(MODEL_PATH, "labels.json")) as f:
    LABELS = json.load(f)

model.eval()

#  Prediction function
def predict(text):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.sigmoid(outputs.logits)[0]

    results = {label: float(prob) for label, prob in zip(LABELS, probs)}

    #  Return top 3 predictions
    top3 = sorted(results.items(), key=lambda x: x[1], reverse=True)[:3]

    return top3


#  Test cases
tests = [
    "I am feeling very stressed and tired",
    "I am stuck and need help",
    "this bug is so annoying",
    "finally completed my task feeling good",
    "i need a break asap"
]

for t in tests:
    print("\n Input:", t)
    print(" Prediction:", predict(t))