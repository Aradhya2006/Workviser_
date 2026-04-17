import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report
import os
import json

# ─── Config ───────────────────────────────────────────

DATASET_PATH = "dataset/Data_set_vector_for_mental_health_in_IT_industry.csv"
MODEL_SAVE_PATH = "saved_model"
BASE_MODEL = "bert-base-uncased"

LABELS = [
    "confused", "focused", "annoyed", "stressed",
    "exhausted", "break", "giveup", "trying",
    "needassistance", "waiting"
]

MAX_LENGTH = 128
BATCH_SIZE = 16
EPOCHS = 3
LEARNING_RATE = 2e-5

print("✅ Config loaded")
print(f"   Labels: {LABELS}")
print(f"   Epochs: {EPOCHS}")
print(f"   Batch size: {BATCH_SIZE}")

# ─── Step 1: Load Dataset ─────────────────────────────

print("\n📂 Loading dataset...")

df = pd.read_csv(DATASET_PATH, encoding="latin1")

print(f"✅ Dataset loaded: {len(df)} rows")
print(f"   Columns: {list(df.columns)}")

# Drop rows where Response is empty
df = df.dropna(subset=["Response"])
df = df.reset_index(drop=True)

print(f"✅ After cleaning: {len(df)} rows")

# Show label distribution
print("\n📊 Label distribution:")
for label in LABELS:
    count = df[label].sum()
    print(f"   {label}: {count}")

# ─── Step 2: Prepare Data ─────────────────────────────

print("\n🔧 Preparing data...")

texts = df["Response"].tolist()
labels_matrix = df[LABELS].values.astype(float)

print(f"✅ Texts: {len(texts)}")
print(f"✅ Labels matrix shape: {labels_matrix.shape}")

# Split into train and test
X_train, X_test, y_train, y_test = train_test_split(
    texts,
    labels_matrix,
    test_size=0.2,
    random_state=42
)

print(f"✅ Train size: {len(X_train)}")
print(f"✅ Test size: {len(X_test)}")

# ─── Step 3: Tokenizer ────────────────────────────────

print("\n🔤 Loading BERT tokenizer...")
tokenizer = BertTokenizer.from_pretrained(BASE_MODEL)
print("✅ Tokenizer loaded")

# ─── Step 4: Dataset Class ────────────────────────────

class EmotionDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        # Tokenize the text
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels": torch.tensor(label, dtype=torch.float)
        }

# Create datasets
train_dataset = EmotionDataset(X_train, y_train, tokenizer, MAX_LENGTH)
test_dataset = EmotionDataset(X_test, y_test, tokenizer, MAX_LENGTH)

# Create dataloaders
train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

print(f"✅ Train batches: {len(train_loader)}")
print(f"✅ Test batches: {len(test_loader)}")

# ─── Step 5: Load BERT Model ──────────────────────────

print("\n🤖 Loading BERT model...")

model = BertForSequenceClassification.from_pretrained(
    BASE_MODEL,
    num_labels=len(LABELS),
    problem_type="multi_label_classification"
)

# Use GPU if available, else CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

print(f"✅ Model loaded")
print(f"   Device: {device}")
print(f"   Labels: {len(LABELS)}")

# ─── Step 6: Training ─────────────────────────────────

print("\n🚀 Starting training...")

optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
loss_fn = torch.nn.BCEWithLogitsLoss()

for epoch in range(EPOCHS):
    model.train()
    total_loss = 0
    correct_batches = 0

    print(f"\n📖 Epoch {epoch + 1}/{EPOCHS}")

    for batch_idx, batch in enumerate(train_loader):
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        # Forward pass
        optimizer.zero_grad()
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        # Calculate loss
        loss = loss_fn(outputs.logits, labels)
        total_loss += loss.item()

        # Backward pass
        loss.backward()
        optimizer.step()

        # Print progress every 50 batches
        if (batch_idx + 1) % 50 == 0:
            print(f"   Batch {batch_idx + 1}/{len(train_loader)} "
                  f"| Loss: {loss.item():.4f}")

    avg_loss = total_loss / len(train_loader)
    print(f"✅ Epoch {epoch + 1} done | Avg Loss: {avg_loss:.4f}")

# ─── Step 7: Evaluation ───────────────────────────────

print("\n📊 Evaluating model...")

model.eval()
all_preds = []
all_labels = []

with torch.no_grad():
    for batch in test_loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        # Convert logits to predictions
        preds = torch.sigmoid(outputs.logits)
        preds = (preds > 0.5).float()

        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

all_preds = np.array(all_preds)
all_labels = np.array(all_labels)

# F1 Score
f1 = f1_score(all_labels, all_preds, average="micro", zero_division=0)
print(f"✅ F1 Score (micro): {f1:.4f}")

# Per label report
print("\n📋 Per-label report:")
print(classification_report(
    all_labels,
    all_preds,
    target_names=LABELS,
    zero_division=0
))

# ─── Step 8: Save Model ───────────────────────────────

print("\n💾 Saving model...")

os.makedirs(MODEL_SAVE_PATH, exist_ok=True)

model.save_pretrained(MODEL_SAVE_PATH)
tokenizer.save_pretrained(MODEL_SAVE_PATH)

# Save label names so emotion_detector.py can load them
with open(f"{MODEL_SAVE_PATH}/labels.json", "w") as f:
    json.dump(LABELS, f)

print(f"✅ Model saved to: {MODEL_SAVE_PATH}/")
print(f"✅ Labels saved to: {MODEL_SAVE_PATH}/labels.json")
print("\n🎉 Training complete!")


# Explanation — What Each Step Does
# Step 1 — Load Dataset

# Reads your CSV with latin1 encoding
# Drops empty rows
# Shows label distribution

# Step 2 — Prepare Data

# Separates text and labels
# Splits 80% train, 20% test
# labels_matrix is a 16466 × 10 array of 0s and 1s

# Step 3 — Tokenizer

# Downloads BERT tokenizer from HuggingFace
# Converts text to numbers BERT understands

# Step 4 — Dataset Class

# EmotionDataset wraps our data
# __getitem__ tokenizes one row at a time
# DataLoader feeds batches to the model

# Step 5 — Load BERT

# Downloads bert-base-uncased
# num_labels=10 → one output per emotion
# multi_label_classification → multiple emotions can be true at once
# Moves to GPU if available, else CPU

# Step 6 — Training

# BCEWithLogitsLoss → right loss for multi-label
# AdamW → best optimizer for BERT
# 3 epochs → good balance of speed and accuracy
# Prints loss every 50 batches so you can watch progress

# Step 7 — Evaluation

# sigmoid converts raw scores to 0-1 probabilities
# > 0.5 threshold → converts to 0 or 1 prediction
# F1 score → measures accuracy fairly for imbalanced labels
# Per-label report → shows which emotions model learned best

# Step 8 — Save Model

# Saves model weights to saved_model/
# Saves tokenizer to saved_model/
# Saves label names to saved_model/labels.json
# emotion_detector.py will load from here later