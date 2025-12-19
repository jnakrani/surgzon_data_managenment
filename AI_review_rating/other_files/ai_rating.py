import os
import time
import random
import pandas as pd
# from openai import OpenAI
from dotenv import load_dotenv
import google.generativeai as genai
from tqdm import tqdm

# Load API key
load_dotenv()
GEMINI_API_KEY2 = os.getenv("GEMINI_API_KEY2")
genai.configure(api_key=GEMINI_API_KEY2)

model = genai.GenerativeModel("gemini-2.5-flash-lite")

# Load CSV with AI_review column
# df = pd.read_csv("C:/tarun-bitcoding/Surgzon/AI_review_rating/Cross_Output.csv")

# Function to rate review
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
            response = model.generate_content(prompt)
            end_row = time.time()

            print(f"⏱️ Time taken for this row: {end_row - start_row:.2f} seconds")

            # Sleep between requests to avoid hitting API limits
            sleep_time = random.uniform(2, 5)  # random between 2–5 sec
            print(f"😴 Sleeping {sleep_time:.2f} seconds...\n")
            time.sleep(sleep_time)

            # Extract number only
            rating_str = response.text.strip()
            return int(rating_str[0]) if rating_str[0].isdigit() else None

        except Exception as e:
            print(f"⚠️ Error: {e}. Retrying in 10 seconds...")
            time.sleep(10)


# Automation: Process all CSVs
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

            # Add AI_rating column if missing
            if "AI_rating" not in df.columns:
                df["AI_rating"] = ""

            start_time = time.time()

            # Process row by row
            for idx in tqdm(range(len(df))):
                if pd.isna(df.at[idx, "AI_rating"]) or df.at[idx, "AI_rating"] == "":
                    review = df.at[idx, "AI_review"]
                    df.at[idx, "AI_rating"] = generate_rating(review)

                    # ✅ Save progress immediately
                    df.to_csv(output_path, index=False)

            end_time = time.time()
            print(f"✅ Completed {file} -> {output_file}")
            print(f"⏳ Total time: {end_time - start_time:.2f} seconds")

# ------------------------------
# Example Usage
# ------------------------------
if __name__ == "__main__":
    input_folder = "OutputFiles_01"   # input folder containing review CSVs  AI_review_rating/OutputFiles_01 AI_review_rating/OutputFiles_Long-des
    output_folder = "OutputRatings"         # output folder 
    process_folder(input_folder, output_folder)












# # Apply with progress bar
# tqdm.pandas()

# start_time = time.time()

# df["AI_rating"] = df["AI_review"].progress_apply(generate_rating)

# # Save updated CSV
# df.to_csv("main_output/Cross_Output_Review&Rating.csv", index=False)

# end_time = time.time()

# print("✅ Ratings generated and saved!")
# print(f"⏳ Total time taken: {end_time - start_time:.2f} seconds")

