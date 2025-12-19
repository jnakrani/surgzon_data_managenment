# import pandas as pd

# # Load the Excel file
# file_path = "SZO-Filtered_File.xlsx"
# df = pd.read_excel(file_path, header=0)

# # Get first 30 rows
# # first_30_rows = df.head(30)

# subset_rows = df.iloc[649:681] 

# # Save to new Excel file
# output_path = "sample_     rows_from_SZO-Filtered_File.xlsx"
# subset_rows.to_excel(output_path, index=False)

# print(f"✅ sample rows saved to {output_path}")



# 
# import pandas as pd

# # ==========================
# # CONFIG
# # ==========================
# INPUT_FILE = "SZO-Filtered_File.xlsx"          # Path to your Excel file
# OUTPUT_FILE = "sample_10_output.xlsx" # Path to save the sampled file
# SAMPLE_SIZE = 20                    # Number of rows you want in the sample

# # ==========================
# # LOAD EXCEL
# # ==========================
# print("📥 Loading Excel file...")
# df = pd.read_excel(INPUT_FILE)

# print(f"Total rows in file: {len(df)}")

# # ==========================
# # RANDOM SAMPLE
# # ==========================
# sample_df = df.sample(n=SAMPLE_SIZE, random_state=42)  # random_state for reproducibility
# print(f"Sampled {SAMPLE_SIZE} rows.")

# # ==========================
# # SAVE SAMPLE
# # ==========================
# sample_df.to_excel(OUTPUT_FILE, index=False)
# print(f"✅ Sample saved to {OUTPUT_FILE}")



import pandas as pd

# File paths
file_path = "Medical_GmbH-202509.csv"      # input file  Data_Extractor/LIMACORPORATE SPA-202509.csv
output_file = "Medical_GmbH-202509-input-columns.csv"  # output file

# Load the CSV file (use header=0 unless headers are on the second row)
df = pd.read_csv(file_path, header=0)

# Show columns to verify exact names
print("Columns in CSV:", df.columns.tolist())

# Select only the needed columns (make sure these names exist)
needed_cols = ["Public Device Record Key", 
               "Public Version Number", 
               "Public Version Date", 
               "DI Record Publish Date", 
               "Commercial Distribution Status", 
               "Brand Name",  
               "Catalog Number", 
               "Company Name", 
               "Device Count", 
               "Device Description", 
               "Size Value", 
               "Size Text", 
               "Device Exempt from Premarket Submission", 
               "Human Cell,Tissue or Cellular or Tissue-Based Product (HCT/P)", 
               "Kit", 
               "Combination Product", 
               "For Single-Use", 
               "Device required to be labeled as containing natural rubber latex or dry natural rubber (21 CFR 801.437)", 
               "Device labeled as 'Not made with natural rubber latex", 
               "MRI Safety Status ",  
               "GMDN Code", 
               "GMDN PT Name", 
               "GMDN PT Definition", 
               "Implantable", 
               "FDA Product Code", 
               "FDA Product Code Name", 
               "Device Packaged as Sterile", 
               "Requires Sterilization Prior to Use", 
               "Sterilization Method"]
df_filtered = df[needed_cols]

# Save to a new CSV
df_filtered.to_csv(output_file, index=False)

print(f"✅ New file saved as: {output_file}")

