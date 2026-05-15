"""
Automatic Folder Updater for review_rating_threaded.py

This script automatically fetches the recent 7 days folder names from Azure
and updates the allowed_folders list in review_rating_threaded.py file.

Usage:
    python auto_folder_updater.py
"""

import os
import re
from datetime import datetime
from folder_fetcher import get_recent_folders
from logger_functionality import logger

def get_recent_7_days_folders():
    """
    Get folder names from the recent 7 days.
    
    Returns:
        List[str]: List of recent 7 days folder names
    """
    logger.info("📅 Fetching recent 7 days folders...")
    
    try:
        # Get folders from last 7 days
        recent_folders = get_recent_folders(days=7)
        
        if not recent_folders:
            logger.warning("⚠️ No recent folders found in the last 7 days")
            return []
        
        logger.info(f"✅ Found {len(recent_folders)} folders from last 7 days: {recent_folders}")
        return recent_folders
        
    except Exception as e:
        logger.error(f"❌ Error fetching recent folders: {e}")
        return []


def update_allowed_folders_in_file(file_path, new_folders):
    """
    Update the allowed_folders list in the review_rating_threaded.py file.
    
    Args:
        file_path (str): Path to the review_rating_threaded.py file
        new_folders (List[str]): List of new folder names to set
    """
    logger.info(f"📝 Updating allowed_folders in {file_path}...")
    
    try:
        # Read the current file
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Create the new allowed_folders list string
        if new_folders:
            folders_str = ",\n        ".join([f"'{folder}'" for folder in new_folders])
            new_allowed_folders = f"""    allowed_folders = [
        {folders_str}
    ]"""
        else:
            new_allowed_folders = "    allowed_folders = []"
        
        # Pattern to match the existing allowed_folders assignment
        # This pattern matches from "allowed_folders = [" to the closing "]"
        pattern = r'(\s*allowed_folders\s*=\s*\[)(.*?)(\]\s*)'
        
        # Find the pattern in the content
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # Replace the existing allowed_folders assignment
            before = content[:match.start()]
            after = content[match.end():]
            
            updated_content = before + new_allowed_folders + " \n" + after
            
            # Write the updated content back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            
            logger.info(f"✅ Successfully updated allowed_folders with {len(new_folders)} folders")
            logger.info(f"📂 Updated folders: {new_folders}")
            
        else:
            logger.error("❌ Could not find allowed_folders assignment in the file")
            logger.error("   Make sure the file contains 'allowed_folders = [...]' pattern")
            
    except Exception as e:
        logger.error(f"❌ Error updating file: {e}")


def backup_original_file(file_path):
    """
    Create a backup of the original file before modification.
    
    Args:
        file_path (str): Path to the file to backup
    """
    try:
        backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with open(file_path, 'r', encoding='utf-8') as original:
            content = original.read()
        
        with open(backup_path, 'w', encoding='utf-8') as backup:
            backup.write(content)
        
        logger.info(f"💾 Backup created: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"❌ Error creating backup: {e}")
        return None


def main():
    """
    Main function to automatically update the allowed_folders list.
    """
    logger.info("🚀 Starting Automatic Folder Updater")
    logger.info("=" * 50)
    
    # Path to the review_rating_threaded.py file
    target_file = "review_rating_threaded.py"
    
    # Check if file exists
    if not os.path.exists(target_file):
        logger.error(f"❌ Target file not found: {target_file}")
        logger.error("   Make sure you're running this script from the auto_processes directory")
        return
    
    # Create backup
    backup_path = backup_original_file(target_file)
    if not backup_path:
        logger.error("❌ Failed to create backup. Aborting update.")
        return
    
    # Get recent 7 days folders
    recent_folders = get_recent_7_days_folders()
    
    if not recent_folders:
        logger.warning("⚠️ No recent folders found. The allowed_folders list will be empty.")
        logger.warning("   This means no files will be processed until folders are added.")
    
    # Update the file
    update_allowed_folders_in_file(target_file, recent_folders)
    
    logger.info("\n🎉 Automatic folder update completed!")
    logger.info(f"📂 Updated {len(recent_folders)} folders in {target_file}")
    logger.info(f"💾 Backup saved as: {backup_path}")
    logger.info("\n💡 You can now run review_rating_threaded.py to process the recent folders")


if __name__ == "__main__":
    main()