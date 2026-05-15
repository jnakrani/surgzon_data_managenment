"""
Azure CSV File Fetcher

A utility function to fetch CSV files from Azure Blob Storage containers.
This function can be used by developers to easily download CSV files from Azure containers.

Requirements:
- azure-storage-blob
- python-dotenv (optional, for environment variables)

Usage:
    from azure_csv_fetcher import fetch_csv_files_from_azure
    
    # Fetch all CSV files from a container
    files = fetch_csv_files_from_azure(
        connection_string="your_connection_string",
        container_name="your_container_name"
    )
    
    # Fetch CSV files from specific folder
    files = fetch_csv_files_from_azure(
        connection_string="your_connection_string",
        container_name="your_container_name",
        folder_prefix="data/2024/"
    )
"""

import os
import pandas as pd
from typing import List, Dict, Optional
from azure.storage.blob import BlobServiceClient, ContainerClient
from io import StringIO


def fetch_csv_files_from_azure(
    connection_string: str,
    container_name: str,
    folder_prefix: str = "",
    download_to_local: bool = False,
    local_download_path: str = "downloads",
    return_as_dataframes: bool = True
) -> Dict[str, any]:
    """
    Fetch CSV files from Azure Blob Storage container.
    
    Args:
        connection_string (str): Azure Storage connection string
        container_name (str): Name of the Azure container
        folder_prefix (str, optional): Folder path prefix to filter files (e.g., "data/2024/")
        download_to_local (bool, optional): Whether to download files locally. Defaults to False.
        local_download_path (str, optional): Local path to save files. Defaults to "downloads".
        return_as_dataframes (bool, optional): Whether to return pandas DataFrames. Defaults to True.
    
    Returns:
        Dict containing:
        - 'files': List of CSV file names found
        - 'data': Dict of DataFrames (if return_as_dataframes=True) or file paths (if downloaded locally)
        - 'count': Number of CSV files found
        - 'success': Boolean indicating success
        - 'message': Status message
    
    Example:
        result = fetch_csv_files_from_azure(
            connection_string="DefaultEndpointsProtocol=https;AccountName=...",
            container_name="mycontainer",
            folder_prefix="data/",
            return_as_dataframes=True
        )
        
        if result['success']:
            print(f"Found {result['count']} CSV files")
            for filename, df in result['data'].items():
                print(f"{filename}: {len(df)} rows")
    """
    
    try:
        # Initialize Azure clients
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        # Find all CSV files
        csv_files = []
        blob_list = container_client.list_blobs(name_starts_with=folder_prefix)
        
        for blob in blob_list:
            if blob.name.lower().endswith('.csv'):
                csv_files.append(blob.name)
        
        if not csv_files:
            return {
                'files': [],
                'data': {},
                'count': 0,
                'success': True,
                'message': f"No CSV files found in container '{container_name}' with prefix '{folder_prefix}'"
            }
        
        # Process files
        data_dict = {}
        
        if download_to_local:
            # Create local download directory
            os.makedirs(local_download_path, exist_ok=True)
            
            for csv_file in csv_files:
                # Download file locally
                filename = os.path.basename(csv_file)
                local_file_path = os.path.join(local_download_path, filename)
                
                blob_client = container_client.get_blob_client(csv_file)
                with open(local_file_path, "wb") as download_file:
                    download_file.write(blob_client.download_blob().readall())
                
                data_dict[filename] = local_file_path
                print(f"✅ Downloaded: {csv_file} -> {local_file_path}")
        
        elif return_as_dataframes:
            # Load files directly into pandas DataFrames
            for csv_file in csv_files:
                try:
                    blob_client = container_client.get_blob_client(csv_file)
                    csv_content = blob_client.download_blob().content_as_text()
                    
                    # Convert to pandas DataFrame
                    df = pd.read_csv(StringIO(csv_content))
                    filename = os.path.basename(csv_file)
                    data_dict[filename] = df
                    
                    print(f"✅ Loaded: {csv_file} ({len(df)} rows, {len(df.columns)} columns)")
                    
                except Exception as e:
                    print(f"⚠️ Error loading {csv_file}: {str(e)}")
                    continue
        
        else:
            # Just return file names and blob references
            for csv_file in csv_files:
                filename = os.path.basename(csv_file)
                data_dict[filename] = csv_file
        
        return {
            'files': csv_files,
            'data': data_dict,
            'count': len(csv_files),
            'success': True,
            'message': f"Successfully processed {len(csv_files)} CSV files from container '{container_name}'"
        }
        
    except Exception as e:
        return {
            'files': [],
            'data': {},
            'count': 0,
            'success': False,
            'message': f"Error fetching CSV files: {str(e)}"
        }


def list_csv_files_in_container(connection_string: str, container_name: str, folder_prefix: str = "") -> List[str]:
    """
    List all CSV files in an Azure container without downloading them.
    
    Args:
        connection_string (str): Azure Storage connection string
        container_name (str): Name of the Azure container
        folder_prefix (str, optional): Folder path prefix to filter files
    
    Returns:
        List[str]: List of CSV file paths in the container
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        csv_files = []
        blob_list = container_client.list_blobs(name_starts_with=folder_prefix)
        
        for blob in blob_list:
            if blob.name.lower().endswith('.csv'):
                csv_files.append(blob.name)
        
        return csv_files
        
    except Exception as e:
        print(f"Error listing CSV files: {str(e)}")
        return []


def fetch_single_csv_file(
    connection_string: str,
    container_name: str,
    file_path: str,
    return_as_dataframe: bool = True
) -> Optional[pd.DataFrame]:
    """
    Fetch a single CSV file from Azure Blob Storage.
    
    Args:
        connection_string (str): Azure Storage connection string
        container_name (str): Name of the Azure container
        file_path (str): Full path to the CSV file in the container
        return_as_dataframe (bool): Whether to return as pandas DataFrame
    
    Returns:
        pandas.DataFrame or str: DataFrame if return_as_dataframe=True, else file content as string
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        blob_client = container_client.get_blob_client(file_path)
        csv_content = blob_client.download_blob().content_as_text()
        
        if return_as_dataframe:
            df = pd.read_csv(StringIO(csv_content))
            print(f"✅ Loaded: {file_path} ({len(df)} rows, {len(df.columns)} columns)")
            return df
        else:
            return csv_content
            
    except Exception as e:
        print(f"Error fetching file {file_path}: {str(e)}")
        return None


# Example usage and testing
if __name__ == "__main__":
    # Example usage - replace with your actual credentials
    
    # Option 1: Using environment variables (recommended)
    from dotenv import load_dotenv
    load_dotenv()
    
    CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")
    
    if CONNECTION_STRING and CONTAINER_NAME:
        print("🚀 Testing Azure CSV Fetcher")
        print("=" * 50)
        
        # List all CSV files first
        print("📋 Listing all CSV files...")
        csv_files = list_csv_files_in_container(CONNECTION_STRING, CONTAINER_NAME)
        print(f"Found {len(csv_files)} CSV files:")
        for i, file in enumerate(csv_files[:10], 1):  # Show first 10
            print(f"  {i}. {file}")
        if len(csv_files) > 10:
            print(f"  ... and {len(csv_files) - 10} more files")
        
        # Fetch CSV files from a specific folder (example)
        print(f"\n📂 Fetching CSV files from container...")
        result = fetch_csv_files_from_azure(
            connection_string=CONNECTION_STRING,
            container_name=CONTAINER_NAME,
            folder_prefix="",  # Empty to get all CSV files, or specify like "data/"
            return_as_dataframes=True
        )
        
        if result['success']:
            print(f"✅ {result['message']}")
            print(f"📊 Data summary:")
            for filename, df in result['data'].items():
                print(f"  • {filename}: {len(df)} rows × {len(df.columns)} columns")
        else:
            print(f"❌ {result['message']}")
    
    else:
        print("⚠️ Please set AZURE_STORAGE_CONNECTION_STRING and AZURE_BLOB_CONTAINER_NAME environment variables")
        print("\nExample usage:")
        print("""
        # Set environment variables or pass directly:
        result = fetch_csv_files_from_azure(
            connection_string="DefaultEndpointsProtocol=https;AccountName=...",
            container_name="your-container-name",
            folder_prefix="data/2024/",  # Optional: filter by folder
            return_as_dataframes=True
        )
        
        if result['success']:
            for filename, dataframe in result['data'].items():
                print(f"File: {filename}")
                print(f"Shape: {dataframe.shape}")
                print(dataframe.head())
        """)