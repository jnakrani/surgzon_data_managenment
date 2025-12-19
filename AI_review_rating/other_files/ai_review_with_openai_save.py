import os
import time
import random
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from openai import RateLimitError

# Load environment variables
load_dotenv()
OPENAI_API_KEY2 = os.getenv("OPENAI_API_KEY2")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY2)

# Load your CSV file
# df = pd.read_csv("C:/tarun-bitcoding/Surgzon/CROSSROADS_EXTREMITY_SYSTEMS-202509_output.csv")
# "C:/tarun-bitcoding/Surgzon/CROSSROADS_EXTREMITY_SYSTEMS-202509_output.csv"

# Custom varied starting phrases
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

# Function to generate AI review
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
    Write a single-paragraph, human-like product review in exactly 5 to 7 lines.
    The opening sentence must use this starting phrase: "{start_phrase}" 
    and must not reuse the same first three words as any previous review.
    Do not start with: "This product", "When it comes to".
    Open with a fresh phrase. Mention one strength and one possible limitation.
    Avoid starting with the same phrase as the previous one; modify the opening to make it different.
    Maintain a warm, conversational yet professional tone.

    Product Name: {product_name}
    Description: {description}
    """

    while True:
        try:
            start_row = time.time()
            response = client.chat.completions.create(
                model="gpt-4o-mini", #gpt-4o-mini 4.1
                messages=[
                    system,
                    {"role": "user", "content": user_template.format(
                        start_phrase=start_phrase,
                        product_name=product_name,
                        description=description
                    )}
                ],
                max_tokens=200,
                temperature=0.7
            )
            end_row = time.time()
            print(f"⏱️ Time taken for this row: {end_row - start_row:.2f} seconds")
            
            # sleep_time = random.uniform(2, 4)  # avoid API rate limit
            # print(f"Sleeping {sleep_time:.2f} seconds...\n")
            # time.sleep(sleep_time)

            return response.choices[0].message.content.strip()
        
        except RateLimitError as e:
            print("⚠️ Rate limit hit. Waiting 25 seconds before retrying...")
            print(e)
            time.sleep(25)

 

# Automation: Process all CSVs in a folder
def process_folder(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if file.endswith(".csv"):
            input_path = os.path.join(input_folder, file)
            output_file = os.path.splitext(file)[0] + "-AI-review.csv"
            output_path = os.path.join(output_folder, output_file)

            print(f"\n📂 Processing file: {file}")

            df = pd.read_csv(input_path)

            # Add AI_review column if missing
            if "AI_review" not in df.columns:
                df["AI_review"] = ""

            start_time = time.time()

            for idx, row in df.iterrows():
                if pd.isna(row["AI_review"]) or row["AI_review"] == "":
                    review = generate_review(row.get("Version or Model Number", ""), row.get("Device Description", ""))
                    # review = generate_review(row.get["Version or Model Number"], row.get["Device Description"])

                    df.at[idx, "AI_review"] = review

                    # Save incrementally
                    df.to_csv(output_path, index=False)
                    print(f"✅ Saved review for row {idx} in {output_file}")

            end_time = time.time()
            print(f"🎉 Completed {file} -> {output_file}")
            print(f"⏳ Total time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    input_folder = "InputFiles_Long-des"   # put your input CSV folder here #AI_review_rating/InputFiles_01 AI_review_rating/InputFiles_Long-des
    output_folder = "OutputFiles_Long-des" # output folder
    process_folder(input_folder, output_folder)






# # Path to save output incrementally
# output_file = "Cross_Output.csv"

# # Add an empty "AI_review" column first if not already present
# if "AI_review" not in df.columns:
#     df["AI_review"] = ""

# start_time = time.time()

# # Process row by row
# for idx, row in df.iterrows():
#     if pd.isna(row["AI_review"]) or row["AI_review"] == "":
#         review = generate_review(row["Version or Model Number"], row["Device Description"])
#         df.at[idx, "AI_review"] = review

#         # Save after each review
#         df.to_csv(output_file, index=False)
#         print(f"✅ Saved review for row {idx} to CSV")

# end_time = time.time()
# print("🎉 All reviews generated and saved incrementally!")
# print(f"⏳ Total time taken: {end_time - start_time:.2f} seconds")
