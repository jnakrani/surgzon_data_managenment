import os
import time
import random
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI

# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_rating(review):
    prompt = f"""
    You are a strict medical product reviewer.
    Based on the following review, assign a star rating (1 to 5) from a customer perspective.
    
    Review:
    "{review}"
    
    Rules:
    - 1 = Very bad (unsafe, poor, not recommended)
    - 2 = Poor (limited use, dissatisfaction, more negatives than positives)
    - 3 = Neutral/Average (some positives and some negatives)
    - 4 = Good (mostly positive, only minor drawbacks)
    - 5 = Excellent (strongly positive, highly recommended)
    
    Only return the number (1-5), no extra words.
    """

    while True:
        try:
            start_row = time.time()

            response = client.chat.completions.create(
                model="gpt-4o-mini",   # 🔄 You can change model (gpt-4o, gpt-4.1, gpt-3.5-turbo, etc.)
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0
            )

            end_row = time.time()
            print(f"⏱️ Time taken for this row: {end_row - start_row:.2f} seconds")

            sleep_time = random.uniform(2, 5)  
            print(f"😴 Sleeping {sleep_time:.2f} seconds...\n")
            time.sleep(sleep_time)

            rating_str = response.choices[0].message.content.strip()
            return int(rating_str[0]) if rating_str[0].isdigit() else None

        except Exception as e:
            print(f"⚠️ Error: {e}. Retrying in 10 seconds...")
            time.sleep(10)

def process_folder(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    tqdm.pandas()

    for file in os.listdir(input_folder):
        if file.endswith(".csv"):
            input_path = os.path.join(input_folder, file)
            output_file = os.path.splitext(file)[0] + "AI-Review&Rating.csv"
            output_path = os.path.join(output_folder, output_file)

            print(f"\n📂 Processing file: {file}")

            df = pd.read_csv(input_path)

            if "AI_rating" not in df.columns:
                df["AI_rating"] = ""

            start_time = time.time()

            # Process row by row
            for idx in tqdm(range(len(df))):
                if pd.isna(df.at[idx, "AI_rating"]) or df.at[idx, "AI_rating"] == "":
                    review = df.at[idx, "AI_review"]
                    df.at[idx, "AI_rating"] = generate_rating(review)

                    df.to_csv(output_path, index=False)

            end_time = time.time()
            print(f"✅ Completed {file} -> {output_file}")
            print(f"⏳ Total time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    input_folder = "OutputFiles_01"   
    output_folder = "OutputRatings"    
    process_folder(input_folder, output_folder)