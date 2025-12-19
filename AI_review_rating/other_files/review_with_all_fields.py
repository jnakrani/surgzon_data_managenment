import os
import time
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Load CSV
df = pd.read_csv("Data/product_files/Extremity_split_top_bottom7.csv")

# Function to generate review
def generate_review(row):
    product_name = row["product_name_displayed"]
    # Include ALL columns as context
    context = "\n".join([f"{col}: {row[col]}" for col in df.columns])

    prompt = f"""
    You are writing a professional **customer-style review** for a medical product.
    The review should sound like it comes from a surgeon, doctor, or patient using the device,
    not from the manufacturer. Keep it realistic, balanced (mention both strengths and limitations),
    and about 5-10 sentences.

    Here are the details:
    {context}

    Write the review for "{product_name}" considering the above details.
    """
    start_row = time.time()
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Or gpt-4o
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250,
        temperature=0.7
    )
    end_row = time.time()
    print(f"⏱️ Time taken for this row: {end_row - start_row:.2f} seconds")
    return response.choices[0].message.content.strip()

# Apply with progress bar
tqdm.pandas()

start_time = time.time()

df["AI_review"] = df.progress_apply(generate_review, axis=1)

# Save to new CSV
df.to_csv("Extremity_medical_with_AI_reviews.csv", index=False)

end_time = time.time()
print("✅ Reviews generated and saved")
print(f"⏳ Total time taken: {end_time - start_time:.2f} seconds")