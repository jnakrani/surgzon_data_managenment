#!/usr/bin/env python3
"""
Daily processing wrapper script.
This script is called by the cronjob to:
1. Fetch new folders from Azure
2. Update the processing script
3. Run the processing on new folders

This ensures complete automation of the folder fetching and processing pipeline.
"""

import os
import sys
import subprocess
from logger_functionality import logger


def run_folder_fetcher():
    """
    Run the cronjob folder fetcher to get latest folders.
    """
    logger.info("🔍 Step 1: Fetching latest folders from Azure...")
    
    try:
        # Run the folder fetcher script
        result = subprocess.run([
            sys.executable, 
            "AI_review_rating/cronjob_folder_fetcher.py"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            logger.info("✅ Folder fetcher completed successfully")
            logger.info(f"📋 Output: {result.stdout}")
            return True
        else:
            logger.error(f"❌ Folder fetcher failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error running folder fetcher: {e}")
        return False


def run_processing():
    """
    Run the main processing script with updated folders.
    """
    logger.info("🚀 Step 2: Running processing with updated folders...")
    
    try:
        # Import and run the processing with automated flag
        sys.path.append('AI_review_rating')
        
        # Modify the script to run in automated mode
        script_path = "AI_review_rating/review_rating_production.py"
        
        # Read the script
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Temporarily modify run_automated flag
        modified_content = content.replace(
            'run_automated = False', 
            'run_automated = True'
        )
        
        # Write temporary version
        temp_script = "AI_review_rating/temp_automated_run.py"
        with open(temp_script, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        # Run the temporary script
        result = subprocess.run([
            sys.executable, 
            temp_script
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Clean up temporary file
        if os.path.exists(temp_script):
            os.remove(temp_script)
        
        if result.returncode == 0:
            logger.info("✅ Processing completed successfully")
            logger.info(f"📋 Output: {result.stdout}")
            return True
        else:
            logger.error(f"❌ Processing failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error running processing: {e}")
        return False


def main():
    """
    Main function to run the complete daily processing pipeline.
    """
    logger.info("🤖 Starting Daily Automated Processing Pipeline")
    logger.info("=" * 60)
    
    # Step 1: Fetch folders
    if not run_folder_fetcher():
        logger.error("❌ Pipeline failed at folder fetching step")
        sys.exit(1)
    
    # Step 2: Run processing
    if not run_processing():
        logger.error("❌ Pipeline failed at processing step")
        sys.exit(1)
    
    logger.info("🎉 Daily processing pipeline completed successfully!")


if __name__ == "__main__":
    main()