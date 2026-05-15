import os
import time
import random
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
import google.generativeai as genai
from azure.storage.blob import BlobServiceClient
from io import StringIO, BytesIO
from logger_functionality import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from folder_fetcher import get_recent_folders
from auto_config import *

# ---------------- Azure Setup ----------------
load_dotenv()
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)

if not genai:
    raise RuntimeError("google.generativeai not installed or importable in this environment.")

# Use single API key for threading
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_CLIENT")  # Single API key
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Single model

# Thread-safe configuration lock
config_lock = Lock()

# Thread-safe progress tracking
progress_lock = Lock()
save_lock = Lock()

def configure_gemini():
    """Configure Gemini with the single API key."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY_CLIENT not found in environment variables")
    
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info(f"Configured Gemini with API key ending in {GEMINI_API_KEY[-4:]}")
    print(f"Configured Gemini with API key ending in {GEMINI_API_KEY[-4:]}")

# Initial configuration
configure_gemini()

def call_gemini(prompt_text, max_attempts: int = 3):
    """Thread-safe Gemini API call using single API key"""
    for attempt in range(max_attempts):
        try:
            # Thread-safe configuration - all threads use same API key
            with config_lock:
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel(GEMINI_MODEL)
            
            resp = model.generate_content(prompt_text, generation_config={"temperature": 0.0})
            return getattr(resp, "text", str(resp))

        except Exception as e:
            error_msg = str(e).lower()

            if "quota" in error_msg or "429" in error_msg or "exceeded" in error_msg:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}. Waiting before retry...")
                wait_time = (attempt + 1) * 10  # Exponential backoff: 10s, 20s, 30s
                time.sleep(wait_time)
            elif "api_key_invalid" in error_msg:
                logger.error(f"Invalid API key: {GEMINI_API_KEY[-4:]}")
                raise RuntimeError(f"Invalid API key ending in {GEMINI_API_KEY[-4:]}")
            else:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(5)  # Short wait for other errors

    raise RuntimeError(f"All {max_attempts} attempts failed for Gemini API call.")

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

            sleep_time = random.uniform(1.0, 2.0)  # Increased sleep for single API key
            logger.info(f"      😴Sleeping {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

            return review_text 

        except Exception as e:
            logger.info(f"⚠️ API error: {e}. Waiting 25 seconds before retrying...")
            time.sleep(25)

def generate_rating(review):
    """Generate a strict star rating (1–5) for a given review text."""
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

            word_count = len(review.split())
            logger.info(f"⭐ Generated rating: {rating} (Review word count: {word_count})")

            end_row = time.time()
            logger.info(f"  ⏱️ Time taken for rating: {end_row - start_row:.2f} seconds")

            sleep_time = random.uniform(1.0, 2.0)  # Increased sleep for single API key
            logger.info(f"      😴 Sleeping {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

            return rating

        except Exception as e:
            logger.error(f"⚠️ API error while generating rating: {e}. Retrying in 25 seconds...")
            time.sleep(25)

def process_single_row(args):
    """Process a single row - generate review and rating"""
    idx, row, thread_id = args
    
    try:
        description = row.get("Device Description", "")
        if pd.isna(description) or str(description).strip() == "":
            logger.info(f"🧵 Thread-{thread_id}: ⚠️ Skipping row {idx+1} - Device Description missing")
            return idx, None, None, "missing_description"

        # Generate review
        review = generate_review(row.get("Brand Name", ""), description)
        logger.info(f"🧵 Thread-{thread_id}: 📝 Row {idx+1} review generated")

        # Generate rating
        rating = generate_rating(review)
        logger.info(f"🧵 Thread-{thread_id}: ⭐ Row {idx+1} rating generated")

        return idx, review, rating, "success"

    except Exception as e:
        logger.error(f"🧵 Thread-{thread_id}: ❌ Error processing row {idx+1}: {e}")
        return idx, None, None, f"error: {e}"

def save_progress_batch(df, output_blob_client, processed_results, batch_size=10):
    """Save progress in batches to reduce I/O operations"""
    with save_lock:
        try:
            # Update dataframe with processed results
            for idx, review, rating, status in processed_results:
                if status == "success":
                    df.at[idx, "AI_review"] = review
                    df.at[idx, "AI_rating"] = rating

            # Save to blob storage
            output_csv = StringIO()
            df.to_csv(output_csv, index=False)
            output_csv.seek(0)
            output_blob_client.upload_blob(output_csv.getvalue(), overwrite=True)
            
            logger.info(f"✅ Batch progress saved ({len(processed_results)} rows)")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving batch progress: {e}")
            return False
def process_container_files_threaded(
    output_prefix="AI-review-rating-output01/",
    allowed_folders=None,
    process_all_files=True,
    max_workers=3,  # Reduced for single API key
    batch_save_size=10  # Save progress every N completed rows
):
    """
    Process files from Azure blob storage using threading for parallel row processing.
    """
    logger.info(f"📂 Fetching files from Azure container with {max_workers} threads...")

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

        # Check allowed folders
        if not any(blob.name.startswith(f"{folder}/") for folder in allowed_folders):
            continue

        # Apply keyword filtering only if process_all_files=False
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
        # Extract folder name (e.g. 20250402)
        folder_name = blob.name.split("/")[0]

        # Create folder structure like AI-review-rating-output01/20250402_review-rating/
        output_folder = f"{output_prefix}{folder_name}_review-rating/"

        # Build output path
        output_blob_name = (
            f"{output_folder}{os.path.basename(blob.name).replace('.csv', '-AI-Review&Rating.csv')}"
        )
        output_blob_client = container_client.get_blob_client(output_blob_name)

        logger.info(f"\n📂 Processing file: {blob.name}")
        logger.info(f"📂 Saving results to: {output_blob_name}")

        # Check if file is already fully processed BEFORE downloading
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

        # Download original file
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

        # Prepare rows that need processing
        rows_to_process = []
        for idx, row in df.iterrows():
            review_val = df.at[idx, "AI_review"]
            rating_val = df.at[idx, "AI_rating"]

            # Skip if both values are already filled
            if pd.notna(review_val) and str(review_val).strip() != "" and \
               pd.notna(rating_val) and str(rating_val).strip() != "":
                continue

            rows_to_process.append((idx, row))

        if not rows_to_process:
            logger.info(f"✅ All rows already processed for {blob.name}")
            continue

        logger.info(f"🧵 Processing {len(rows_to_process)} rows with {max_workers} threads...")

        # Process rows in parallel using ThreadPoolExecutor
        processed_results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_row = {}
            for i, (idx, row) in enumerate(rows_to_process):
                thread_id = i % max_workers + 1
                future = executor.submit(process_single_row, (idx, row, thread_id))
                future_to_row[future] = (idx, row)

            # Process completed tasks with progress bar
            with tqdm(total=len(rows_to_process), desc=f"🧵 Threading {os.path.basename(blob.name)}") as pbar:
                for future in as_completed(future_to_row):
                    result = future.result()
                    processed_results.append(result)
                    pbar.update(1)

                    # Save progress in batches
                    if len(processed_results) >= batch_save_size:
                        save_progress_batch(df, output_blob_client, processed_results, batch_save_size)
                        processed_results = []  # Clear batch

                # Save any remaining results
                if processed_results:
                    save_progress_batch(df, output_blob_client, processed_results, batch_save_size)

        file_count += 1
        logger.info(f"✅ Completed {blob.name} -> {output_blob_name}")

    # Summary
    logger.info("\n🎉 Threaded processing completed!")
    logger.info(f"📊 Total files processed: {file_count}")
    logger.info(f"📑 Total rows processed: {row_count_total}")
    logger.info(f"🧵 Used {max_workers} parallel threads")
# Copy utility functions from original file
def check_processed_files(allowed_folders=None, process_all_files=True):
    """Check which files are already processed and which need processing."""
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
    """List all files that would be processed without actually processing them."""
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
    
    return {
        'all_files': all_files,
        'processed_files': processed_files,
        'unprocessed_files': unprocessed_files
    }
def get_recent_folders_automatically(days=None, method="date_range"):
    """
    Automatically fetch recent folders from Azure blob storage.
    
    Args:
        days (int): Number of recent days to fetch folders for (default: from config)
        method (str): Method to use for fetching ("date_range", "modified", "created", "both")
        
    Returns:
        List[str]: List of recent folder names
    """
    if days is None:
        days = DAYS_TO_FETCH
        
    logger.info(f"🔄 Auto-fetching folders using method '{method}' for last {days} days...")
    
    try:
        if method == "date_range":
            recent_folders = get_recent_folders(days=days)
        elif method == "modified":
            from folder_fetcher import get_folders_by_last_modified
            hours = days * 24
            recent_folders = get_folders_by_last_modified(hours_ago=hours)
        elif method == "created":
            from folder_fetcher import get_folders_by_creation_time
            hours = days * 24
            recent_folders = get_folders_by_creation_time(hours_ago=hours)
        elif method == "both":
            from folder_fetcher import get_newly_added_folders
            hours = days * 24
            recent_folders = get_newly_added_folders(hours_ago=hours, method="both")
        else:
            logger.error(f"❌ Invalid method '{method}'. Using 'date_range' as fallback.")
            recent_folders = get_recent_folders(days=days)
        
        if recent_folders:
            logger.info(f"✅ Auto-fetched {len(recent_folders)} recent folders: {recent_folders}")
        else:
            logger.warning(f"⚠️ No folders found using method '{method}' for last {days} days")
            
        return recent_folders
        
    except Exception as e:
        logger.error(f"❌ Error auto-fetching folders: {e}")
        logger.warning("⚠️ Falling back to manual folder list...")
        return []


if __name__ == "__main__":
    logger.info("🚀 Starting AI Review & Rating Generation")
    logger.info("=" * 70)
    
    # 🔄 Determine which folders to use
    if AUTO_FETCH_FOLDERS:
        logger.info("🔄 AUTO_FETCH_FOLDERS enabled - fetching recent folders automatically...")
        logger.info(f"   📅 Days to fetch: {DAYS_TO_FETCH}")
        logger.info(f"   🔧 Method: {FOLDER_FETCH_METHOD}")
        
        allowed_folders = get_recent_folders_automatically(
            days=DAYS_TO_FETCH, 
            method=FOLDER_FETCH_METHOD
        )
        
        if not allowed_folders and USE_MANUAL_FALLBACK:
            logger.warning("⚠️ Auto-fetch returned no folders, falling back to manual list")
            allowed_folders = MANUAL_ALLOWED_FOLDERS
        elif not allowed_folders:
            logger.error("❌ No folders found and manual fallback is disabled")
            logger.error("   Either enable USE_MANUAL_FALLBACK or check your Azure connection")
            exit(1)
    else:
        logger.info("📂 Using manual folder list from config...")
        allowed_folders = MANUAL_ALLOWED_FOLDERS
    
    logger.info(f"📂 Final folder list ({len(allowed_folders)} folders): {allowed_folders}")
    
    # 🔍 Options for running the script
    check_status_only = CHECK_STATUS_ONLY
    preview_only = PREVIEW_ONLY
    
    # 🧵 Threading configuration
    MAX_WORKERS_FINAL = MAX_WORKERS
    BATCH_SAVE_SIZE_FINAL = BATCH_SAVE_SIZE 
    
    if check_status_only:
        # Just check and display processing status
        check_processed_files(
            allowed_folders=allowed_folders,
            process_all_files=PROCESS_ALL_FILES
        )
    elif preview_only:
        # Preview files before processing
        list_files_to_process(
            allowed_folders=allowed_folders,
            process_all_files=PROCESS_ALL_FILES
        )
    else:
        # Run the actual threaded processing
        logger.info("🚀 Starting AI Review & Rating Generation with THREADING")
        logger.info(f"🧵 Using {MAX_WORKERS_FINAL} parallel threads")
        logger.info(f"💾 Saving progress every {BATCH_SAVE_SIZE_FINAL} completed rows")
        logger.info("=" * 70)
        
        # First, show a quick status check
        status = check_processed_files(
            allowed_folders=allowed_folders,
            process_all_files=PROCESS_ALL_FILES
        )
        
        if status['fully_processed'] + status['partially_processed'] + status['not_started'] == 0:
            logger.info("❌ No files found to process!")
        else:
            logger.info(f"\n🎯 Will process {status['partially_processed'] + status['not_started']} files")
            logger.info(f"⏩ Will skip {status['fully_processed']} already completed files")
            
            # Proceed with threaded processing
            process_container_files_threaded(
                output_prefix=OUTPUT_PREFIX,
                allowed_folders=allowed_folders,
                process_all_files=PROCESS_ALL_FILES,
                max_workers=MAX_WORKERS_FINAL,
                batch_save_size=BATCH_SAVE_SIZE_FINAL
            )