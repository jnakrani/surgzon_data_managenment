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
    os.getenv("GEMINI_API_KEY_CLIENT"),
    # os.getenv("GEMINI_API_KEY1"),
    # os.getenv("GEMINI_API_KEY2"),
    # os.getenv("GEMINI_API_KEY3"),
    # os.getenv("GEMINI_API_KEY4"),
    # os.getenv("GEMINI_API_KEY5"),
    # os.getenv("GEMINI_API_KEY6"),

    os.getenv("GEMINI_API_KEY14"),
    os.getenv("GEMINI_API_KEY15"),
    os.getenv("GEMINI_API_KEY16"),
    os.getenv("GEMINI_API_KEY17"),
    os.getenv("GEMINI_API_KEY18"),
    os.getenv("GEMINI_API_KEY19"),
    os.getenv("GEMINI_API_KEY20"),
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


def check_processed_files(allowed_folders=None, process_all_files=True):
    """
    Check which files are already processed and which need processing.
    Returns summary statistics without processing anything.
    """
    logger.info("🔍 Checking file processing status...")
    
    if allowed_folders is None:
        allowed_folders = []

    keywords = ["Foot", "Ankle", "Plate", "Screws", "Knee", "Hip", "Screw"]
    
    total_files = 0
    fully_processed = 0
    partially_processed = 0
    not_started = 0
    
    processed_files_list = []
    partial_files_list = []
    unprocessed_files_list = []
    
    for blob in container_client.list_blobs():
        # Only process CSV and XLSX files
        if not (blob.name.endswith(".csv") or blob.name.endswith(".xlsx")):
            continue

        # Check allowed folders
        if not any(blob.name.startswith(f"{folder}/") for folder in allowed_folders):
            continue

        # Apply keyword filtering only if process_all_files=False
        if not process_all_files:
            filename = os.path.basename(blob.name)
            if not any(kw.lower() in filename.lower() for kw in keywords):
                continue

        total_files += 1
        
        # Check processing status
        folder_name = blob.name.split("/")[0]
        output_folder = f"AI-review-rating-output01/{folder_name}_review-rating/"
        output_blob_name = f"{output_folder}{os.path.basename(blob.name).replace('.csv', '-AI-Review&Rating.csv')}"
        
        try:
            output_blob_client = container_client.get_blob_client(output_blob_name)
            existing_data = output_blob_client.download_blob().readall()
            df_existing = pd.read_csv(StringIO(existing_data.decode("utf-8")))
            
            # Count completed rows
            completed_rows = df_existing[
                (df_existing["AI_review"].notna()) & (df_existing["AI_review"].astype(str).str.strip() != "") &
                (df_existing["AI_rating"].notna()) & (df_existing["AI_rating"].astype(str).str.strip() != "")
            ].shape[0]
            
            total_rows = len(df_existing)
            
            if completed_rows == total_rows:
                fully_processed += 1
                processed_files_list.append(f"{blob.name} ({completed_rows}/{total_rows} rows)")
            else:
                partially_processed += 1
                partial_files_list.append(f"{blob.name} ({completed_rows}/{total_rows} rows)")
                
        except Exception:
            not_started += 1
            unprocessed_files_list.append(blob.name)
    
    # Print summary
    logger.info(f"\n📊 FILE PROCESSING STATUS SUMMARY:")
    logger.info(f"=" * 60)
    logger.info(f"📂 Total files found: {total_files}")
    logger.info(f"✅ Fully processed: {fully_processed}")
    logger.info(f"🔄 Partially processed: {partially_processed}")
    logger.info(f"❌ Not started: {not_started}")
    logger.info(f"🎯 Files needing work: {partially_processed + not_started}")
    
    if fully_processed > 0:
        logger.info(f"\n✅ FULLY PROCESSED FILES ({fully_processed}):")
        for file in processed_files_list[:10]:  # Show first 10
            logger.info(f"   - {file}")
        if len(processed_files_list) > 10:
            logger.info(f"   ... and {len(processed_files_list) - 10} more files")
    
    if partially_processed > 0:
        logger.info(f"\n🔄 PARTIALLY PROCESSED FILES ({partially_processed}):")
        for file in partial_files_list:
            logger.info(f"   - {file}")
    
    if not_started > 0:
        logger.info(f"\n❌ NOT STARTED FILES ({not_started}):")
        for file in unprocessed_files_list[:10]:  # Show first 10
            logger.info(f"   - {file}")
        if len(unprocessed_files_list) > 10:
            logger.info(f"   ... and {len(unprocessed_files_list) - 10} more files")
    
    logger.info(f"=" * 60)
    
    return {
        'total_files': total_files,
        'fully_processed': fully_processed,
        'partially_processed': partially_processed,
        'not_started': not_started,
        'processed_files': processed_files_list,
        'partial_files': partial_files_list,
        'unprocessed_files': unprocessed_files_list
    }


def list_files_to_process(allowed_folders=None, process_all_files=True):
    """
    List all files that would be processed without actually processing them.
    Useful for preview before running the main process.
    """
    logger.info("📋 Listing files that would be processed...")
    
    if allowed_folders is None:
        allowed_folders = []

    keywords = ["Foot", "Ankle", "Plate", "Screws", "Knee", "Hip", "Screw"]
    
    all_files = []
    processed_files = []
    unprocessed_files = []
    
    for blob in container_client.list_blobs():
        # Only process CSV and XLSX files
        if not (blob.name.endswith(".csv") or blob.name.endswith(".xlsx")):
            continue

        # Check allowed folders
        if not any(blob.name.startswith(f"{folder}/") for folder in allowed_folders):
            continue

        # Apply keyword filtering only if process_all_files=False
        if not process_all_files:
            filename = os.path.basename(blob.name)
            if not any(kw.lower() in filename.lower() for kw in keywords):
                continue

        all_files.append(blob.name)
        
        # Check if already processed
        folder_name = blob.name.split("/")[0]
        output_folder = f"AI-review-rating-output01/{folder_name}_review-rating/"
        output_blob_name = f"{output_folder}{os.path.basename(blob.name).replace('.csv', '-AI-Review&Rating.csv')}"
        
        try:
            output_blob_client = container_client.get_blob_client(output_blob_name)
            existing_data = output_blob_client.download_blob().readall()
            df_out = pd.read_csv(StringIO(existing_data.decode("utf-8")))
            
            # Check if fully processed
            completed_rows = df_out[
                (df_out["AI_review"].notna()) & (df_out["AI_review"].astype(str).str.strip() != "") &
                (df_out["AI_rating"].notna()) & (df_out["AI_rating"].astype(str).str.strip() != "")
            ].shape[0]
            
            if completed_rows == len(df_out):
                processed_files.append(blob.name)
            else:
                unprocessed_files.append(f"{blob.name} ({completed_rows}/{len(df_out)} rows done)")
                
        except Exception:
            unprocessed_files.append(f"{blob.name} (not started)")
    
    logger.info(f"\n📊 File Processing Summary:")
    logger.info(f"   📂 Total files found: {len(all_files)}")
    logger.info(f"   ✅ Already processed: {len(processed_files)}")
    logger.info(f"   🔄 Need processing: {len(unprocessed_files)}")
    
    if processed_files:
        logger.info(f"\n✅ Already Processed Files:")
        for file in processed_files:
            logger.info(f"   - {file}")
    
    if unprocessed_files:
        logger.info(f"\n🔄 Files Needing Processing:")
        for file in unprocessed_files:
            logger.info(f"   - {file}")
    
    return {
        'all_files': all_files,
        'processed_files': processed_files,
        'unprocessed_files': unprocessed_files
    }


def process_container_files(
    output_prefix="AI-review-rating-output01/",
    allowed_folders=None,
    process_all_files=True
):
    """
    Process files from specific folders in Azure blob storage.
    - If process_all_files=True: Process ALL CSV/XLSX files in allowed folders
    - If process_all_files=False: Only process files with specific keywords
    - Saves into structure:
      AI-review-rating-output01/{date}_review-rating/<file>-AI-Review&Rating.csv
    """

    logger.info("📂 Fetching files from Azure container...")

    if allowed_folders is None:
        allowed_folders = []

    file_count = 0
    row_count_total = 0

    # Keywords for filtering (only used if process_all_files=False)
    keywords = ["Foot", "Ankle", "Plate", "Screws", "Knee", "Hip", "Screw"]

    blobs = []
    for blob in container_client.list_blobs():
        # Only process CSV and XLSX files
        if not (blob.name.endswith(".csv") or blob.name.endswith(".xlsx")):
            continue

        # ✅ Check allowed folders
        if not any(blob.name.startswith(f"{folder}/") for folder in allowed_folders):
            continue

        # ✅ Apply keyword filtering only if process_all_files=False
        if not process_all_files:
            filename = os.path.basename(blob.name)
            if not any(kw.lower() in filename.lower() for kw in keywords):
                continue

        blobs.append(blob)

    if process_all_files:
        logger.info(f"📂 Found {len(blobs)} files (ALL CSV/XLSX) in {allowed_folders}")
    else:
        logger.info(f"📂 Found {len(blobs)} files with keywords {keywords} in {allowed_folders}")

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

        # ✅ FIRST: Check if file is already fully processed BEFORE downloading
        try:
            existing_data = output_blob_client.download_blob().readall()
            df_existing = pd.read_csv(StringIO(existing_data.decode("utf-8")))
            
            # Check if all rows are completed
            completed_rows = df_existing[
                (df_existing["AI_review"].notna()) & (df_existing["AI_review"].astype(str).str.strip() != "") &
                (df_existing["AI_rating"].notna()) & (df_existing["AI_rating"].astype(str).str.strip() != "")
            ].shape[0]
            
            if completed_rows == len(df_existing):
                logger.info(f"⏩ Skipping...✅ File already fully processed: {blob.name} ({completed_rows}/{len(df_existing)} rows completed)")
                continue
            else:
                logger.info(f"🔄 File partially processed: {blob.name} ({completed_rows}/{len(df_existing)} rows completed)")
                
        except Exception:
            logger.info(f"➡️ Output file not found, starting fresh for {blob.name}")

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

        # Resume support - merge existing progress
        try:
            existing_data = output_blob_client.download_blob().readall()
            df_out = pd.read_csv(StringIO(existing_data.decode("utf-8")))
            
            # Merge existing AI_review and AI_rating data
            for col in ["AI_review", "AI_rating"]:
                if col in df_out.columns:
                    df[col] = df_out[col]

            completed_rows = df[
                (df["AI_review"].notna()) & (df["AI_review"].astype(str).str.strip() != "") &
                (df["AI_rating"].notna()) & (df["AI_rating"].astype(str).str.strip() != "")
            ].shape[0]

            logger.info(f"🔄 Resuming {blob.name} ({completed_rows}/{len(df)} rows already processed)")

        except Exception:
            logger.info(f"➡️ Starting fresh processing for {blob.name}")

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
    logger.info(f"📊 Total files processed: {file_count}")
    logger.info(f"📑 Total rows processed: {row_count_total}")


def run_automated_processing():
    """
    Run processing with folders automatically fetched by cronjob.
    This function is called when folders are updated by the cronjob system.
    """
    logger.info("🤖 Running automated processing with cronjob-fetched folders...")
    
    # First, show a quick status check
    status = check_processed_files(
        allowed_folders=allowed_folders,
        process_all_files=True
    )
    
    if status['fully_processed'] + status['partially_processed'] + status['not_started'] == 0:
        logger.info("❌ No files found to process!")
        return
    
    logger.info(f"\n🎯 Will process {status['partially_processed'] + status['not_started']} files")
    logger.info(f"⏩ Will skip {status['fully_processed']} already completed files")
    
    # Proceed with processing
    process_container_files(
        output_prefix="AI-review-rating-output01/",
        allowed_folders=allowed_folders,
        process_all_files=True  # 🔥 Process ALL files (not just keyword files)
    )


if __name__ == "__main__":
    # 🤖 CRONJOB-UPDATED FOLDERS - DO NOT MODIFY MANUALLY
    # This list is automatically updated by cronjob_folder_fetcher.py
    allowed_folders = [
        '20250602', '20250603', '20250604', '20250605', '20250606', '20250609', 
        '20250610', '20250611', '20250612', '20250613', '20250617', '20250618', 
        '20250620', '20250623', '20250624', '20250625', '20250626', '20250627',
    ]
    
    # 🔍 Options for running the script
    check_status_only = False  # Set to True to only check processing status
    preview_only = False       # Set to True to preview files that will be processed
    run_automated = False      # Set to True to run with cronjob-fetched folders
    
    if check_status_only:
        # Just check and display processing status
        check_processed_files(
            allowed_folders=allowed_folders,
            process_all_files=True
        )
    elif preview_only:
        # Preview files before processing
        list_files_to_process(
            allowed_folders=allowed_folders,
            process_all_files=True
        )
    elif run_automated:
        # Run automated processing (typically called after cronjob updates folders)
        run_automated_processing()
    else:
        # Run the actual processing (with improved file skipping)
        logger.info("🚀 Starting AI Review & Rating Generation with Enhanced File Skipping")
        logger.info("=" * 70)
        
        # First, show a quick status check
        status = check_processed_files(
            allowed_folders=allowed_folders,
            process_all_files=True
        )
        
        if status['fully_processed'] + status['partially_processed'] + status['not_started'] == 0:
            logger.info("❌ No files found to process!")
        else:
            logger.info(f"\n🎯 Will process {status['partially_processed'] + status['not_started']} files")
            logger.info(f"⏩ Will skip {status['fully_processed']} already completed files")
            
            # Proceed with processing
            process_container_files(
                output_prefix="AI-review-rating-output01/",
                allowed_folders=allowed_folders,
                process_all_files=True  # 🔥 Process ALL files (not just keyword files)
            ) 