import os
import time
import random
import pandas as pd
from dotenv import load_dotenv
# from openai import RateLimitError
import google.generativeai as genai
from azure.storage.blob import BlobServiceClient
from io import StringIO

# ---------------- Azure Setup ----------------
load_dotenv()
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)

load_dotenv()
GEMINI_API_KEY2 = os.getenv("GEMINI_API_KEY2")
genai.configure(api_key=GEMINI_API_KEY2)


orthopedic_user_review_phrases_varied = [
    "Recovery progress became smoother with",
    "Daily mobility felt more natural using",
    "Comfort during extended wear improved through",
    "Pain management was noticeably better with",
    "Confidence in walking increased thanks to",
    "Joint stability was enhanced by",
    "Rehabilitation exercises became easier with",
    "Long hours of use remained comfortable due to",
    "Every step felt more supported by",
    "Balance and posture improved noticeably through",
    "Relief during routine activities was experienced with",
    "Movement restrictions were reduced significantly by",
    "Healing felt more consistent using",
    "Support during therapy sessions was strengthened by",
    "Comfort throughout the recovery journey was ensured with",
    "Daily routines were maintained more easily through",
    "Strain on joints was reduced noticeably with",
    "Mobility challenges were overcome more effectively using",
    "Independence in daily tasks was regained thanks to",
    "Flexibility during rehabilitation was supported by",
    "Stability during physical activity was reinforced with",
    "Recovery confidence improved steadily through",
    "Everyday comfort and usability were increased by",
    "Rehabilitation outcomes became more positive with",
    "Long-term recovery felt more reliable thanks to",
    "Surgeons often highlight the reliability of",
    "Recovery milestones are easier to achieve with",
    "Specialized care teams often recommend",
    "Everyday mobility is supported effectively through",
    "Long-term orthopedic care is enhanced by",
    "Stability during healing is ensured with",
    "Efficient recovery practices are made possible by",
    "Patient-centered outcomes improve noticeably with",
    "Mobility challenges are addressed effectively by",
    "Support during daily movements was noticeably improved by",
    "Overall recovery time felt shorter with the help of",
    "Strength during rehabilitation sessions was maintained through",
    "Physical therapy progress advanced more steadily with",
    "Mobility during routine activities became easier thanks to",
    "Endurance throughout the day was supported effectively by",
    "Post-surgical recovery gained consistency using",
    "Daily independence was restored more quickly with",
    "Orthopedic comfort was sustained even during long use through",
    "Confidence in performing regular tasks was reinforced with",
    "Flexibility in movement returned more naturally by using",
    "Pain reduction remained consistent during recovery with",
    "Activity levels improved gradually through the support of",
    "Balance while walking outdoors became more secure using",
    "Return to normal routines was achieved faster with",
    "Joint protection was ensured during physical activity through",
    "Everyday strength and stability improved noticeably by",
    "Comfort in resting positions was maintained with",
    "Smoother recovery transitions were supported effectively by",
    "Quality of life improved significantly with the use of",
    "Reliable support during strenuous activities was provided by",
    "Confidence during social and work activities was regained through",
    "Rehabilitation challenges were managed more easily using",
    "Durability and lasting comfort were experienced with",
    "Consistent orthopedic support was evident throughout recovery with",
    "Mobility returned to near-normal levels thanks to",
    "Adaptation to daily tasks became faster using",
    "The transition back to active living was made easier by",
    "Physical strain was minimized significantly with",
    "Confidence in long-term recovery increased through",
]


def generate_review(product_name, description):
    start_phrase = random.choice(orthopedic_user_review_phrases_varied)

    system = {
        "role": "system",
        "content": (
            "You are a professional reviewer focusing on natural, varied, human-like product reviews. "
            "Avoid repetition in starting words, formatting and style—each review must feel fresh."
        )
    }

    user_template = """
    Write a single-paragraph, human-like product review in exactly 8 to 10 lines.
    The opening sentence must use this starting phrase: "{start_phrase}" 
    and must not reuse the same first three words as any previous review.
    Do not start with: "This product", "When it comes to".
    Open with a fresh phrase. Mention one strength and one possible limitation using simple words.
    Avoid starting with the same phrase as the previous one; modify the opening to make it different.
    Do not use product's serial number or model number (such as HT-401124, HT-31832, HT-401122, etc).
    Maintain a warm, conversational yet professional tone and use clear, simple language.

    IMPORTANT: Do not include any special or garbled characters (such as â€™, â€œ, â€, or similar encoding artifacts).
    Only use standard English letters, numbers, punctuation (.,!?'), and common symbols.

    Product Name: {product_name}
    Description: {description}
    """

    while True:
        try:
            start_row = time.time()
            model = genai.GenerativeModel("gemini-2.5-flash-lite") # gemini-2.5-flash-lite gemini-2.0-flash
            prompt = f"{system}\n\n" + user_template.format(
                start_phrase=start_phrase,
                product_name=product_name,
                description=description
            )

            response = model.generate_content(prompt)

            end_row = time.time()
            print(f"⏱️ Time taken for this row: {end_row - start_row:.2f} seconds")

            sleep_time = random.uniform(2, 5) 
            print(f"Sleeping {sleep_time:.2f} seconds...\n")
            time.sleep(sleep_time)

            return response.text.strip()

        except Exception as e:
            print(f"⚠️ API error: {e}. Waiting 25 seconds before retrying...")
            time.sleep(25)


def process_folder(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if file.endswith(".csv"):
            input_path = os.path.join(input_folder, file)
            output_file = os.path.splitext(file)[0] + "-AI-review.csv"
            output_path = os.path.join(output_folder, output_file)

            print(f"\n📂 Processing file: {file}")

            df = pd.read_csv(input_path)
            print("reading complete! now you can start the process")
            if "AI_review" not in df.columns:
                df["AI_review"] = ""

            start_time = time.time()

            for idx, row in df.iterrows():
                if pd.isna(row["AI_review"]) or row["AI_review"] == "":
                    review = generate_review(row.get("Version or Model Number", ""), row.get("Device Description", ""))
                    # review = generate_review(row.get["Version or Model Number"], row.get["Device Description"])

                    df.at[idx, "AI_review"] = review

                    df.to_csv(output_path, index=False)
                    print(f"✅ Saved review for row {idx} in {output_file}")

            end_time = time.time()
            print(f"🎉 Completed {file} -> {output_file}")
            print(f"⏳ Total time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    input_folder = "InputFiles_01"   # InputFiles_01          InputFiles_Long-des
    output_folder = "OutputFiles_01" # output folder          OutputFiles_01
    process_folder(input_folder, output_folder)






# # Path to save output incrementally
# output_file = "main_output/C2_2_100_re_rows.csv"

# # Add an empty "AI_review" column first if not already present
# if "AI_review" not in df.columns:
#     df["AI_review"] = ""

# start_time = time.time()

# # Process only rows without AI_review
# remaining_rows = df[df["AI_review"].isna() | (df["AI_review"] == "")]

# print(f"📝 Total remaining rows to process: {len(remaining_rows)}")


# # Process row by row
# for idx, row in remaining_rows.iterrows():
#     try:
#         if pd.isna(row["AI_review"]) or row["AI_review"] == "":
#             review = generate_review(row["product_name_displayed"], row["description"])
#             df.at[idx, "AI_review"] = review

#             # Save after each review
#             df.to_csv(output_file, index=False)
#             print(f"✅ Saved review for row {idx} to CSV")
    
#     except Exception as e:
#         print(f"⚠️ Error at row {idx}: {e}. Waiting 25 seconds before retrying...")
#         time.sleep(25)

# end_time = time.time()
# print("🎉 All reviews generated and saved incrementally!")
# print(f"⏳ Total time taken: {end_time - start_time:.2f} seconds")
