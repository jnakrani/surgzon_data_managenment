#!/usr/bin/env python3
"""
Cronjob script to automatically fetch new folder names from Azure container
and update the review_rating_production.py file with the latest folders.

This script runs daily at 23:59 PM to:
1. Fetch all folder names from Azure container
2. Filter for date-based folders (YYYYMMDD format)
3. Update the allowed_folders list in review_rating_production.py
4. Skip folders that are already processed completely

Usage:
- Run manually: python cronjob_folder_fetcher.py
- Add to crontab: 59 23 * * * /usr/bin/python3 /path/to/cronjob_folder_fetcher.py
"""

import os
import re
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from logger_functionality import logger

# Load environment variables
load_dotenv()

# Azure Setup
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

if not AZURE_STORAGE_CONNECTION_STRING or not AZURE_BLOB_CONTAINER_NAME:
    logger.error("❌ Azure connection string or container name not found in environment variables")
    sys.exit(1)

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)


def fetch_folder_names_from_azure():
    """
    Fetch all folder names from Azure container that match date pattern (YYYYMMDD).
    Returns a list of folder names sorted by date.
    """
    logger.info("🔍 Fetching folder names from Azure container...")
    
    folder_names = set()
    date_pattern = re.compile(r'^\d{8}/')  # Matches YYYYMMDD/ pattern
    
    try:
        # List all blobs and extract folder names
        for blob in container_client.list_blobs():
            # Extract folder name (first part before '/')
            if '/' in blob.name:
                folder_name = blob.name.split('/')[0]
                
                # Check if folder name matches date pattern (YYYYMMDD)
                if date_pattern.match(folder_name + '/'):
                    folder_names.add(folder_name)
        
        # Convert to sorted list (newest first)
        sorted_folders = sorted(list(folder_names), reverse=True)
        
        logger.info(f"📂 Found {len(sorted_folders)} date-based folders in container")
        logger.info(f"📅 Latest folders: {sorted_folders[:5]}")  # Show first 5
        
        return sorted_folders
        
    except Exception as e:
        logger.error(f"❌ Error fetching folders from Azure: {e}")
        return []


def filter_recent_folders(folder_names, days_back=30):
    """
    Filter folders to include only recent ones (within specified days).
    This helps avoid processing very old folders unnecessarily.
    """
    if not folder_names:
        return []
    
    cutoff_date = datetime.now() - timedelta(days=days_back)
    recent_folders = []
    
    for folder in folder_names:
        try:
            # Parse folder name as date (YYYYMMDD)
            folder_date = datetime.strptime(folder, '%Y%m%d')
            if folder_date >= cutoff_date:
                recent_folders.append(folder)
        except ValueError:
            # Skip folders that don't match YYYYMMDD format
            logger.warning(f"⚠️ Skipping folder with invalid date format: {folder}")
            continue
    
    logger.info(f"📅 Filtered to {len(recent_folders)} folders from last {days_back} days")
    return recent_folders


def check_folder_processing_status(folder_names):
    """
    Check which folders are already fully processed to avoid unnecessary work.
    Returns list of folders that need processing.
    """
    logger.info("🔍 Checking processing status of folders...")
    
    folders_needing_work = []
    
    for folder in folder_names:
        # Check if folder has any files that need processing
        has_unprocessed_files = False
        
        try:
            # Look for CSV/XLSX files in this folder
            folder_files = []
            for blob in container_client.list_blobs(name_starts_with=f"{folder}/"):
                if blob.name.endswith(('.csv', '.xlsx')):
                    folder_files.append(blob.name)
            
            if not folder_files:
                logger.info(f"📂 {folder}: No CSV/XLSX files found")
                continue
            
            # Check if output files exist and are complete
            for file_blob in folder_files:
                output_folder = f"AI-review-rating-output01/{folder}_review-rating/"
                output_file = f"{output_folder}{os.path.basename(file_blob).replace('.csv', '-AI-Review&Rating.csv')}"
                
                try:
                    # Try to access output file
                    output_blob_client = container_client.get_blob_client(output_file)
                    output_blob_client.get_blob_properties()  # Just check if exists
                    # If we reach here, file exists - could check completeness but for now assume it's processed
                except:
                    # Output file doesn't exist, folder needs processing
                    has_unprocessed_files = True
                    break
            
            if has_unprocessed_files:
                folders_needing_work.append(folder)
                logger.info(f"🔄 {folder}: Needs processing")
            else:
                logger.info(f"✅ {folder}: Already processed")
                
        except Exception as e:
            logger.warning(f"⚠️ Error checking {folder}: {e}")
            # If we can't check, include it to be safe
            folders_needing_work.append(folder)
    
    logger.info(f"🎯 {len(folders_needing_work)} folders need processing out of {len(folder_names)}")
    return folders_needing_work


def update_azure_test_file(folder_names):
    """
    Update the review_rating_production.py file with new folder names.
    """
    script_path = "AI_review_rating/review_rating_production.py"
    
    if not os.path.exists(script_path):
        logger.error(f"❌ Target file not found: {script_path}")
        return False
    
    try:
        # Read current file
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create new allowed_folders list
        folder_list_str = "[\n        " + ",\n        ".join([f"'{folder}'" for folder in folder_names]) + "\n    ]"
        
        # Find and replace the allowed_folders assignment
        pattern = r'allowed_folders\s*=\s*\[[\s\S]*?\]'
        new_assignment = f"allowed_folders = {folder_list_str}"
        
        if re.search(pattern, content):
            updated_content = re.sub(pattern, new_assignment, content)
            
            # Write back to file
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.info(f"✅ Updated {script_path} with {len(folder_names)} folders")
            logger.info(f"📂 Updated folders: {folder_names}")
            return True
        else:
            logger.error("❌ Could not find allowed_folders assignment in file")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error updating file: {e}")
        return False


def main():
    """
    Main function to fetch folders and update the processing script.
    """
    logger.info("🚀 Starting cronjob folder fetcher...")
    logger.info("=" * 60)
    
    # Step 1: Fetch all folder names from Azure
    all_folders = fetch_folder_names_from_azure()
    
    if not all_folders:
        logger.error("❌ No folders found in Azure container")
        return
    
    # Step 2: Filter to recent folders (last 30 days)
    recent_folders = filter_recent_folders(all_folders, days_back=30)
    
    if not recent_folders:
        logger.warning("⚠️ No recent folders found")
        return
    
    # Step 3: Check which folders actually need processing
    folders_to_process = check_folder_processing_status(recent_folders)
    
    if not folders_to_process:
        logger.info("✅ All recent folders are already processed")
        return
    
    # Step 4: Update the processing script with folders that need work
    success = update_azure_test_file(folders_to_process)
    
    if success:
        logger.info("🎉 Cronjob completed successfully!")
        logger.info(f"📊 Summary: {len(folders_to_process)} folders ready for processing")
    else:
        logger.error("❌ Cronjob failed to update processing script")
        sys.exit(1)


if __name__ == "__main__":
    main()