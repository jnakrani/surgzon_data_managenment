"""
Configuration file for automatic folder processing

Adjust these settings to control the automatic folder fetching and processing behavior.
"""

# ============================================================================
# AUTOMATIC FOLDER FETCHING SETTINGS
# ============================================================================

# Enable/disable automatic folder fetching
AUTO_FETCH_FOLDERS = True

# Number of recent days to fetch folders for
DAYS_TO_FETCH = 7

# Fallback to manual list if auto-fetch fails
USE_MANUAL_FALLBACK = True

# Manual folder list (used as fallback or when AUTO_FETCH_FOLDERS = False)
MANUAL_ALLOWED_FOLDERS = [
    '20260101', '20260102', '20260105', '20260106', '20260108', '20260109', 
    '20260112', '20260113', '20260114', '20260115', '20260116', '20260120',
]

# ============================================================================
# PROCESSING SETTINGS
# ============================================================================

# Threading configuration
MAX_WORKERS = 5           # Number of parallel threads
BATCH_SAVE_SIZE = 10      # Save progress every N completed rows

# Processing options
CHECK_STATUS_ONLY = False  # Set to True to only check processing status
PREVIEW_ONLY = False       # Set to True to preview files that will be processed
PROCESS_ALL_FILES = True   # Process all CSV/XLSX files (not just keyword-filtered)

# Output settings
OUTPUT_PREFIX = "AI-review-rating-output01/"

# ============================================================================
# FOLDER FETCHING METHOD SETTINGS
# ============================================================================

# Method for determining "recent" folders
# Options: "date_range", "modified", "created", "both"
FOLDER_FETCH_METHOD = "date_range"  # Recommended: uses folder name dates

# For time-based methods (modified/created), specify hours instead of days
HOURS_TO_FETCH = 168  # 7 days = 168 hours (only used if method is not "date_range")

# ============================================================================
# LOGGING SETTINGS
# ============================================================================

# Enable detailed logging
VERBOSE_LOGGING = True

# Log file settings (handled by logger_functionality.py)
LOG_TO_FILE = True