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
               "MRI Safety Status ",
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
