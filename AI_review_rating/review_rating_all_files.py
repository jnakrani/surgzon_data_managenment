"""
AI Review & Rating Generator - Version 03
Modified to process files WITHOUT specific keywords (avoiding duplicates)

Key Changes from v02:
- ✅ Processes files that do NOT contain orthopedic keywords (inverse filtering)
- ✅ Avoids duplicate processing of files already processed with keyword filtering
- ✅ Option to process ALL output folders automatically (excluding keyword files)
- ✅ Same API key cycling mechanism as v02
- ✅ Same model cycling (gemini-2.5-flash-lite, gemini-2.5-flash, gemini-2.5-pro)

Excluded Keywords: ["Foot", "Ankle", "Plate", "Screws", "Knee", "Hip", "Screw"]

Usage:
1. Specific folders: Set allowed_folders list and run process_container_files()
2. All output folders: Uncomment process_all_output_folders() in main section

This ensures no duplicate processing between v02 (keyword files) and v03 (non-keyword files).
"""

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
# ---------------- Azure Setup ----------------
load_dotenv()
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)

API_KEYS = [
    # Use the same API keys as review_rating_keyword_filter.py for consistency
    os.getenv("GEMINI_API_KEY_CLIENT"),
    os.getenv("GEMINI_API_KEY1"),
    os.getenv("GEMINI_API_KEY2"),
    os.getenv("GEMINI_API_KEY3"),
    os.getenv("GEMINI_API_KEY4"),
    os.getenv("GEMINI_API_KEY5"),
    os.getenv("GEMINI_API_KEY6"),
    os.getenv("GEMINI_API_KEY7"),
    os.getenv("GEMINI_API_KEY8"),
    os.getenv("GEMINI_API_KEY9"),
    os.getenv("GEMINI_API_KEY10"),
    os.getenv("GEMINI_API_KEY11"),
    os.getenv("GEMINI_API_KEY12"),
    os.getenv("GEMINI_API_KEY13"),
]
api_key_cycle = cycle(API_KEYS)
current_api_key = next(api_key_cycle)

gemini_models = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
model_cycle = cycle(gemini_models)
current_model = next(model_cycle)

def configure_gemini(api_key: str):
    """Configure Gemini with the given API key."""
    genai.configure(api_key=api_key)
    logger.info(f"Configured Gemini with API key ending in {api_key[-4:]}")
    print(f"Configured Gemini with API key ending in {api_key[-4:]}")

def validate_api_keys():
    """Validate API keys by testing a simple call"""
    valid_keys = []
    for i, key in enumerate(API_KEYS):
        if not key:
            continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.5-flash-lite")
            resp = model.generate_content("Test", generation_config={"temperature": 0.0})
            valid_keys.append(key)
            logger.info(f"✅ API Key {i+1} ending in {key[-4:]} is valid")
        except Exception as e:
            logger.warning(f"❌ API Key {i+1} ending in {key[-4:]} is invalid: {str(e)[:100]}")
    
    logger.info(f"Found {len(valid_keys)} valid API keys out of {len(API_KEYS)}")
    return valid_keys

# Validate keys on startup (optional - comment out if you want to skip validation)
# valid_keys = validate_api_keys()

# Initial configuration
configure_gemini(current_api_key)

def call_gemini(prompt_text, max_attempts: int = 3):
    global current_api_key, current_model

    for attempt in range(max_attempts):
        try:
            model = genai.GenerativeModel(current_model)
            resp = model.generate_content(prompt_text, generation_config={"temperature": 0.0})
            return getattr(resp, "text", str(resp))

        except Exception as e:
            error_msg = str(e).lower()

            if "quota" in error_msg or "429" in error_msg or "exceeded" in error_msg or "api_key_invalid" in error_msg:
                print(f"Issue with key ending in {current_api_key[-4:]} (Model: {current_model}). Switching to next key and model...")
                current_api_key = next(api_key_cycle)
                current_model = next(model_cycle)
                configure_gemini(current_api_key)
                print(f"Switched to key ending in {current_api_key[-4:]} with model {current_model}")
                time.sleep(2)

            else:
                print(f"Unexpected error: {e}")
                if attempt == max_attempts - 1:
                    raise e

    raise RuntimeError("All Gemini API keys/models exhausted after retries.")

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

def generate_review(product_name, description):
    start_phrase = random.choice(orthopedic_user_review_phrases_varied)

    system = {
        "role": "system",
        "content": (
            "You are a professional reviewer focusing on natural, varied, human-like product reviews. "
            "Avoid repetition in starting words, formatting and style—each review must feel fresh."
        )
    }

    user_template = """
    Write a natural, human-like product review in a single paragraph. The review should be exactly 7 to 8 lines when formatted as a paragraph, contain between 70 and 120 words. Do not exceed 120 words.
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

    while True:
        try:
            start_row = time.time()
            prompt = f"{system}\n\n" + user_template.format(
                start_phrase=start_phrase,
                product_name=product_name,
                description=description
            )

            review_text = call_gemini(prompt).strip()

            word_count = len(review_text.split())
            logger.info(f"📝 Generated review word count: {word_count}")

            end_row = time.time()
            logger.info(f"  ⏱️ Time taken for this row: {end_row - start_row:.2f} seconds")

            sleep_time = random.uniform(1, 2) 
            logger.info(f"      😴Sleeping {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

            return review_text 

        except Exception as e:
            logger.info(f"⚠️ API error: {e}. Waiting 25 seconds before retrying...")
            time.sleep(25)


def generate_rating(review):
    """
    Generate a strict star rating (1–5) for a given review text.
    """
    rating_prompt = f"""
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
            rating_text = call_gemini(rating_prompt).strip()

            # Extract number only (ensure it's valid 1–5)
            rating = None
            if rating_text and rating_text[0].isdigit():
                rating = int(rating_text[0])
                if rating not in [1, 2, 3, 4, 5]:
                    rating = None

            # Word count of the review (for reference/logging)
            word_count = len(review.split())
            logger.info(f"⭐ Generated rating: {rating} (Review word count: {word_count})")

            end_row = time.time()
            logger.info(f"  ⏱️ Time taken for rating: {end_row - start_row:.2f} seconds")

            sleep_time = random.uniform(1, 2)
            logger.info(f"      😴 Sleeping {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

            return rating

        except Exception as e:
            logger.error(f"⚠️ API error while generating rating: {e}. Retrying in 25 seconds...")
            time.sleep(25)


def process_container_files(
    output_prefix="AI-review-rating-output01/",
    allowed_folders=None
):
    """
    Process files from specific folders in Azure blob storage that do NOT contain specific keywords.
    This avoids duplicate processing of files that were already processed with keyword filtering.
    - Saves into structure:
      AI-review-rating-output01/{date}_review-rating/<file>-AI-Review&Rating.csv
    """

    logger.info("📂 Fetching files WITHOUT keywords from Azure container...")

    if allowed_folders is None:
        allowed_folders = []

    file_count = 0
    row_count_total = 0

    # ✅ EXCLUDE files with these keywords (since they were already processed)
    exclude_keywords = ["Foot", "Ankle", "Plate", "Screws", "Knee", "Hip", "Screw"]

    blobs = []
    for blob in container_client.list_blobs():
        if not (blob.name.endswith(".csv") or blob.name.endswith(".xlsx")):
            continue

        # ✅ Check allowed folders
        if not any(blob.name.startswith(f"{folder}/") for folder in allowed_folders):
            continue

        # ✅ EXCLUDE files that contain keywords (inverse of previous logic)
        filename = os.path.basename(blob.name)
        if any(kw.lower() in filename.lower() for kw in exclude_keywords):
            continue  # Skip files with keywords

        blobs.append(blob)

    logger.info(f"📂 Found {len(blobs)} files WITHOUT keywords {exclude_keywords} in {allowed_folders}")

    for blob in blobs:
        # --- extract folder name (e.g. 20250402) ---
        folder_name = blob.name.split("/")[0]

        # --- create folder structure like AI-review-rating-output01/20250402_review-rating/ ---
        output_folder = f"{output_prefix}{folder_name}_review-rating/"

        # --- build output path ---
        output_blob_name = (
            f"{output_folder}{os.path.basename(blob.name).replace('.csv', '-AI-Review&Rating.csv')}"
        )
        output_blob_client = container_client.get_blob_client(output_blob_name)

        logger.info(f"\n📂 Processing file: {blob.name}")
        logger.info(f"📂 Saving results to: {output_blob_name}")

        # --- download original file ---
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

        # Resume support
        try:
            existing_data = output_blob_client.download_blob().readall()
            df_out = pd.read_csv(StringIO(existing_data.decode("utf-8")))
            logger.info(f"🔄 Resuming {blob.name} ({len(df_out)} rows already processed)")

            for col in ["AI_review", "AI_rating"]:
                if col in df_out.columns:
                    df[col] = df_out[col]

            completed_rows = df[
                (df["AI_review"].notna()) & (df["AI_review"].astype(str).str.strip() != "") &
                (df["AI_rating"].notna()) & (df["AI_rating"].astype(str).str.strip() != "")
            ].shape[0]

            if completed_rows == len(df):
                logger.info(f"⏩ Skipping...✅ File already fully processed: {blob.name}")
                continue

            logger.info(f"🔄 Resuming {blob.name} ({completed_rows}/{len(df)} rows already processed)")

        except Exception:
            logger.info(f"➡️ Starting fresh for {blob.name}")

        row_count = len(df)
        row_count_total += row_count
        logger.info(f"   📑 Rows in {blob.name}: {row_count}")

        # Process rows one by one ---
        for idx, row in tqdm(df.iterrows(), total=row_count, desc=f"📂 Processing {os.path.basename(blob.name)}"):
            review_val = df.at[idx, "AI_review"]
            rating_val = df.at[idx, "AI_rating"]

            if pd.notna(review_val) and str(review_val).strip() != "" and \
            pd.notna(rating_val) and str(rating_val).strip() != "":
                continue  # Skip only if both values are already filled

            description = row.get("Device Description", "")
            if pd.isna(description) or str(description).strip() == "":
                logger.info(f"⚠️ Skipping row {idx+1}/{row_count} - Device Description missing")
                continue  

            # ✅ Only generate if Device Description exists
            if pd.isna(row["AI_review"]) or row["AI_review"] == "":
                review = generate_review(row.get("Brand Name", ""), description)
                df.at[idx, "AI_review"] = review
                logger.info(f"          📝 Row {idx+1}/{row_count} review generated")

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

    # Summary
    logger.info("\n🎉 Processing completed!")
    logger.info(f"📑 Total files processed: {file_count}")
    logger.info(f"📑 Total rows processed: {row_count_total}")


def process_all_output_folders(output_prefix="AI-review-rating-output01/"):
    """
    Process files from ALL output folders in the container that do NOT contain keywords.
    This will scan the entire container and process any folder that contains output files,
    but exclude files that were already processed with keyword filtering.
    """
    logger.info("🔍 Scanning container for ALL output folders (excluding keyword files)...")
    
    # Find all folders that contain output files
    output_folders = set()
    exclude_keywords = ["Foot", "Ankle", "Plate", "Screws", "Knee", "Hip", "Screw"]
    
    for blob in container_client.list_blobs():
        if not (blob.name.endswith(".csv") or blob.name.endswith(".xlsx")):
            continue
            
        # Check if this is in an output folder pattern
        if ("/output/" in blob.name or 
            blob.name.startswith("latest_full_release/") or
            blob.name.startswith("AI-review-rating-output01/") or
            blob.name.startswith("AI-data-extract-output/") or
            blob.name.startswith("latest_full_release_review-rating/")):
            
            # Check if file should be excluded (has keywords)
            filename = os.path.basename(blob.name)
            if any(kw.lower() in filename.lower() for kw in exclude_keywords):
                continue  # Skip files with keywords
            
            folder_name = blob.name.split("/")[0]
            output_folders.add(folder_name)
    
    output_folders = sorted(list(output_folders))
    logger.info(f"📂 Found {len(output_folders)} output folders with non-keyword files to process:")
    for i, folder in enumerate(output_folders[:10]):  # Show first 10
        logger.info(f"   {i+1}. {folder}")
    if len(output_folders) > 10:
        logger.info(f"   ... and {len(output_folders) - 10} more folders")
    
    # Process all found output folders
    process_container_files(output_prefix=output_prefix, allowed_folders=output_folders)


if __name__ == "__main__":
    # Option 1: Process specific folders (current behavior)
    specific_folders = [
        # '20250211', '20250212', '20250213', '20250214', '20250217', '20250218', 
        # '20250219', '20250220', '20250221', '20250224', '20250225', '20250226', 
        # '20250227', '20250228', 

        # '20250303', '20250304', '20250305', '20250306', '20250307', '20250310', 
        # '20250311', '20250312', '20250313', '20250314', '20250317', '20250318', 
        # '20250319', '20250320', '20250321', '20250324', '20250325', '20250326', 
        # '20250327', '20250328', '20250331', 

        # '20250401', '20250402', '20250403', '20250404', '20250407', '20250408', 
        # '20250409', '20250410', '20250411', '20250414', '20250415', '20250416', 
        # '20250417', '20250418', '20250421', '20250422', '20250423', '20250424', 
        # '20250425', '20250428', '20250429', '20250430', 

        # "20250502", "20250505", "20250506", "20250507", "20250508",
        # "20250509", "20250512", "20250513", "20250514", "20250515",
        # "20250516", "20250519", "20250520", "20250521", "20250522",
        # "20250523", "20250526", "20250527", "20250528", "20250529", "20250530",

        # '20250602', '20250603', '20250604', '20250605', '20250606', '20250609', 
        # '20250610', '20250611', '20250612', '20250613', '20250617', '20250618', 
        # '20250620', '20250623', '20250624', '20250625', '20250626', '20250627',

        # '20250701', '20250703', '20250704', '20250707', '20250708', '20250709',
        '20250710', '20250711', '20250714', '20250715', '20250716', '20250717', 
        '20250718', '20250721', '20250722', '20250723', '20250724', '20250725', 
        '20250728', '20250729', '20250730', '20250731',

        '20250804', '20250805', '20250806', '20250807', '20250808', '20250811', '20250812', 
        '20250813', '20250814', '20250815', '20250818', '20250819', '20250820', '20250821', 
        '20250822', '20250825', '20250826', '20250827', '20250828', '20250829', 

        '20250902', '20250903', '20250904', '20250905', '20250908', '20250909', 
        '20250910', '20250911', '20250912', '20250915', '20250916', '20250917', 
        '20250919', '20250922', '20250923', '20250925', '20250926', '20250929', '20250930',

        '20251002', '20251003', '20251006', '20251007', 

        '20251119', '20251121', '20251124', '20251125', '20251128', 

        '20251201', '20251202', '20251203', '20251205', '20251208', 
        '20251209', '20251210', '20251211', '20251212', '20251215', 
        '20251216', '20251217', '20251218', '20251219', '20251222', 
        '20251223', '20251224', '20251225', '20251226', '20251229', 
        '20251230', '20251231',

        '20260101', '20260102', '20260105', '20260106', '20260108', 
        '20260109', '20260112', '20260113', '20260114', '20260115', 
        # '20260116', '20260119', '20260120', '20260121', '20260122', '20260123',

    ]
    
    # Option 2: Process ALL output folders (uncomment to use)
    # process_all_output_folders(output_prefix="AI-review-rating-output01/")
    
    # Current: Process only specific folders
    process_container_files(
        output_prefix="AI-review-rating-output01/",
        allowed_folders=specific_folders
    )
