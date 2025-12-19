import pandas as pd
import spacy, random, os
from spacy.training import Example


# ==========================
# CONFIG
# ==========================
INPUT_FILE = "C:/tarun-bitcoding/Surgzon/Data_Extractor/SZO-sample-file.xlsx"
MODEL_DIR = "product_ner_model"
TARGET_FIELDS = ["company","product","warranty","length","diameter","height", "coated", "thickness", "constrained", "cannulated", "cancellous", "thread", "locking", "other", "size", "compression", "shape", "loop", "bone", "flat", "wedge", "side", "angle", "position", "offset", "sterile"]
# ==========================

print("📥 Loading Excel...")
df = pd.read_excel(INPUT_FILE, header=1)   # <-- use 2nd row as header
df.columns = [c.strip() for c in df.columns]  # remove any extra spaces
print("📋 Columns in file:", list(df.columns))

# Normalize column names (replace _ with space and strip)
df.columns = [c.strip() for c in df.columns]

df['text'] = df['Product_Code'].astype(str) + " " + df['Device_Description'].astype(str)


print("📝 Building training data...")
TRAIN_DATA = []
for _, row in df.iterrows():
    text = row['text']
    entities = []
    for label in TARGET_FIELDS:
        val = str(row.get(label,"")).strip()
        if val and val.lower() != "nan":
            start = text.find(val)
            if start != -1:
                entities.append((start, start+len(val), label.upper()))
    if entities:
        TRAIN_DATA.append((text, {"entities": entities}))

print(f"Training samples: {len(TRAIN_DATA)}")

# --------------------------
# Train spaCy model
# --------------------------
print("🤖 Training spaCy model...")
nlp = spacy.blank("en")
ner = nlp.add_pipe("ner")

for _, ann in TRAIN_DATA:
    for _,_,label in ann['entities']:
        ner.add_label(label)

optimizer = nlp.initialize()


for i in range(30):
    random.shuffle(TRAIN_DATA)
    losses = {}
    for text, ann in TRAIN_DATA:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, ann)
        nlp.update([example], drop=0.3, losses=losses)
    print(f"Epoch {i+1} loss:", losses)

os.makedirs(MODEL_DIR, exist_ok=True)
nlp.to_disk(MODEL_DIR)
print("✅ Model saved to", MODEL_DIR)
