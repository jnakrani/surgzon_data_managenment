import os
import sys
from collections import defaultdict
from azure.storage.blob import BlobServiceClient, ContainerClient
from dotenv import load_dotenv


# ---------------- Azure Setup ----------------
load_dotenv()
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)


def create_folder_and_upload_file(folder_name: str, file_path: str, blob_name: str = None):
    """
    Upload a file into a 'folder' inside the container.
    Azure Blob doesn't have real folders, we simulate using prefix: folder/file.txt
    """
    if not blob_name:
        blob_name = os.path.basename(file_path)

    # Full path in blob = folder_name/file_name
    blob_path = f"{folder_name}/{blob_name}"

    blob_client = container_client.get_blob_client(blob_path)
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    print(f"Uploaded {file_path} to {blob_path}")


def list_files_in_folder(folder_name: str):
    """
    List all blobs with a given prefix (simulating a folder).
    """
    print(f"\n📂 Files in folder '{folder_name}':")
    blob_list = container_client.list_blobs(name_starts_with=folder_name + "/")
    for blob in blob_list:
        print(f"- {blob.name}")


def list_all_folders():
    """
    Display all top-level folders in the container in a clean format.
    """
    print("🚀 LISTING ALL FOLDERS IN CONTAINER")
    print("=" * 60)
    
    try:
        folders = list_folders(container_client)
        
        if not folders:
            print("❌ No folders found in the container")
            return []
        
        print(f"📂 Found {len(folders)} folders:")
        print("-" * 60)
        
        for i, folder in enumerate(folders, 1):
            print(f"   {i:3d}. {folder}")
        
        print("-" * 60)
        print(f"📊 Total: {len(folders)} folders")
        
        return folders
        
    except Exception as e:
        print(f"❌ Error listing folders: {e}")
        return []


def get_folders_as_python_list():
    """
    Get all folders formatted as a Python list that can be copied and pasted.
    """
    print("🚀 GETTING FOLDERS AS PYTHON LIST")
    print("=" * 60)
    
    try:
        folders = list_folders(container_client)
        
        if not folders:
            print("❌ No folders found in the container")
            return []
        
        print(f"📂 Found {len(folders)} folders")
        print("\n📋 COPY THIS PYTHON LIST:")
        print("=" * 60)
        
        # Format as Python list
        print("folders = [")
        for i, folder in enumerate(folders):
            if i == len(folders) - 1:  # Last item, no comma
                print(f'    "{folder}"')
            else:
                print(f'    "{folder}",')
        print("]")
        
        print("=" * 60)
        print(f"📊 Total: {len(folders)} folders")
        
        return folders
        
    except Exception as e:
        print(f"❌ Error listing folders: {e}")
        return []


def get_folders_as_python_dict():
    """
    Get all folders formatted as a Python dictionary that can be copied and pasted.
    Groups folders by year-month for better organization.
    """
    print("🚀 GETTING FOLDERS AS PYTHON DICTIONARY")
    print("=" * 60)
    
    try:
        folders = list_folders(container_client)
        
        if not folders:
            print("❌ No folders found in the container")
            return {}
        
        print(f"📂 Found {len(folders)} folders")
        
        # Group folders by year-month pattern (YYYYMM)
        folder_dict = {}
        special_folders = []
        
        for folder in folders:
            # Check if folder follows YYYYMMDD pattern
            if len(folder) == 8 and folder.isdigit():
                year_month = folder[:6]  # Extract YYYYMM
                if year_month not in folder_dict:
                    folder_dict[year_month] = []
                folder_dict[year_month].append(folder)
            else:
                # Special folders (non-date folders)
                special_folders.append(folder)
        
        print("\n📋 COPY THIS PYTHON DICTIONARY:")
        print("=" * 60)
        
        print("folders_dict = {")
        
        # Print date-based folders grouped by month
        for year_month in sorted(folder_dict.keys()):
            month_folders = sorted(folder_dict[year_month])
            year = year_month[:4]
            month = year_month[4:6]
            month_name = {
                '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                '09': 'September', '10': 'October', '11': 'November', '12': 'December'
            }.get(month, f'Month{month}')
            
            print(f'    "{year_month}": [  # {month_name} {year}')
            for i, folder in enumerate(month_folders):
                if i == len(month_folders) - 1:  # Last item in this month
                    print(f'        "{folder}"')
                else:
                    print(f'        "{folder}",')
            print('    ],')
        
        # Print special folders if any
        if special_folders:
            print('    "special": [  # Non-date folders')
            for i, folder in enumerate(sorted(special_folders)):
                if i == len(special_folders) - 1:  # Last item
                    print(f'        "{folder}"')
                else:
                    print(f'        "{folder}",')
            print('    ]')
        
        print("}")
        
        print("\n📋 ALTERNATIVE: FLAT LIST FORMAT (for review_rating_selected_folders.py):")
        print("=" * 60)
        
        # Print in the format used in review_rating_selected_folders.py
        print("specific_folders = [")
        
        # Group by months for comments
        for year_month in sorted(folder_dict.keys()):
            month_folders = sorted(folder_dict[year_month])
            year = year_month[:4]
            month = year_month[4:6]
            month_name = {
                '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
                '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
                '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
            }.get(month, f'M{month}')
            
            print(f'    # {month_name} {year}')
            
            # Print folders in groups of 6 per line for readability
            for i in range(0, len(month_folders), 6):
                line_folders = month_folders[i:i+6]
                line = "    " + ", ".join(f'"{folder}"' for folder in line_folders)
                if i + 6 < len(month_folders) or year_month != sorted(folder_dict.keys())[-1]:
                    line += ","
                print(line)
            print()  # Empty line between months
        
        # Add special folders at the end
        if special_folders:
            print('    # Special folders')
            line = "    " + ", ".join(f'"{folder}"' for folder in sorted(special_folders))
            print(line)
        
        print("]")
        
        print("=" * 60)
        print(f"📊 Total: {len(folders)} folders")
        print(f"📅 Date folders: {sum(len(folders) for folders in folder_dict.values())}")
        print(f"🔧 Special folders: {len(special_folders)}")
        
        return folder_dict
        
    except Exception as e:
        print(f"❌ Error listing folders: {e}")
        return {}


def list_folders(container_client, prefix: str = ""):
    """
    List all 'folders' (prefixes) in the container.
    Azure Blob doesn't have true folders, but we infer them from blob names.
    If prefix is provided, it lists sub-folders under that prefix.
    """
    folder_set = set()

    # List blobs that start with prefix
    blob_list = container_client.list_blobs(name_starts_with=prefix)

    for blob in blob_list:
        # Split path after prefix
        relative_path = blob.name[len(prefix):].lstrip("/")
        if "/" in relative_path:   # has subfolder
            folder = relative_path.split("/")[0]
            folder_set.add(folder)

    return sorted(folder_set)



def download_all_output_files(folder_name: str, download_dir: str = "downloads"):
    os.makedirs(download_dir, exist_ok=True)

    blobs = container_client.list_blobs(name_starts_with=f"{folder_name}/output/")
    found_any = False

    for blob in blobs:
        found_any = True
        # save file with just the filename part (not full folder path)
        local_path = os.path.join(download_dir, f"{folder_name}_{os.path.basename(blob.name)}")
        blob_client = container_client.get_blob_client(blob)
        with open(local_path, "wb") as f:
            data = blob_client.download_blob()
            f.write(data.readall())
        print(f"✅ Downloaded {blob.name} -> {local_path}")

    if not found_any:
        print(f"⚠️ No files found under {folder_name}/output/")


def count_files_in_folder(folder_name: str) -> int:
    """
    Count how many blobs (files) are inside a given folder.
    """
    blob_list = container_client.list_blobs(name_starts_with=folder_name + "/")
    return sum(1 for _ in blob_list)


def count_all_output_files():
    """
    Count all files in output folders across the entire container.
    Returns detailed breakdown by folder and total count.
    """
    print("🔍 Scanning container for output files...")
    
    # Counter
    total_output_files = 0
    folder_counts = defaultdict(int)
    output_folders = set()
    scanned_count = 0
    
    # Scan all blobs in container with progress indicator
    try:
        for blob in container_client.list_blobs():
            scanned_count += 1
            if scanned_count % 1000 == 0:
                print(f"   Scanned {scanned_count} files...")
            
            blob_name = blob.name
            
            # Case 1: Any folder with "/output/" in the path
            if "/output/" in blob_name:
                # Extract the parent folder (first part of path)
                folder = blob_name.split("/")[0]
                folder_counts[folder] += 1
                total_output_files += 1
                output_folders.add(f"{folder}/output/")
            
            # Case 2: Special handling for specific output folders
            elif (blob_name.startswith("latest_full_release/") or 
                  blob_name.startswith("AI-review-rating-output01/") or
                  blob_name.startswith("AI-data-extract-output/") or
                  blob_name.startswith("latest_full_release_review-rating/")):
                folder = blob_name.split("/")[0]
                folder_counts[folder] += 1
                total_output_files += 1
                output_folders.add(folder)
    
    except Exception as e:
        print(f"❌ Error scanning container: {e}")
        return 0, {}, set()
    
    print(f"   ✅ Scanned {scanned_count} total files")
    
    # Print detailed breakdown
    print("\n📊 OUTPUT FILES BREAKDOWN:")
    print("=" * 60)
    
    if folder_counts:
        for folder, count in sorted(folder_counts.items()):
            print(f"📂 {folder:<40} : {count:>6} files")
    else:
        print("❌ No output files found!")
    
    print("=" * 60)
    print(f"📈 TOTAL OUTPUT FILES: {total_output_files}")
    print(f"📁 TOTAL OUTPUT FOLDERS: {len(output_folders)}")
    
    return total_output_files, folder_counts, output_folders


def count_files_by_keywords(keywords=None, folder_prefix=""):
    """
    Count files matching specific keywords in their names.
    """
    if keywords is None:
        keywords = ["Foot", "Ankle", "Plate", "Screws", "Screw", "Knee", "Hip"]
    
    print(f"🔍 Searching for files with keywords: {keywords}")
    if folder_prefix:
        print(f"📂 Restricting search to folder: {folder_prefix}")
    
    count = 0
    matching_files = []
    
    # List blobs with optional folder prefix
    blob_iterator = container_client.list_blobs(name_starts_with=folder_prefix)
    
    for blob in blob_iterator:
        if any(keyword.lower() in blob.name.lower() for keyword in keywords):
            matching_files.append(blob.name)
            count += 1
    
    print(f"\n📊 Found {count} files matching keywords")
    
    # Show first few matches as examples
    if matching_files:
        print("\n📋 Sample matches:")
        for i, file in enumerate(matching_files[:5]):
            print(f"   {i+1}. {file}")
        if len(matching_files) > 5:
            print(f"   ... and {len(matching_files) - 5} more files")
    
    return count, matching_files



if __name__ == "__main__":
    print("Azure Blob Container Analysis")
    print("=" * 50)

    if len(sys.argv) > 1 and sys.argv[1] == "--folders":
        list_all_folders()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--python-list":
        get_folders_as_python_list()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--python-dict":
        get_folders_as_python_dict()
        sys.exit(0)
    
    # First, let's check specific known output folders quickly
    print("📂 CHECKING SPECIFIC OUTPUT FOLDERS:")
    specific_folders = [
        'AI-review-rating-output01',
        'AI-data-extract-output', 
        'latest_full_release',
        'latest_full_release_review-rating'
    ]
    
    total_specific = 0
    for folder in specific_folders:
        try:
            count = count_files_in_folder(folder)
            print(f"   📂 {folder:<35} : {count:>6} files")
            total_specific += count
        except Exception as e:
            print(f"   ❌ {folder:<35} : Error - {e}")
    
    print(f"   📊 Total in specific folders: {total_specific}")
    
    # Now do the comprehensive scan
    print("\n" + "=" * 50)
    total_files, folder_breakdown, output_folders = count_all_output_files()
    
    # Show ALL top level folders
    print("\n📁 ALL TOP LEVEL FOLDERS:")
    try:
        top_folders = list_folders(container_client)
        print(f"Found {len(top_folders)} top-level folders")
        print("=" * 60)
        
        # Display all folders in a neat format
        for i, folder in enumerate(top_folders, 1):
            print(f"   {i:3d}. {folder}")
            
        print("=" * 60)
        print(f"📊 Total folders: {len(top_folders)}")
        
    except Exception as e:
        print(f"❌ Error listing folders: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 FINAL SUMMARY:")
    print(f"   • Total output files (comprehensive): {total_files}")
    print(f"   • Total in specific folders: {total_specific}")
    print(f"   • Output folders found: {len(output_folders)}")
    
    if folder_breakdown:
        print(f"   • Largest output folder: {max(folder_breakdown.items(), key=lambda x: x[1])}")

