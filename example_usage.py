"""
Example usage of Azure CSV Fetcher

This file demonstrates how to use the azure_csv_fetcher module to download
CSV files from Azure Blob Storage containers.
"""

from azure_csv_fetcher import fetch_csv_files_from_azure, list_csv_files_in_container, fetch_single_csv_file
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure credentials - replace with your actual values or set as environment variables
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING") or "your_connection_string_here"
AZURE_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME") or "your_container_name_here"


def example_1_list_all_csv_files():
    """Example 1: List all CSV files in the container"""
    print("📋 Example 1: Listing all CSV files")
    print("-" * 40)
    
    csv_files = list_csv_files_in_container(
        connection_string=AZURE_CONNECTION_STRING,
        container_name=AZURE_CONTAINER_NAME
    )
    
    print(f"Found {len(csv_files)} CSV files:")
    for i, file in enumerate(csv_files[:5], 1):  # Show first 5
        print(f"  {i}. {file}")
    
    if len(csv_files) > 5:
        print(f"  ... and {len(csv_files) - 5} more files")
    
    return csv_files


def example_2_fetch_all_csv_as_dataframes():
    """Example 2: Fetch all CSV files as pandas DataFrames"""
    print("\n📊 Example 2: Fetching CSV files as DataFrames")
    print("-" * 40)
    
    result = fetch_csv_files_from_azure(
        connection_string=AZURE_CONNECTION_STRING,
        container_name=AZURE_CONTAINER_NAME,
        return_as_dataframes=True
    )
    
    if result['success']:
        print(f"✅ {result['message']}")
        print(f"\n📈 Data Summary:")
        
        for filename, df in result['data'].items():
            print(f"  • {filename}:")
            print(f"    - Shape: {df.shape}")
            print(f"    - Columns: {list(df.columns)[:3]}{'...' if len(df.columns) > 3 else ''}")
            print(f"    - Sample data:")
            print(f"      {df.head(2).to_string().replace(chr(10), chr(10) + '      ')}")
            print()
    else:
        print(f"❌ {result['message']}")
    
    return result


def example_3_fetch_from_specific_folder():
    """Example 3: Fetch CSV files from a specific folder"""
    print("\n📂 Example 3: Fetching CSV files from specific folder")
    print("-" * 40)
    
    # Example: fetch from a date folder (adjust folder_prefix as needed)
    folder_prefix = "20250315/"  # Change this to match your folder structure
    
    result = fetch_csv_files_from_azure(
        connection_string=AZURE_CONNECTION_STRING,
        container_name=AZURE_CONTAINER_NAME,
        folder_prefix=folder_prefix,
        return_as_dataframes=True
    )
    
    if result['success']:
        print(f"✅ Found {result['count']} CSV files in folder '{folder_prefix}'")
        for filename, df in result['data'].items():
            print(f"  • {filename}: {df.shape}")
    else:
        print(f"❌ {result['message']}")
    
    return result


def example_4_download_files_locally():
    """Example 4: Download CSV files to local directory"""
    print("\n💾 Example 4: Downloading CSV files locally")
    print("-" * 40)
    
    result = fetch_csv_files_from_azure(
        connection_string=AZURE_CONNECTION_STRING,
        container_name=AZURE_CONTAINER_NAME,
        folder_prefix="",  # Empty to get all files
        download_to_local=True,
        local_download_path="downloaded_csv_files"
    )
    
    if result['success']:
        print(f"✅ Downloaded {result['count']} files to 'downloaded_csv_files/' folder")
        for filename, local_path in result['data'].items():
            print(f"  • {filename} -> {local_path}")
    else:
        print(f"❌ {result['message']}")
    
    return result


def example_5_fetch_single_file():
    """Example 5: Fetch a single specific CSV file"""
    print("\n🎯 Example 5: Fetching a single CSV file")
    print("-" * 40)
    
    # First, get list of available files
    csv_files = list_csv_files_in_container(AZURE_CONNECTION_STRING, AZURE_CONTAINER_NAME)
    
    if csv_files:
        # Take the first CSV file as example
        target_file = csv_files[0]
        print(f"Fetching: {target_file}")
        
        df = fetch_single_csv_file(
            connection_string=AZURE_CONNECTION_STRING,
            container_name=AZURE_CONTAINER_NAME,
            file_path=target_file,
            return_as_dataframe=True
        )
        
        if df is not None:
            print(f"✅ Successfully loaded file")
            print(f"   Shape: {df.shape}")
            print(f"   Columns: {list(df.columns)}")
            print(f"   First few rows:")
            print(df.head(3))
        else:
            print("❌ Failed to load file")
    else:
        print("❌ No CSV files found in container")


def main():
    """Run all examples"""
    print("🚀 Azure CSV Fetcher - Example Usage")
    print("=" * 50)
    
    # Check if credentials are set
    if AZURE_CONNECTION_STRING == "your_connection_string_here" or AZURE_CONTAINER_NAME == "your_container_name_here":
        print("⚠️  Please update the connection string and container name in this file")
        print("   Or set environment variables:")
        print("   - AZURE_STORAGE_CONNECTION_STRING")
        print("   - AZURE_BLOB_CONTAINER_NAME")
        return
    
    try:
        # Run examples
        example_1_list_all_csv_files()
        example_2_fetch_all_csv_as_dataframes()
        example_3_fetch_from_specific_folder()
        example_4_download_files_locally()
        example_5_fetch_single_file()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {str(e)}")
        print("Please check your Azure credentials and container name.")


if __name__ == "__main__":
    main()