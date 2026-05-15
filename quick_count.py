#!/usr/bin/env python3
"""
Quick count of files in Azure blob container output folders
"""
import os
from collections import defaultdict
from azure.storage.blob import BlobServiceClient, ContainerClient
from dotenv import load_dotenv

# Load environment
load_dotenv()
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

container_client = ContainerClient.from_connection_string(
    conn_str=AZURE_STORAGE_CONNECTION_STRING,
    container_name=AZURE_BLOB_CONTAINER_NAME
)

def quick_count_output_files():
    """Quick count of output files with progress"""
    print("🔍 Quick scanning for output files...")
    
    total_output_files = 0
    folder_counts = defaultdict(int)
    scanned = 0
    
    try:
        for blob in container_client.list_blobs():
            scanned += 1
            if scanned % 2000 == 0:
                print(f"   📊 Scanned {scanned:,} files, found {total_output_files:,} output files...")
            
            blob_name = blob.name
            
            # Check for output patterns
            if ("/output/" in blob_name or 
                blob_name.startswith("AI-review-rating-output01/") or
                blob_name.startswith("AI-data-extract-output/") or
                blob_name.startswith("latest_full_release/") or
                blob_name.startswith("latest_full_release_review-rating/")):
                
                folder = blob_name.split("/")[0]
                folder_counts[folder] += 1
                total_output_files += 1
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0, {}
    
    print(f"✅ Scan complete! Checked {scanned:,} total files")
    
    # Show results
    print("\n📊 OUTPUT FILES BY FOLDER:")
    print("=" * 50)
    
    if folder_counts:
        # Sort by count (descending)
        sorted_folders = sorted(folder_counts.items(), key=lambda x: x[1], reverse=True)
        
        for folder, count in sorted_folders[:20]:  # Show top 20
            print(f"📂 {folder:<30} : {count:>6} files")
        
        if len(sorted_folders) > 20:
            remaining = sum(count for _, count in sorted_folders[20:])
            print(f"📂 {'... other folders':<30} : {remaining:>6} files")
    
    print("=" * 50)
    print(f"📈 TOTAL OUTPUT FILES: {total_output_files:,}")
    print(f"📁 TOTAL OUTPUT FOLDERS: {len(folder_counts)}")
    
    return total_output_files, folder_counts

def count_specific_folders():
    """Count files in specific known output folders"""
    print("\n🎯 CHECKING SPECIFIC OUTPUT FOLDERS:")
    
    specific_folders = [
        'AI-review-rating-output01',
        'AI-data-extract-output', 
        'latest_full_release',
        'latest_full_release_review-rating'
    ]
    
    total_specific = 0
    for folder in specific_folders:
        try:
            count = sum(1 for _ in container_client.list_blobs(name_starts_with=folder + "/"))
            print(f"   📂 {folder:<35} : {count:>6} files")
            total_specific += count
        except Exception as e:
            print(f"   ❌ {folder:<35} : Error")
    
    print(f"   📊 Total in specific folders: {total_specific:,}")
    return total_specific

if __name__ == "__main__":
    print("🚀 Quick Azure Blob Analysis")
    print("=" * 50)
    
    # Check specific folders first (fast)
    specific_total = count_specific_folders()
    
    # Do comprehensive scan
    total_files, folder_breakdown = quick_count_output_files()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 FINAL SUMMARY:")
    print(f"   • Total output files (comprehensive): {total_files:,}")
    print(f"   • Total in specific folders: {specific_total:,}")
    print(f"   • Number of output folders: {len(folder_breakdown)}")
    
    if folder_breakdown:
        top_folder = max(folder_breakdown.items(), key=lambda x: x[1])
        print(f"   • Largest folder: {top_folder[0]} ({top_folder[1]:,} files)")