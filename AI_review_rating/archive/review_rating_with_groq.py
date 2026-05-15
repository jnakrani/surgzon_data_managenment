import os
import time
import random
import pandas as pd
from tqdm import tqdm
from itertools import cycle
from dotenv import load_dotenv
import google.generativeai as genai
from azure.storage.blob import BlobServiceClient
from io import StringIO, BytesIO 
from logger_functionality import logger
from groq import Groq  # import Groq client
# ---------------- Azure Setup ----------------
load_dotenv()
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)

API_KEYS = [
    os.getenv("GROQ_API_KEY_"),
    os.getenv("GROQ_API_KEY_0"),
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_4"),
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_5"),
    os.getenv("GROQ_API_KEY_6"),
]

# Remove None values
API_KEYS = [k for k in API_KEYS if k]

if not API_KEYS:
    raise ValueError("❌ No GROQ_API_KEYs found in .env")

# Cycle through keys
api_key_cycle = cycle(API_KEYS)
current_api_key = next(api_key_cycle)

total_tokens_used = 0

def get_groq_client():
    """Return a Groq client with the current API key."""
    global current_api_key
    return Groq(api_key=current_api_key)

def rotate_api_key():
    """Move to the next API key in cycle."""
    global current_api_key
    current_api_key = next(api_key_cycle)
    logger.warning(f"🔄 Rotating API key. Now using: {current_api_key[:6]}...")
    return get_groq_client()

def call_groq(messages, model="llama-3.3-70b-versatile", max_retries=5):
    """Call Groq API with automatic key rotation on error and return usage."""
    retries = 0
    while retries < max_retries:
        client = get_groq_client()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )
            content = response.choices[0].message.content
            usage = response.usage  # ✅ capture token usage
            return content, usage

        except Exception as e:
            logger.error(f"⚠️ Error with key {current_api_key[:6]}...: {e}")
            retries += 1
            if retries < max_retries:
                rotate_api_key()
                time.sleep(2)
            else:
                raise RuntimeError("❌ All API keys failed.")


orthopedic_user_review_phrases_varied = [
    "Recovery progress became smoother with",
    "Daily mobility felt more natural using",
    "Comfort during extended wear improved through",
    "Pain management was noticeably better with",
    "Confidence in walking increased thanks to",
    "Joint stability was enhanced by",
    "Rehabilitation exercises became easier with",
    "Long hours of use remained comfortable due to",
    "Every step felt more supported by",
    "Balance and posture improved noticeably through",
    "Relief during routine activities was experienced with",
    "Movement restrictions were reduced significantly by",
    "Healing felt more consistent using",
    "Support during therapy sessions was strengthened by",
    "Comfort throughout the recovery journey was ensured with",
    "Daily routines were maintained more easily through",
    "Strain on joints was reduced noticeably with",
    "Mobility challenges were overcome more effectively using",
    "Independence in daily tasks was regained thanks to",
    "Flexibility during rehabilitation was supported by",
    "Stability during physical activity was reinforced with",
    "Recovery confidence improved steadily through",
    "Everyday comfort and usability were increased by",
    "Rehabilitation outcomes became more positive with",
    "Long-term recovery felt more reliable thanks to",
    "Surgeons often highlight the reliability of",
    "Recovery milestones are easier to achieve with",
    "Specialized care teams often recommend",
    "Everyday mobility is supported effectively through",
    "Long-term orthopedic care is enhanced by",
    "Stability during healing is ensured with",
    "Efficient recovery practices are made possible by",
    "Patient-centered outcomes improve noticeably with",
    "Mobility challenges are addressed effectively by",
    "Support during daily movements was noticeably improved by",
    "Overall recovery time felt shorter with the help of",
    "Strength during rehabilitation sessions was maintained through",
    "Physical therapy progress advanced more steadily with",
    "Mobility during routine activities became easier thanks to",
    "Endurance throughout the day was supported effectively by",
    "Post-surgical recovery gained consistency using",
    "Daily independence was restored more quickly with",
    "Orthopedic comfort was sustained even during long use through",
    "Confidence in performing regular tasks was reinforced with",
    "Flexibility in movement returned more naturally by using",
    "Pain reduction remained consistent during recovery with",
    "Activity levels improved gradually through the support of",
    "Balance while walking outdoors became more secure using",
    "Return to normal routines was achieved faster with",
    "Joint protection was ensured during physical activity through",
    "Everyday strength and stability improved noticeably by",
    "Comfort in resting positions was maintained with",
    "Smoother recovery transitions were supported effectively by",
    "Quality of life improved significantly with the use of",
    "Reliable support during strenuous activities was provided by",
    "Confidence during social and work activities was regained through",
    "Rehabilitation challenges were managed more easily using",
    "Durability and lasting comfort were experienced with",
    "Consistent orthopedic support was evident throughout recovery with",
    "Mobility returned to near-normal levels thanks to",
    "Adaptation to daily tasks became faster using",
    "The transition back to active living was made easier by",
    "Physical strain was minimized significantly with",
    "Confidence in long-term recovery increased through",
]

# total_tokens_used = 0

def generate_review(product_name, description):
    start_phrase = random.choice(orthopedic_user_review_phrases_varied)

    system = {
        "role": "system",
        "content": (
            "You are a professional reviewer focusing on natural, varied, human-like product reviews. "
            "Avoid repetition in starting words, formatting and style—each review must feel fresh, and must generate words between 90 and 130."
        )
    }

    user_template = {
        "role": "user",
        "content": f"""
        Write a natural, human-like product review in a single paragraph. 
        The review should be exactly 10 to 15 lines when formatted as a paragraph, contain between 100 and 150 words. Do not exceed 120 words and under 70 words.
        The opening sentence must use this starting phrase: "{start_phrase}" 
        and must not reuse the same first three words as any previous review.
        Do not start with: "This product", "When it comes to".
        Open with a fresh phrase. Mention one strength and one possible limitation using simple words.
        Avoid starting with the same phrase as the previous one; modify the opening to make it different.
        Do not use product's serial number or model number (such as HT-401124, HT-31832, HT-401122, etc).
        Maintain a warm, conversational yet professional tone and use clear, simple language.

        IMPORTANT: Do not include any special or garbled characters (such as â€™, â€œ, â€, or similar encoding artifacts).
        Only use standard English letters, numbers, punctuation (.,!?'), and common symbols.

        Product Name: {product_name}
        Description: {description}
        """
    }

    messages = [system, user_template]

    while True:
        try:
            start_row = time.time()
            review_text, usage = call_groq(messages, model="llama-3.3-70b-versatile")

            word_count = len(review_text.split())
            logger.info(f"📝 Generated review word count: {word_count}")
            logger.info(
                f"🔢 Tokens used - Prompt: {usage.prompt_tokens}, "
                f"Completion: {usage.completion_tokens}, Total: {usage.total_tokens}"
            )

            end_row = time.time()
            logger.info(f"  ⏱️ Time taken for this row: {end_row - start_row:.2f} seconds")

            global total_tokens_used
            total_tokens_used += usage.total_tokens
            logger.info(f"📊 Running total tokens used so far: {total_tokens_used}")

            sleep_time = random.uniform(2, 4) 
            logger.info(f"😴Sleeping {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

            return review_text.strip()
        except Exception as e:
            logger.info(f"⚠️ API error: {e}. Waiting 25 seconds before retrying...")
            time.sleep(25)


def generate_rating(review):
    """
    Generate a strict star rating (1–5) for a given review text.
    """
    system = {
        "role": "system",
        "content": "You are a strict medical product reviewer that assigns star ratings (1–5)."
    }
    rating_prompt = {
        "role": "user",
        "content": f"""
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
    }

    messages = [system, rating_prompt]

    while True:
        try:
            start_row = time.time()
            rating_text, usage = call_groq(messages, model="llama-3.3-70b-versatile")
            rating_text = rating_text.strip()

            rating = None
            if rating_text and rating_text[0].isdigit():
                rating = int(rating_text[0]) if int(rating_text[0]) in [1, 2, 3, 4, 5] else None

            word_count = len(review.split())
            logger.info(f"⭐ Generated rating: {rating} (Review word count: {word_count})")
            logger.info(
                f"🔢 Tokens used - Prompt: {usage.prompt_tokens}, "
                f"Completion: {usage.completion_tokens}, Total: {usage.total_tokens}"
            )

            end_row = time.time()
            logger.info(f"  ⏱️ Time taken for rating: {end_row - start_row:.2f} seconds")

            global total_tokens_used
            total_tokens_used += usage.total_tokens
            logger.info(f"📊 Running total tokens used so far: {total_tokens_used}")

            sleep_time = random.uniform(2, 4)
            logger.info(f"😴 Sleeping {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

            return rating
        except Exception as e:
            logger.error(f"⚠️ API error while generating rating: {e}. Retrying in 25 seconds...")
            time.sleep(25)

def process_container_files(output_prefix="AI-review-rating-output01/"):
    """
    Process Azure container files folder-wise.
    - Skips already processed files.
    - Saves results row by row (so resume is possible if interrupted).
    """

    logger.info("📂 Fetching files from Azure container...")
    file_count = 0
    row_count_total = 0

    # Define keywords to filter files ---
    keywords = ["Foot", "Ankle", "Plate", "Screws", "Knee", "Hip", "Screw"]

    # Group blobs by parent folder (e.g., 20250214/output/) ---
    folders = {}
    for blob in container_client.list_blobs():
        if not (blob.name.endswith(".csv") or blob.name.endswith(".xlsx")):
            continue
        if "/output/" not in blob.name:
            continue

        # ✅ Extract just the filename for keyword filtering
        filename = os.path.basename(blob.name)

        if not any(kw.lower() in filename.lower() for kw in keywords):
            continue

        folder_name = blob.name.split("/")[0]  # e.g., "20250214"
        if folder_name not in folders:
            folders[folder_name] = []
        folders[folder_name].append(blob)

    # --- Process folder by folder ---
    folder_names = sorted(folders.keys())   # ensure stable order
    start_from = 78  # <-- change this number when needed

    for folder_name in folder_names[start_from:]:
        blobs = folders[folder_name]
        output_folder = f"{output_prefix}{folder_name}_review-rating/"

        logger.info(f"\n📂 Processing folder {folder_name} "
                    f"(index {folder_names.index(folder_name)+1}/{len(folder_names)})")

        for blob in blobs:
            input_filename = os.path.basename(blob.name).replace(".csv", "")
            output_blob_name = (
                f"{output_folder}{os.path.basename(blob.name).replace('.csv', '-AI-Review&Rating.csv')}"
            )
            output_blob_client = container_client.get_blob_client(output_blob_name)

            # Download input file ---
            blob_client = container_client.get_blob_client(blob.name)
            data = blob_client.download_blob().readall()

            if blob.name.endswith(".csv"):
                df = pd.read_csv(StringIO(data.decode("utf-8")))
            else:
                df = pd.read_excel(BytesIO(data))

            # Ensure review & rating columns exist
            if "AI_review" not in df.columns:
                df["AI_review"] = ""
            if "AI_rating" not in df.columns:
                df["AI_rating"] = ""

            # Check if output file exists (resume support) ---
            try:
                existing_data = output_blob_client.download_blob().readall()
                df_out = pd.read_csv(StringIO(existing_data.decode("utf-8")))
                logger.info(f"🔄 Resuming {blob.name} ({len(df_out)} rows already processed)")
                # Merge processed results into df
                for col in ["AI_review", "AI_rating"]:
                    if col in df_out.columns:
                        df[col] = df_out[col]

                # Count how many rows are actually done
                completed_rows = df[
                    (df["AI_review"].notna()) & (df["AI_review"].astype(str).str.strip() != "") &
                    (df["AI_rating"].notna()) & (df["AI_rating"].astype(str).str.strip() != "")
                ].shape[0]

                if completed_rows == len(df):
                    logger.info(f"⏩ Skipping...✅ File already fully processed: {blob.name}")
                    continue  # skip file safely

                logger.info(f"🔄 Resuming {blob.name} ({completed_rows}/{len(df)} rows already processed)")

            except Exception:
                logger.info(f"➡️ Starting fresh for {blob.name}")

            row_count = len(df)
            row_count_total += row_count
            logger.info(f"   📑 Rows in {blob.name}: {row_count}")

            # ✅ NEW: Check if file is fully processed
            if (
                df["AI_review"].notna().all()
                and df["AI_review"].astype(str).str.strip().ne("").all()
                and df["AI_rating"].notna().all()
                and df["AI_rating"].astype(str).str.strip().ne("").all()
            ):
                logger.info(f"⏩ Skipping {blob.name} (already fully processed)")
                continue

            # Process rows one by one ---
            for idx, row in tqdm(df.iterrows(), total=row_count, desc=f"📂 Processing {os.path.basename(blob.name)}"):
                review_val = df.at[idx, "AI_review"]
                rating_val = df.at[idx, "AI_rating"]

                if pd.notna(review_val) and str(review_val).strip() != "" and \
                pd.notna(rating_val) and str(rating_val).strip() != "":
                    continue  # Skip only if both values are truly filled

                description = row.get("Device Description", "")
                if pd.isna(description) or str(description).strip() == "":
                    description = row.get("FDA Product Code Name", "")

                if pd.isna(row["AI_review"]) or row["AI_review"] == "":
                    review = generate_review(row.get("Brand Name", ""), description)
                    df.at[idx, "AI_review"] = review
                    logger.info(f"          📝 Row {idx+1}/{row_count} review generated \n ")

                if pd.isna(row["AI_rating"]) or row["AI_rating"] == "":
                    rating = generate_rating(df.at[idx, "AI_review"])
                    df.at[idx, "AI_rating"] = rating
                    logger.info(f"          ⭐ Row {idx+1}/{row_count} rating generated")

                # Save progress after each row ---
                output_csv = StringIO()
                df.to_csv(output_csv, index=False)
                output_csv.seek(0)
                output_blob_client.upload_blob(output_csv.getvalue(), overwrite=True)

                logger.info(f"✅ Progress saved at row {idx+1}/{row_count}\n")

            file_count += 1
            logger.info(f"✅ Completed {blob.name} -> {output_blob_name}")

    # Summary report ---
    logger.info("\n🎉 Processing completed!")
    logger.info(f"📊 Total files processed: {file_count}")
    logger.info(f"📑 Total rows processed: {row_count_total}")

if __name__ == "__main__":
    process_container_files()