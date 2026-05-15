"""
Azure Blob Container Folder Fetcher Utility

This utility fetches all folder names from the Azure blob container and returns them as a list.
It's designed to be used by other automation processes to get the latest available folders.
"""

import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from typing import List, Dict
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Azure Setup
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

# Initialize Azure clients
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)


def list_folders(prefix: str = "") -> List[str]:
    """
    List all 'folders' (prefixes) in the container.
    Azure Blob doesn't have true folders, but we infer them from blob names.
    
    Args:
        prefix (str): Optional prefix to filter folders
        
    Returns:
        List[str]: Sorted list of folder names
    """
    folder_set = set()

    try:
        # List blobs that start with prefix
        blob_list = container_client.list_blobs(name_starts_with=prefix)

        for blob in blob_list:
            # Split path after prefix
            relative_path = blob.name[len(prefix):].lstrip("/")
            if "/" in relative_path:   # has subfolder
                folder = relative_path.split("/")[0]
                folder_set.add(folder)

        return sorted(folder_set)
    
    except Exception as e:
        print(f"❌ Error listing folders: {e}")
        return []


def get_all_folders() -> List[str]:
    """
    Get all top-level folders in the Azure container.
    
    Returns:
        List[str]: List of all folder names (e.g., ['20250602', '20250603', ...])
    """
    print("📂 Fetching all folders from Azure container...")
    
    try:
        folders = list_folders()
        
        if not folders:
            print("❌ No folders found in the container")
            return []
        
        print(f"✅ Found {len(folders)} folders")
        return folders
        
    except Exception as e:
        print(f"❌ Error fetching folders: {e}")
        return []


def get_date_folders_only() -> List[str]:
    """
    Get only date-formatted folders (YYYYMMDD pattern).
    Filters out special folders like 'AI-review-rating-output01', etc.
    
    Returns:
        List[str]: List of date folders only (e.g., ['20250602', '20250603', ...])
    """
    print("📅 Fetching date folders from Azure container...")
    
    try:
        all_folders = list_folders()
        
        # Filter for date folders (8 digits, YYYYMMDD pattern)
        date_folders = [
            folder for folder in all_folders 
            if len(folder) == 8 and folder.isdigit()
        ]
        
        if not date_folders:
            print("❌ No date folders found in the container")
            return []
        
        print(f"✅ Found {len(date_folders)} date folders")
        return sorted(date_folders)
        
    except Exception as e:
        print(f"❌ Error fetching date folders: {e}")
        return []


def get_folders_by_date_range(start_date: str, end_date: str) -> List[str]:
    """
    Get folders within a specific date range.
    
    Args:
        start_date (str): Start date in YYYYMMDD format (e.g., '20250601')
        end_date (str): End date in YYYYMMDD format (e.g., '20250630')
        
    Returns:
        List[str]: List of folders within the date range
    """
    print(f"📅 Fetching folders between {start_date} and {end_date}...")
    
    try:
        date_folders = get_date_folders_only()
        
        # Filter folders within date range
        filtered_folders = [
            folder for folder in date_folders 
            if start_date <= folder <= end_date
        ]
        
        print(f"✅ Found {len(filtered_folders)} folders in date range")
        return filtered_folders
        
    except Exception as e:
        print(f"❌ Error fetching folders by date range: {e}")
        return []


def get_folders_by_month(year_month: str) -> List[str]:
    """
    Get all folders for a specific month.
    
    Args:
        year_month (str): Year and month in YYYYMM format (e.g., '202506')
        
    Returns:
        List[str]: List of folders for that month
    """
    print(f"📅 Fetching folders for {year_month}...")
    
    try:
        date_folders = get_date_folders_only()
        
        # Filter folders for specific month
        month_folders = [
            folder for folder in date_folders 
            if folder.startswith(year_month)
        ]
        
        print(f"✅ Found {len(month_folders)} folders for {year_month}")
        return month_folders
        
    except Exception as e:
        print(f"❌ Error fetching folders for month: {e}")
        return []


def get_folders_by_creation_time(hours_ago: int = 24) -> List[str]:
    """
    Get folders that were created within the last N hours.
    This checks the creation time of the first file in each folder.
    
    Args:
        hours_ago (int): Number of hours to look back (default: 24 hours)
        
    Returns:
        List[str]: List of newly created folders
    """
    print(f"🕒 Fetching folders created in the last {hours_ago} hours...")
    
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_ago)
        new_folders = set()
        
        # Get all blobs and check their creation time
        blob_list = container_client.list_blobs()
        
        for blob in blob_list:
            # Extract folder name (first part before '/')
            if "/" in blob.name:
                folder_name = blob.name.split("/")[0]
                
                # Check if this is a date folder (8 digits)
                if len(folder_name) == 8 and folder_name.isdigit():
                    # Check blob creation time
                    blob_client = container_client.get_blob_client(blob.name)
                    try:
                        blob_properties = blob_client.get_blob_properties()
                        creation_time = blob_properties.creation_time
                        
                        if creation_time and creation_time >= cutoff_time:
                            new_folders.add(folder_name)
                    except Exception as e:
                        # If we can't get properties, skip this blob
                        continue
        
        new_folders_list = sorted(list(new_folders))
        print(f"✅ Found {len(new_folders_list)} folders created in the last {hours_ago} hours")
        
        return new_folders_list
        
    except Exception as e:
        print(f"❌ Error fetching folders by creation time: {e}")
        return []


def get_folders_by_last_modified(hours_ago: int = 24) -> List[str]:
    """
    Get folders that had files modified within the last N hours.
    This checks the last modified time of files in each folder.
    
    Args:
        hours_ago (int): Number of hours to look back (default: 24 hours)
        
    Returns:
        List[str]: List of recently modified folders
    """
    print(f"🕒 Fetching folders modified in the last {hours_ago} hours...")
    
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_ago)
        modified_folders = set()
        
        # Get all blobs and check their last modified time
        blob_list = container_client.list_blobs()
        
        for blob in blob_list:
            # Extract folder name (first part before '/')
            if "/" in blob.name:
                folder_name = blob.name.split("/")[0]
                
                # Check if this is a date folder (8 digits)
                if len(folder_name) == 8 and folder_name.isdigit():
                    # Check blob last modified time
                    if blob.last_modified and blob.last_modified >= cutoff_time:
                        modified_folders.add(folder_name)
        
        modified_folders_list = sorted(list(modified_folders))
        print(f"✅ Found {len(modified_folders_list)} folders modified in the last {hours_ago} hours")
        
        return modified_folders_list
        
    except Exception as e:
        print(f"❌ Error fetching folders by last modified time: {e}")
        return []


def get_newly_added_folders(hours_ago: int = 24, method: str = "modified") -> List[str]:
    """
    Get newly added folders based on creation or modification time.
    
    Args:
        hours_ago (int): Number of hours to look back (default: 24 hours)
        method (str): Method to use - "created", "modified", or "both" (default: "modified")
        
    Returns:
        List[str]: List of newly added folders
    """
    print(f"🆕 Fetching newly added folders (last {hours_ago} hours, method: {method})...")
    
    try:
        if method == "created":
            return get_folders_by_creation_time(hours_ago)
        elif method == "modified":
            return get_folders_by_last_modified(hours_ago)
        elif method == "both":
            created_folders = set(get_folders_by_creation_time(hours_ago))
            modified_folders = set(get_folders_by_last_modified(hours_ago))
            combined_folders = sorted(list(created_folders.union(modified_folders)))
            print(f"✅ Found {len(combined_folders)} folders (created or modified)")
            return combined_folders
        else:
            print(f"❌ Invalid method '{method}'. Use 'created', 'modified', or 'both'")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching newly added folders: {e}")
        return []


def get_folders_added_today() -> List[str]:
    """
    Get folders that were added today (since midnight).
    
    Returns:
        List[str]: List of folders added today
    """
    print("📅 Fetching folders added today...")
    
    try:
        # Calculate hours since midnight
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hours_since_midnight = int((now - midnight).total_seconds() / 3600) + 1
        
        return get_newly_added_folders(hours_since_midnight, "modified")
        
    except Exception as e:
        print(f"❌ Error fetching folders added today: {e}")
        return []


def get_folders_added_yesterday() -> List[str]:
    """
    Get folders that were added yesterday.
    
    Returns:
        List[str]: List of folders added yesterday
    """
    print("📅 Fetching folders added yesterday...")
    
    try:
        # Get folders from 24-48 hours ago
        all_48h = set(get_newly_added_folders(48, "modified"))
        all_24h = set(get_newly_added_folders(24, "modified"))
        
        # Yesterday's folders = folders in 48h but not in 24h
        yesterday_folders = sorted(list(all_48h - all_24h))
        
        print(f"✅ Found {len(yesterday_folders)} folders added yesterday")
        return yesterday_folders
        
    except Exception as e:
        print(f"❌ Error fetching folders added yesterday: {e}")
        return []


def get_folder_details_with_timestamps() -> List[Dict]:
    """
    Get detailed information about all folders including timestamps.
    
    Returns:
        List[Dict]: List of folder details with timestamps
    """
    print("📊 Fetching detailed folder information with timestamps...")
    
    try:
        folder_details = {}
        
        # Get all blobs and collect folder information
        blob_list = container_client.list_blobs()
        
        for blob in blob_list:
            # Extract folder name (first part before '/')
            if "/" in blob.name:
                folder_name = blob.name.split("/")[0]
                
                # Check if this is a date folder (8 digits)
                if len(folder_name) == 8 and folder_name.isdigit():
                    if folder_name not in folder_details:
                        folder_details[folder_name] = {
                            'folder_name': folder_name,
                            'first_file_created': None,
                            'last_modified': None,
                            'file_count': 0
                        }
                    
                    # Update folder details
                    folder_details[folder_name]['file_count'] += 1
                    
                    # Update last modified time
                    if blob.last_modified:
                        if (folder_details[folder_name]['last_modified'] is None or 
                            blob.last_modified > folder_details[folder_name]['last_modified']):
                            folder_details[folder_name]['last_modified'] = blob.last_modified
                    
                    # Try to get creation time for first file
                    if folder_details[folder_name]['first_file_created'] is None:
                        try:
                            blob_client = container_client.get_blob_client(blob.name)
                            blob_properties = blob_client.get_blob_properties()
                            if blob_properties.creation_time:
                                folder_details[folder_name]['first_file_created'] = blob_properties.creation_time
                        except:
                            pass  # Skip if can't get creation time
        
        # Convert to list and sort by folder name
        details_list = sorted(folder_details.values(), key=lambda x: x['folder_name'])
        
        print(f"✅ Retrieved details for {len(details_list)} folders")
        return details_list
        
    except Exception as e:
        print(f"❌ Error fetching folder details: {e}")
        return []


def print_folder_details(details: List[Dict]) -> None:
    """
    Print folder details in a formatted table.
    
    Args:
        details (List[Dict]): List of folder details
    """
    if not details:
        print("❌ No folder details to display")
        return
    
    print(f"\n📊 FOLDER DETAILS ({len(details)} folders):")
    print("=" * 80)
    print(f"{'Folder':<12} {'Files':<6} {'Created':<20} {'Last Modified':<20}")
    print("-" * 80)
    
    for folder in details:
        folder_name = folder['folder_name']
        file_count = folder['file_count']
        
        created_str = "Unknown"
        if folder['first_file_created']:
            created_str = folder['first_file_created'].strftime("%Y-%m-%d %H:%M")
        
        modified_str = "Unknown"
        if folder['last_modified']:
            modified_str = folder['last_modified'].strftime("%Y-%m-%d %H:%M")
        
        print(f"{folder_name:<12} {file_count:<6} {created_str:<20} {modified_str:<20}")
    
    print("=" * 80)


def get_recent_folders(days: int = 30) -> List[str]:
    """
    Get folders from the last N days based on folder name date.
    
    Args:
        days (int): Number of recent days to include
        
    Returns:
        List[str]: List of recent folders
    """
    print(f"📅 Fetching folders from last {days} days...")
    
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        return get_folders_by_date_range(start_str, end_str)
        
    except Exception as e:
        print(f"❌ Error fetching recent folders: {e}")
        return []


def get_folders_grouped_by_month() -> Dict[str, List[str]]:
    """
    Get all folders grouped by month for better organization.
    
    Returns:
        Dict[str, List[str]]: Dictionary with month as key and list of folders as value
                             e.g., {'202506': ['20250602', '20250603', ...]}
    """
    print("📅 Fetching folders grouped by month...")
    
    try:
        date_folders = get_date_folders_only()
        
        # Group by month
        grouped_folders = {}
        for folder in date_folders:
            month = folder[:6]  # Extract YYYYMM
            if month not in grouped_folders:
                grouped_folders[month] = []
            grouped_folders[month].append(folder)
        
        # Sort folders within each month
        for month in grouped_folders:
            grouped_folders[month].sort()
        
        print(f"✅ Found folders in {len(grouped_folders)} different months")
        return grouped_folders
        
    except Exception as e:
        print(f"❌ Error grouping folders by month: {e}")
        return {}


def print_folders_as_python_list(folders: List[str], variable_name: str = "folders") -> None:
    """
    Print folders in Python list format for easy copy-paste.
    
    Args:
        folders (List[str]): List of folder names
        variable_name (str): Variable name for the Python list
    """
    if not folders:
        print("❌ No folders to display")
        return
    
    print(f"\n📋 COPY THIS PYTHON LIST ({len(folders)} folders):")
    print("=" * 60)
    
    print(f"{variable_name} = [")
    for i, folder in enumerate(folders):
        if i == len(folders) - 1:  # Last item, no comma
            print(f'    "{folder}"')
        else:
            print(f'    "{folder}",')
    print("]")
    
    print("=" * 60)


def print_folders_grouped_format(folders: List[str]) -> None:
    """
    Print folders in grouped format by month for better readability.
    
    Args:
        folders (List[str]): List of folder names
    """
    if not folders:
        print("❌ No folders to display")
        return
    
    # Group folders by month
    grouped = {}
    for folder in folders:
        if len(folder) == 8 and folder.isdigit():
            month = folder[:6]
            if month not in grouped:
                grouped[month] = []
            grouped[month].append(folder)
    
    print(f"\n📋 FOLDERS GROUPED BY MONTH ({len(folders)} total):")
    print("=" * 60)
    
    print("folders = [")
    
    for month in sorted(grouped.keys()):
        month_folders = grouped[month]
        year = month[:4]
        month_num = month[4:6]
        month_name = {
            '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
            '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
            '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
        }.get(month_num, f'M{month_num}')
        
        print(f'    # {month_name} {year}')
        
        # Print folders in groups of 6 per line for readability
        for i in range(0, len(month_folders), 6):
            line_folders = month_folders[i:i+6]
            line = "    " + ", ".join(f'"{folder}"' for folder in line_folders)
            if i + 6 < len(month_folders) or month != sorted(grouped.keys())[-1]:
                line += ","
            print(line)
        print()  # Empty line between months
    
    print("]")
    print("=" * 60)


# Main functions for easy import
def get_folders_list() -> List[str]:
    """
    Main function to get all folders as a simple list.
    This is the primary function other scripts should use.
    
    Returns:
        List[str]: List of all folder names
    """
    return get_all_folders()


def get_date_folders_list() -> List[str]:
    """
    Main function to get only date folders as a simple list.
    
    Returns:
        List[str]: List of date folder names only
    """
    return get_date_folders_only()


def get_new_folders_list(hours_ago: int = 24) -> List[str]:
    """
    Main function to get newly added folders as a simple list.
    
    Args:
        hours_ago (int): Number of hours to look back (default: 24 hours)
        
    Returns:
        List[str]: List of newly added folder names
    """
    return get_newly_added_folders(hours_ago, "modified")


def get_todays_folders_list() -> List[str]:
    """
    Main function to get folders added today as a simple list.
    
    Returns:
        List[str]: List of folders added today
    """
    return get_folders_added_today()


def get_yesterdays_folders_list() -> List[str]:
    """
    Main function to get folders added yesterday as a simple list.
    
    Returns:
        List[str]: List of folders added yesterday
    """
    return get_folders_added_yesterday()


# CLI interface
if __name__ == "__main__":
    import sys
    
    print("🚀 Azure Blob Container Folder Fetcher")
    print("=" * 50)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "--all":
            folders = get_all_folders()
            print_folders_as_python_list(folders, "all_folders")
            
        elif command == "--date-only":
            folders = get_date_folders_only()
            print_folders_as_python_list(folders, "date_folders")
            
        elif command == "--grouped":
            folders = get_date_folders_only()
            print_folders_grouped_format(folders)
            
        elif command == "--recent":
            try:
                days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
                folders = get_recent_folders(days)
                print_folders_as_python_list(folders, f"recent_{days}_days")
            except ValueError:
                print("❌ Please provide a valid number for days (e.g., --recent 30)")
                print("   Usage: python folder_fetcher.py --recent 30")
            
        elif command == "--month":
            if len(sys.argv) > 2:
                year_month = sys.argv[2]
                folders = get_folders_by_month(year_month)
                print_folders_as_python_list(folders, f"folders_{year_month}")
            else:
                print("❌ Please provide year-month in YYYYMM format")
                
        elif command == "--range":
            if len(sys.argv) > 3:
                start_date = sys.argv[2]
                end_date = sys.argv[3]
                folders = get_folders_by_date_range(start_date, end_date)
                print_folders_as_python_list(folders, f"folders_{start_date}_to_{end_date}")
            else:
                print("❌ Please provide start and end dates in YYYYMMDD format")
                
        elif command == "--new":
            try:
                hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
                folders = get_newly_added_folders(hours, "modified")
                print_folders_as_python_list(folders, f"new_folders_last_{hours}h")
            except ValueError:
                print("❌ Please provide a valid number for hours (e.g., --new 24)")
                print("   Usage: python folder_fetcher.py --new 24")
            
        elif command == "--created":
            try:
                hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
                folders = get_folders_by_creation_time(hours)
                print_folders_as_python_list(folders, f"created_folders_last_{hours}h")
            except ValueError:
                print("❌ Please provide a valid number for hours (e.g., --created 24)")
                print("   Usage: python folder_fetcher.py --created 24")
            
        elif command == "--modified":
            try:
                hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
                folders = get_folders_by_last_modified(hours)
                print_folders_as_python_list(folders, f"modified_folders_last_{hours}h")
            except ValueError:
                print("❌ Please provide a valid number for hours (e.g., --modified 24)")
                print("   Usage: python folder_fetcher.py --modified 24")
            
        elif command == "--today":
            folders = get_folders_added_today()
            print_folders_as_python_list(folders, "todays_folders")
            
        elif command == "--yesterday":
            folders = get_folders_added_yesterday()
            print_folders_as_python_list(folders, "yesterdays_folders")
            
        elif command == "--details":
            details = get_folder_details_with_timestamps()
            print_folder_details(details)
                
        else:
            print("❌ Unknown command. Available commands:")
            print("   --all              : Get all folders")
            print("   --date-only        : Get date folders only")
            print("   --grouped          : Get folders grouped by month")
            print("   --recent 30        : Get recent folders (specify number of days)")
            print("   --month 202506     : Get folders for specific month")
            print("   --range 20250601 20250630 : Get folders in date range")
            print("   --new 24           : Get newly added folders (specify hours)")
            print("   --created 24       : Get folders by creation time (specify hours)")
            print("   --modified 24      : Get folders by modification time (specify hours)")
            print("   --today            : Get folders added today")
            print("   --yesterday        : Get folders added yesterday")
            print("   --details          : Get detailed folder information with timestamps")
    
    else:
        # Default behavior - show date folders in grouped format
        folders = get_date_folders_only()
        print(f"📂 Found {len(folders)} date folders")
        print_folders_grouped_format(folders)
        
        print("\n💡 Usage examples:")
        print("   python folder_fetcher.py --all")
        print("   python folder_fetcher.py --date-only")
        print("   python folder_fetcher.py --recent 7")
        print("   python folder_fetcher.py --month 202506")
        print("   python folder_fetcher.py --range 20250601 20250630")
        print("   python folder_fetcher.py --new 24")
        print("   python folder_fetcher.py --today")
        print("   python folder_fetcher.py --yesterday")
        print("   python folder_fetcher.py --details")