import os
from collections import defaultdict
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from azure.storage.blob import ContainerClient


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



container_client = ContainerClient.from_connection_string(
    conn_str=AZURE_STORAGE_CONNECTION_STRING,
    container_name=AZURE_BLOB_CONTAINER_NAME
)
keywords = ["Foot", "Ankle", "Plate", "Screws", "Screw", "Knee", "Hip"]

# Folder prefix to restrict search
folder_prefix = "latest_full_release/"

count = 0
# print("Matching files inside 'latest_full_release':\n")

# List only blobs within the folder
for blob in container_client.list_blobs(name_starts_with=folder_prefix):
    if any(keyword.lower() in blob.name.lower() for keyword in keywords):
        # print(blob.name)
        count += 1

print("\n📂📂Total matching files:", count)


# # Counter
# total_output_files = 0
# folder_counts = defaultdict(int)

# for blob in container_client.list_blobs():
#     blob_name = blob.name

#     # Case 1: Any "output/" folder file
#     if "/output/" in blob_name:
#         # Extract the parent folder (first part of path)
#         folder = blob_name.split("/")[0]
#         folder_counts[folder] += 1
#         total_output_files += 1

#     # Case 2: Special handling for "latest_full_release"
#     elif blob_name.startswith("latest_full_release/"):
#         folder_counts["latest_full_release"] += 1
#         total_output_files += 1

# # Print breakdown
# for folder, count in folder_counts.items():
#     print(f"📂 {folder}: {count} output files")

# print(f"\n📊 Total files in ALL output folders (including latest_full_release): {total_output_files}")

if __name__ == "__main__":
    folders1 = ['AI-review-rating-output01']  # have 15 files
    folders = ['AI-data-extract-output/latest_full_release_data-extract']  # have 15 files
    folders2 = ['latest_full_release_review-rating']  # have 15 files
    folders3 = ['latest_full_release']  # have 15 files

    top_folders = list_folders(container_client)
    print("Top level folders:", top_folders)

    # for folder in folders3:
    #     count = count_files_in_folder(folder)
    #     print(f"📂 {folder}: {count} files")

    # for folder in folders1:
    #     count = count_files_in_folder(folder)
    #     print(f"📂 {folder}: {count} files")

    # for folder in folders:
    #     count = count_files_in_folder(folder)
    #     print(f"📂 {folder}: {count} files")

    # for folder in folders2:
    #     count = count_files_in_folder(folder)
    #     print(f"📂 {folder}: {count} files")


    # for folder in folders:
    #     download_all_output_files(folder, download_dir="downloads")

    
    # # List subfolders under a given folder
    # subfolders = list_folders(container_client, prefix="AI-review-rating-output01")
    # print("Subfolders inside '20250915':", subfolders)

    # # List files
    # for folder in folders:
    #     list_files_in_folder(folder)

    # Upload file
    # create_folder_and_upload_file(folder, file_to_upload)


# Top level folders: [
# '20250211', '20250212', '20250213', '20250214', '20250217', '20250218', '20250219', '20250220', '20250221', '20250224', '20250225', '20250226', '20250227', '20250228', 
# '20250303', '20250304', '20250305', '20250306', '20250307', '20250310', '20250311', '20250312', '20250313', '20250314', '20250317', '20250318', '20250319', '20250320', '20250321', '20250324', '20250325', '20250326', '20250327', '20250328', '20250331', 
# '20250401', '20250402', '20250403', '20250404', '20250407', '20250408', '20250409', '20250410', '20250411', '20250414', '20250415', '20250416', '20250417', '20250418', '20250421', '20250422', '20250423', '20250424', '20250425', '20250428', '20250429', '20250430', 

# '20250502', '20250505', '20250506', '20250507', '20250508', '20250509', '20250512', '20250513', '20250514', '20250515', '20250516', '20250519', '20250520', '20250521', '20250522', '20250523', '20250526', '20250527', '20250528', '20250529', '20250530', 
# '20250602', '20250603', '20250604', '20250605', '20250606', '20250609', '20250610', '20250611', '20250612', '20250613', '20250617', '20250618', '20250620', '20250623', '20250624', '20250625', '20250626', '20250627', 

# '20250701', '20250703', '20250704', '20250707', '20250708', '20250709', '20250710', '20250711', '20250714', '20250715', '20250716', '20250717', '20250718', '20250721', '20250722', '20250723', '20250724', '20250725', '20250728', '20250729', '20250730', '20250731',
#  
# '20250804', '20250805', '20250806', '20250807', '20250808', '20250811', '20250812', '20250813', '20250814', '20250815', '20250818', '20250819', '20250820', '20250821', '20250822', '20250825', '20250826', '20250827', '20250828', '20250829', 

# '20250902', '20250903', '20250904', '20250905', '20250908', '20250909', '20250910', '20250911', '20250912', '20250915', '20250916', '20250917', '20250919', '20250922', '20250923', '20250925', '20250926', '20250929', '20250930', 
# 
# '20251002', '20251003', '20251006', '20251007',
# 
#  'AI-data-extract-output', 'AI-review-rating-output01', 'latest_full_release', 'latest_full_release_review-rating']





# Request for Salary Revision

# Dear Management Team,

# I hope this email finds you well.

# I am writing to kindly request a revision of my current salary. At present, my salary is ₹8,000, which is quite minimal, and after monthly deductions, very little remains at hand


# When I joined the company, I had limited knowledge and therefore kept my salary expectations low.
# At that time, I think salary will increase after the probation period. 





# import os
# from azure.storage.blob import BlobServiceClient
# from dotenv import load_dotenv

# load_dotenv()

# AZURE_STORAGE_CONNECTION_STRING = "InstrumentationKey=016f36c5-d29b-4fb8-9765-ac01532bfcef;IngestionEndpoint=https://eastus2-3.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus2.livediagnostics.monitor.azure.com/;ApplicationId=ae0d9508-7385-4956-9076-df6419d6356b"
# # Load connection string and container name from env
# # AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
# # AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

# # Create blob service client
# blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# # Get container client
# container_client = blob_service_client.get_container_client("surgzondata")


# # def create_folder_and_upload_file(folder_name: str, file_path: str, blob_name: str = None):
# #     """
# #     Upload a file into a 'folder' inside the container.
# #     Azure Blob doesn't have real folders, we simulate using prefix: folder/file.txt
# #     """
# #     if not blob_name:
# #         blob_name = os.path.basename(file_path)

# #     # Full path in blob = folder_name/file_name
# #     blob_path = f"{folder_name}/{blob_name}"

# #     blob_client = container_client.get_blob_client(blob_path)
# #     with open(file_path, "rb") as data:
# #         blob_client.upload_blob(data, overwrite=True)

# #     print(f"Uploaded {file_path} to {blob_path}")


# def list_files_in_folder(folder_name: str):
#     """
#     List all blobs with a given prefix (simulating a folder).
#     """
#     print(f"Files in folder '{folder_name}':")
#     blob_list = container_client.list_blobs(name_starts_with=folder_name + "/")
#     for blob in blob_list:
#         print(f"- {blob.name}")


# # def download_file(folder_name: str, blob_name: str, download_path: str):
# #     """
# #     Download a blob (file) from the folder to local path.
# #     """
# #     blob_path = f"{folder_name}/{blob_name}"
# #     blob_client = container_client.get_blob_client(blob_path)

# #     with open(download_path, "wb") as f:
# #         data = blob_client.download_blob()
# #         f.write(data.readall())

# #     print(f"Downloaded {blob_path} to {download_path}")


# if __name__ == "__main__":
#     # Example usage
#     folder = "20250915"
#     # file_to_upload = "example.txt"

#     # Upload file
#     # create_folder_and_upload_file(folder, file_to_upload)

#     # List files
#     list_files_in_folder(folder)

#     # Download file back
#     # download_file(folder, "example.txt", "downloaded_example.txt")

 