from itertools import cycle
import os
import random
import re
import json
from queue import Queue
from threading import Thread
import time

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from io import StringIO, BytesIO
from azure.storage.blob import BlobServiceClient
# from perplexity import Perplexity
import google.generativeai as genai
from logger_functionality import logger


load_dotenv()


AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)


API_KEYS = [
    os.getenv("GEMINI_API_KEY4"),
]
api_key_cycle = cycle(API_KEYS)
current_api_key = next(api_key_cycle)

gemini_models = ["gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.0-flash-lite"]
model_cycle = cycle(gemini_models)
current_model = next(model_cycle)

def configure_gemini(api_key: str):
    """Configure Gemini with the given API key."""
    genai.configure(api_key=api_key)
    logger.info(f"Configured Gemini with API key ending in {api_key[-4:]}")

configure_gemini(current_api_key)

def call_gemini_chat(prompt_text, max_attempts: int = 1):
    global current_api_key, current_model

    for attempt in range(max_attempts):
        try:
            model = genai.GenerativeModel(current_model)
            resp = model.generate_content(prompt_text, generation_config={"temperature": 0.0})
            return getattr(resp, "text", str(resp))

        except Exception as e:
            error_msg = str(e).lower()

            if "quota" in error_msg or "429" in error_msg or "exceeded" in error_msg:
                logger.warning(f"Quota exceeded for key ending in {current_api_key[-4:]}. Switching to next key...")
                current_api_key = next(api_key_cycle)
                configure_gemini(current_api_key)
                time.sleep(2)

            else:
                logger.error(f"Unexpected error: {e}")
                raise e

    raise RuntimeError("All Gemini API keys/models exhausted after retries.")


def _extract_json_from_text(s)->dict|None:
    if not s:
        return None
    m = re.search(r'\{[\s\S]*\}', s)
    if not m:
        return None
    blob = m.group(0)
    blob = re.sub(r',\s*}', '}', blob)
    blob = re.sub(r',\s*\]', ']', blob)
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


PROMPT = """You are a Regulatory/Clinical Data Analyst with 10+ years of experience in medical devices, orthopaedics, and clinical data. 
Your task is to **analyze product/device descriptions** and **accurately extract the following information**: 

🎯 TARGET FIELDS TO EXTRACT
1. Bone
2. Bone Type
3. Is Lower Limb (Yes/No)

📌 INPUTS
- Device Description: text describing the device, surgical use, or implant. 
- Brand Name: may include hints like "upper limb", "lower limb", "wrist", etc. 
- GMDN PT Definition: standard device definition from GMDN. 
- FDA Product Code Name: official FDA code name related to the device.

---

📌 TASK INSTRUCTIONS
1. Carefully read **all four inputs**. Use **any relevant clues** from the Brand Name, GMDN PT Definition, and FDA Product Code to support extraction if the Device Description alone is ambiguous.
2. Identify if the device is associated with a specific bone or anatomical region.
3. Map the bone/anatomical region to its **Bone Type** (e.g., Ulna, Radius, Tibia, Femur, Craniofacial, Spine, Clavicle, Sternum, etc.).
4. Determine whether the bone/bone type belongs to the **lower limb**:
   - Lower limb bones include: Tibia, Fibula, Femur, Patella, Talus, Calcaneus, Mid-foot, etc.
   - Upper limb or craniofacial/spinal/other bones → mark **No**.
5. If the device is **non-bone-specific** (e.g., tray, container, general surgical tool) → Bone and Bone Type = "", Is Lower Limb = "".
6. If multiple bones are mentioned (e.g., Tibia-Talus) → include all in Bone field, and evaluate lower limb accordingly.
7. Use **exact anatomical rules and keywords** for mapping:
   - Volar/Dorsal → forearm/wrist (Radius/Ulna), upper limb
   - Olecranon → Ulna, upper limb
   - Craniofacial → skull/face, not lower limb
   - Spine → cervical/thoracic/lumbar/sacral/coccyx, not lower limb
   - Clavicle → Clavicle, upper limb
   - Sternum → Sternum, not lower limb
   - Tibia/Femur/Fibula/Patella/Talus/Calcaneus → lower limb
   - Mid-foot → lower limb
8. Always provide a clear, concise output in the following format:
    {
        "bone":"<bone_name(s)>",
        "bone_type": "<bone_type(s)>",
        "is_lower_limb":"<Yes/No>",
    }
9. Avoid assumptions; only extract **based on the device description** and the rules above.
10. When in doubt, default to **None** rather than guessing.
"""


def process_file(input_path:str, output_path:str):
    logger.info(f"Processing: {input_path}")

    try:
        df = pd.read_excel(input_path)
    except Exception as e:
        df = pd.read_csv(input_path)
    
    parsed_rows = []
    for _, row in df.iterrows():
        distribution_satus = str(row.get("Commercial Distribution Status", "")).strip()

        if distribution_satus == "In Commercial Distribution":
            brand_name = str(row.get("Brand Name", "")).strip()
            gmdn_pt_definition = str(row.get("GMDN PT Definition", "")).strip()
            fda_product_code_name = str(row.get("FDA Product Code Name", "")).strip()
            desc = str(row.get("Device Description", "")).strip()
            print(":: desc ::", desc)
            prompt = PROMPT + "\n\nNow Use following Inputs and return a single JSON object. Use empty string \"\" for fields that cannot be determined.\n\n-Device Description: " + desc +"\n- Brand Name: " + brand_name + "\n- GMDN PT Definition: " + gmdn_pt_definition + "\n- FDA Product Code Name: " + fda_product_code_name

            print(":: Prompt ::\n",prompt)
            resp_text = call_gemini_chat(prompt)
            print(":: Res ::", resp_text)

            resp_json = _extract_json_from_text(resp_text)
            print(":: JSON ::", resp_json)
            
            is_lower_limb = str(resp_json.get("is_lower_limb", "")).strip().lower()
            parsed = {
                "bone" : resp_json.get("bone", ""),
                "out of scope": "No" if is_lower_limb in ["yes", ""] else "Yes"
            }

        else:
            parsed = {
                "out of scope" : "yes"
            }

        combined = {**row.to_dict(), **parsed}
        parsed_rows.append(combined)

    out_df = pd.DataFrame(parsed_rows)
    out_df.to_excel(output_path, index=False)
    print(f"✅ Saved parsed output to {output_path}")





if __name__ == "__main__":
    process_file(r"C:\Users\BitCoding Solutions\Downloads\HWC-Screw, fixation, bone-KEY SURGICAL, INC-202507-AI-Extracted.xlsx", r"D:\Mukund\Surgzon\data_extractor\qc_val-gemini-prompt.xlsx")
    # distribution_satus = "In Commercial Distribution"
    # if distribution_satus == "In Commercial Distribution":
    #     brand_name = "Accord"
    #     gmdn_pt_definition = "A non-bioabsorbable, non-customized, firm, implantable sheet intended to stabilize a fractured orthopaedic bone (excluding craniofacial and spinal) to treat a traumatic/pathological fracture, to fuse a joint (arthrodesis) and/or as part of an osteotomy. Typically attached to a bone of a limb, rib, sternum, or pelvis, it is designed to be fixed in place with screws, and may be used in connection with another fixation plate; it does not incorporate a sleeve or blade. Instruments intended to facilitate implantation, or fixation implants (i.e., bone screws), may be included with the plate."
    #     fda_product_code_name = "PLATE, FIXATION, BONE"
    #     desc = "ACCORD 250MM TITANIUM PLATE"
        
    #     prompt = PROMPT + "\n\nNow Use following Inputs and return a single JSON object. Use empty string \"\" for fields that cannot be determined.\n\n-Device Description: " + desc +"\n- Brand Name: " + brand_name + "\n- GMDN PT Definition: " + gmdn_pt_definition + "\n- FDA Product Code Name: " + fda_product_code_name

    #     print(":: Prompt ::\n",prompt)
    #     resp_text = call_gemini_chat(prompt)
    #     print(":: Res ::", resp_text)

    #     resp_json = _extract_json_from_text(resp_text)
    #     print(":: JSON ::", resp_json)
        