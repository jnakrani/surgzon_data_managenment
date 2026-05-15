"""
Automatic Processing Runner

This script runs the complete automated workflow:
1. Updates the folder list with recent 7 days folders
2. Runs the AI review & rating processing

Usage:
    python run_auto_processing.py
"""

import os
import sys
import subprocess
from logger_functionality import logger

def run_command(command, description):
    """
    Run a command and handle errors.
    
    Args:
        command (str): Command to run
        description (str): Description of what the command does
        
    Returns:
        bool: True if successful, False if failed
    """
    logger.info(f"🚀 {description}...")
    logger.info(f"   Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        
        if result.stdout:
            logger.info(f"✅ Output: {result.stdout.strip()}")
        
        logger.info(f"✅ {description} completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed with exit code {e.returncode}")
        if e.stdout:
            logger.error(f"   stdout: {e.stdout.strip()}")
        if e.stderr:
            logger.error(f"   stderr: {e.stderr.strip()}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during {description}: {e}")
        return False

def main():
    """
    Main function to run the automated processing workflow.
    """
    logger.info("🚀 Starting Automatic Processing Workflow")
    logger.info("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("auto_folder_updater.py"):
        logger.error("❌ auto_folder_updater.py not found!")
        logger.error("   Make sure you're running this script from the auto_processes directory")
        return False
    
    if not os.path.exists("review_rating_threaded.py"):
        logger.error("❌ review_rating_threaded.py not found!")
        logger.error("   Make sure you're running this script from the auto_processes directory")
        return False
    
    # Step 1: Update folder list
    logger.info("\n📂 STEP 1: Updating folder list automatically...")
    if not run_command("python auto_folder_updater.py", "Folder list update"):
        logger.error("❌ Failed to update folder list. Aborting.")
        return False
    
    # Step 2: Run processing
    logger.info("\n🤖 STEP 2: Starting AI Review & Rating processing...")
    if not run_command("python review_rating_threaded.py", "AI Review & Rating processing"):
        logger.error("❌ Processing failed.")
        return False
    
    # Success
    logger.info("\n🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    logger.info("✅ Folder list updated with recent 7 days folders")
    logger.info("✅ AI Review & Rating processing completed")
    logger.info("💡 Check the logs above for detailed processing information")
    
    return True

if __name__ == "__main__":
    success = main()
    
    if not success:
        logger.error("\n❌ Workflow failed. Check the logs above for details.")
        sys.exit(1)
    else:
        logger.info("\n✅ All done! You can now check the processed files in Azure storage.")