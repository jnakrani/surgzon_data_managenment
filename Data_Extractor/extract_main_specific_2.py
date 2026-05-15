from itertools import cycle
import os
import random
import re
import json
import time

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from io import StringIO, BytesIO
from azure.storage.blob import BlobServiceClient


load_dotenv()

# ---------------- Azure Setup ----------------
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)


# --- Load API key ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY environment variable before running.")
client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-4o-mini"
def call_openai_chat(prompt_text):
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a strict information extraction model. Always output valid JSON only."},
                {"role": "user", "content": prompt_text},
            ],
            temperature=0.0
        )
        return resp.choices[0].message.content
    except Exception as e:
        print("OpenAI API error:", e)
        return None

PARSED_FIELDS = [
    "diameter", "length", "height", "width", "thickness", "coated",
    "constrained", "material", "cannulated", "cancellous", "thread",
    "locking", "size", "compression", "shape", "loop", "bone", "side",
    "angle", "position", "offset", "sterile", "product", "headed", 
    "dimensions", "other", "color"
]

try:
    import google.generativeai as genai
except Exception:
    genai = None

if not genai:
    raise RuntimeError("google.generativeai not installed or importable in this environment.")
API_KEYS = [
    os.getenv("GEMINI_API_KEY_CLIENT"),
    os.getenv("GEMINI_API_KEY21"),
    os.getenv("GEMINI_API_KEY22"),
    os.getenv("GEMINI_API_KEY23"),
    os.getenv("GEMINI_API_KEY24"),
    os.getenv("GEMINI_API_KEY25"),
    os.getenv("GEMINI_API_KEY26"),
    os.getenv("GEMINI_API_KEY27"),
    os.getenv("GEMINI_API_KEY28"),
    os.getenv("GEMINI_API_KEY29"),
    os.getenv("GEMINI_API_KEY30"),
]

# Filter out None values
API_KEYS = [key for key in API_KEYS if key is not None]

if not API_KEYS:
    raise RuntimeError("No valid Gemini API keys found in environment variables.")

api_key_cycle = cycle(API_KEYS)
current_api_key = next(api_key_cycle)

gemini_models = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
model_cycle = cycle(gemini_models)
current_model = next(model_cycle)

def configure_gemini(api_key: str):
    """Configure Gemini with the given API key."""
    if not api_key:
        raise ValueError("API key cannot be None or empty")
    genai.configure(api_key=api_key)
    print(f"Configured Gemini with API key ending in {api_key[-4:]}")

# Initial configuration
configure_gemini(current_api_key)

def call_gemini_chat(prompt_text, max_attempts: int = 3):
    global current_api_key, current_model

    for attempt in range(max_attempts):
        try:
            model = genai.GenerativeModel(current_model)
            resp = model.generate_content(prompt_text, generation_config={"temperature": 0.0})
            return getattr(resp, "text", str(resp))

        except Exception as e:
            error_msg = str(e).lower()

            if "quota" in error_msg or "429" in error_msg or "exceeded" in error_msg or "api_key_invalid" in error_msg:
                print(f"Issue with key ending in {current_api_key[-4:]} (Model: {current_model}). Switching to next key and model...")
                current_api_key = next(api_key_cycle)
                current_model = next(model_cycle)
                configure_gemini(current_api_key)
                print(f"Switched to key ending in {current_api_key[-4:]} with model {current_model}")
                time.sleep(2)

            else:
                print(f"Unexpected error: {e}")
                if attempt == max_attempts - 1:
                    raise e

    raise RuntimeError("All Gemini API keys/models exhausted after retries.")

# ------------------------------------------------------------------
# PROMPT (exact block you provided — DO NOT CHANGE THIS BLOCK)
PROMPT_RULES = """
You are an AI data extraction expert. 
Your task is to extract structured fields from medical device text data. 
Your output must always match the defined rules and the logic implemented in rule-based extraction functions.
Your task is to extract the following fields from the given "Device Description" text.  
Always follow the exact rules given below.
---

🎯 TARGET FIELDS TO EXTRACT
company, product, length, diameter, height, coated, thickness, constrained, material,
cannulated, cancellous, thread, locking, size, compression, shape, loop, bone, side, angle,
position, offset, sterile, headed, dimensions, other, color

---

📌 EXTRACTION PRINCIPLES
- Apply REGEX-style rule logic for every field as described below.
- If a field does not match any rule → return an empty string "" (never guess).
- Do NOT try to infer or hallucinate any value.
- Extract only values present in the text exactly as per rule conditions.
- Return only one best value for each field.
- If multiple matches are present, take the first valid match.
- Output strictly as JSON object with all required keys.

---

📌 PRODUCT NAME MAPPING RULES
Always normalize abbreviations into their full product names:

COMP PLATE → compression plate  
FRAG SCRW → fragment screw  
FRAC PLT SCRW → fracture plate screw  
CONTURLK HTO PLT → contourlock high tibial osteotomy plate  
OSTEO SUPPORT PLT → osteotomy support plate  
PLT,OPENG WEDG OSTEO → opening wedge osteotomy plate  
PLT,LO-PRO / LPS → low profile plate  
LP SCREW / LO-PRO SCRW / LOW PROF SCRW → low profile screw  
L-PLATE → l-shape plate  
LO-PRO STR PLT → low profile straight plate  
LO-PRO MTP PLT → low profile metatarsophalangeal plate  
FIB PLT → fibula plate  
DBL COMP PLATES → double compression plate  
BTB → bone-tendon-bone  
TIB A/P SLPD OSTEO PLT → tibial osteotomy plate  
HTO IMPL,IBAL → iBalance high tibial osteotomy implant  
MTP PLT → metatarsophalangeal plate  
CONTURLK FEM OS-TEOTOMY PLT → contourlock femoral osteotomy plate  
HUM INSERT → humeral insert  
PLATE, POW, LOCKING → proximal opening wedge "pow" plate  
T-ROPE SYNDESMO BUTTRESS PLATE → tightrope syndesmosis buttress plate  

If no mapping matches, take the product name as it appears (full name) from the device description.  
Never return short forms if the full form is already given.

---

📌 FIELD-SPECIFIC EXTRACTION RULES
🔹 Length 
Extract diameter and length based on the following rules:
1. Dimension Pattern (D × LMM — exactly two numbers):
    - Match only <number> × <number>MM (or "x").
    - Extract the second number as Length.
    - Examples:
        - "6.7 × 95MM" → Length = 95
        - "6.0MM x 60MM" → Length = 60
    - Ignore if there are three numbers (e.g., "17x34x12MM").
    - Ignore if the text contains the word "LOOP" (e.g., "15MM X 40MM LOOP").
2. Plus Pattern (D + HMM)
    - Do not extract Length from this pattern.
    - Example: "42+12MM" → Length = None.
3. Single Number with PLT/PLATE
    - If only one number appears with PLT/PLATE → treat as Length.
    - Example: "PLT 8MM" → Length = 8.
    - Exception:
        - If "STEP" → treat number as Height, not Length.
        - If "LOOP" → treat number as loop, not Length.
4. Ignore SIZE Values
    - If a number appears with/after "SIZE", ignore it.
    - Example: "SIZE 14" → Length = None.
5. Single Number (no PLT/PLATE)
    - Only treat as Length if context indicates linear component, e.g.: "BAR", "ROD", "RODS", "ROD BAR", "CLAMP PIN TO ROD" etc.
    - Otherwise, treat as Diameter (see Diameter rules).
    - Example: "39" → Diameter = 39.
6. Inches with Optional cm Conversion
    - If the format matches:
        - "<number> Inch(es)"
        - or "<number> Inches (<number>cm)"
    - Extract the first number (inches) as Length.
    - Example:
        - "36 Inches (91cm)" → Length = 36
        - "24 Inch" → Length = 24
7. Rod/Wire/Needle Pattern (two separate MM/CM/Inch(es) values, no "×")
    - If two numbers in MM/CM/Inch(es) appear without an × or +:
        - The first number (usually smaller, next to material name) → Diameter.
        - The second number (usually larger, trailing at end) → Length.
    - Example:
        - "11.0MM CARBON FIBER ROD 450MM" → Diameter = 11.0, Length = 450

🔹 Diameter 
1. Dimension Pattern (D × LMM — exactly two numbers)
    - xtract the first number as Diameter.
    - Example: "6.7 × 95MM" → Diameter = 6.7.
    - Ignore if there are three numbers (e.g., "17x34x12MM").
2. Plus Pattern (D + HMM)
    - Extract the first number as Diameter.
    - Example: "42+12MM" → Diameter = 42.
3. Dual Measurement / Range Pattern
    - If text is <number>/<number>MM or <number>/+, treat entire value as Diameter.
    - Example: "2.7/3.5MM" → Diameter = "2.7/3.5".
4. Single Number (no PLT/PLATE)
    - Only treat as Diameter if context does NOT indicate length (e.g., not "BAR", "ROD", "RODS", "CLAMP", etc.).
    - Any number immediately preceded by # is not a diameter (e.g., #14 → ignore).
    - Example: "39" → Diameter = 39.
5. Ignore SIZE Values
    - Example: "SIZE 14" → Diameter = None.
6. Ignore Hole/Plate Counts
    - If the number appears before words like “HOLE”, “HOLES”, do not treat it as a diameter.
    - Example:
        - "4 HOLES COMPRESSION PLATE T SHAPED" → Diameter = None
7. Ignore Catalog/Item Numbers
    - Any long numeric sequence (usually ≥5 digits) without units (no MM, CM, IN, etc.) and appearing before or inside the device name.
    - Example:
        - "SCREW 123456 FULL THREAD 50MM" → 123456 → Ignore

🔹 Height  
1. Three-number Dimension (A × B × CMM)
    - Extract the first number only as Height.
    - Example: "17x34x12MM" → Height = 17..
2. Plus Pattern (A + BMM)/(A + B)
    - Extract the second number (after "+") as Height (include "+" sign).
    - Example: "42+15MM" → Height = "+15".
    - Exclude if text contains "INF", "LAT", "OFFSET", or "TO FIT IN".
    - Ensures that Thickness or Offset is not double-counted.
3. Single Number with STEP
    - If only one number with STEP, treat it as Height.
    - Example: "7MM STEP" → Height = 7.


🔹 Width 
- pattern: - Pattern: `17x34x12mm` → length = 12mm, width = 34mm, height = 17mm
- In this pattern middle number is treated as width. do not consider any other value for width.
- Example: (13x40x13mm) → width = 40, (08x28x11mm) → width = 28, (07x34x12mm) → width = 34.
- If only two values like `15x52mm` then do not consider any number as width.

🔹 Coated  
- CAP CTD / CAP COATED → Cap Coated  
- CTD → Coated

🔹 Thickness
1. Tibial Insert / Trial Pattern:
    - If a number is immediately followed by the letter "T" (e.g., 10T, 12T, 14T), interpret it as Thickness in millimeters.
    - Example: "10T" → Thickness = 10
    - Ignore if the T is part of a larger alphanumeric code (e.g., "T123", "TX10").
2. "TO FIT IN +<number>" Pattern:
    - If text contains "TO FIT IN" followed by "+<number>", extract that number as Thickness.
    - Example: "TO FIT IN +3" → Thickness = +3
    - Do not assign this same "+<number>" to Height or Offset fields.
3. General Rule:
    - Only extract Thickness when context clearly refers to insert, pad, or fitting dimensions (e.g., "INSERT", "SPACER", "TRIAL", "THICKNESS").
    - Avoid confusing it with length, height, or offset unless explicitly stated.

🔹 Constrained  
- CONST → Yes

🔹 Material  
- TI or TITANIUM → Titanium  
- SS → Stainless Steel

🔹 Cannulated  
- CANN → Cannulated

🔹 Cancellous  
- CANC → Cancellous  
- CORTICAL → Cortical  
- CORTEX → Cortex  
- NEAR CORTEX → Near Cortex

🔹 Thread  
- PT THD → Partially Threaded  
- FULLY THD/THRDED/THREADED → Fully Threaded  
- (number)MM THD → just the numeric value (e.g. "4" for "4MM THD")

🔹 Locking  
- LOCK or LOCKING → Yes

🔹 Size  
1. Hole Count Pattern
    - Match when a number is directly followed or preceded by “HOLE”, “HOLES”, or “H”.
    - Examples:
        - 6H, 10 HOLE, 08 Holes, 9 Hole
    - Convert format: → <number>-Hole
        - e.g., 6H → 6-Hole, 10 Holes → 10-Hole.
2. Explicit "SIZE" Keyword
    - Match when the word “SIZE” is followed by a number or short abbreviation.
    - Examples:
        - SIZE 14 → Size 14
        - SIZE M → Size Medium.
3. Recognized Size Abbreviations (with full expansion)
    - Map common shorthand notations to their full descriptive forms:
        - S → Small
        - M → Medium
        - L → Large
        - XL → X-Large
        - XXL → XX-Large
        - STD → Standard
        - LNG → Long
        - S/M → Small–Medium
        - M/L → Medium–Large
        - L/XL → Large–X-Large
    - Note:
        - Always expand the entire abbreviation.
        - Do not keep abbreviations in short form (e.g., “L/XL” → write “Large–X-Large”).
        - Always detect both sides of the slash (/) if present.
4. Valid Context Requirement
    - Only consider size values if they appear in a clear context (e.g., near “SIZE” or “HOLE”) or match the known abbreviations above.
    - Do not treat standalone numbers (e.g., 42, 39, 24) as size unless explicitly tied to:
        - a prefix like SIZE, or
        - a postfix like HOLE, HOLES, or H.
5. Invalid Cases
    - Ignore numbers related to length, diameter, angle, or catalog codes.
    - Ignore size-like tokens that appear as part of other descriptors (e.g., L-BEND, M-THREAD, S-SHAPE).

🔹 Compression  
- DBL → Double


🔹 Shape  
- SQUARE → Square  
- STR → Straight  
- HEXALOBE → Hexalobe  
- A/P SLPD → Antero-Posterior Sloped Wedge  
- META OPEN WDG → Metatarsal Opening Wedge  
- NAR → Narrow  
- WIDE → Wide  
- CONTRD → Contoured  
- 10MM WEDGE → 10 mm Wedge  
- CLOSING WEDG → Closing Wedge  
- OPENING WEDGE → Opening Wedge  
- FLAT → Flat


🔹 Loop 
- If text contains LOOP, extract the number directly before it (ignore if used in x-dimension).
- Examples:
    - "60MM LOOP" → Loop = 60
    - "LOOP 40" → Loop = 40
    - "15MM x 40MM LOOP" → Loop = 40


🔹 Bone
- If the text contains "CLAVICLE" or "CLAVICULAR", output → Clavicle
- If the text contains "HUMERAL" or "HUMERUS", output → Humerus
- If the text contains "TIBIAL" or "TIBIA", output → Tibia
- If the text contains "FEMORAL" or "FEMUR", output → Femur
- If the text contains "RADIUS" or "RADIAL", output → Radius
- If the text contains "ULNA" or "ULNAR", output → Ulna
- If the text contains "FIBULA" or "FIBULAR", output → Fibula
- If the text contains "TALUS" or "TALAR", output → Talus
- If the text contains "CALCANEUS" or "CALCANEAL", output → Calcaneus
- If the text contains "TT", output → Tibia - Talus
- If the text contains "TTC", output → Tibia - Talus - Calcaneus
- If the text contains "MIDFOOT", output → Mid-foot
- If the text contains "ANKLE" or "TIBIOTALAR", output → Ankle (Tibia - Talus)
- If the text contains "PELVIC" or "ACETABULAR", output → Pelvis / Acetabulum
- If the text contains "STERNAL" or "STERNUM", output → Sternum
- If the text contains "CRANIAL", "CRANIOFACIAL", "FACIAL", "MAXILLOFACIAL", "MANDIBLE", or "MANDIBULAR", output → Craniofacial / Mandible
- If the text contains "SCAPULA" or "SCAPULAR", output → Scapula
- If the text contains "PATELLA" or "PATELLAR", output → Patella
- If the text contains "METACARPAL" or "CARPAL", output → Hand / Wrist
- If the text contains "METATARSAL" or "TARSAL", output → Foot
- If the text contains "SPINE", "VERTEBRAL", "CERVICAL", "THORACIC", "LUMBAR", or "SACRAL", output → Spine
- If the text contains "RIB" or "COSTAL", output → Rib
- If the text contains "COXA" or "HIP", output → Hip
- If the text contains OLECRANON, CORONOID PROCESS, output → Ulna
- If the text contains TIBIAL PLATEAU, output → Tibia
- If the text contains DISTAL RADIUS, PROXIMAL RADIUS, output → Radius
- If the text contains DISTAL HUMERUS, PROXIMAL HUMERUS, output → Humerus
- If the text contains DISTAL FEMUR, PROXIMAL FEMUR, output → Femur
- If the text contains DISTAL TIBIA, PROXIMAL TIBIA, output → Tibia
- If multiple keywords match, choose the most specific anatomical region.
- If no bone keyword is found, output → None.

🔹 Side  
- RT / RGHT / R → Right  
- LT / LFT / L → Left

🔹 Angle  
- 14° → 14°  
- 15 DEG → 15°

🔹 Position  
- INF → Inferior  
- LAT → Lateral  
- ANTERIOR → Anterior  
- DISTAL → Distal  
- POSTERIOR → Posterior  
- ANTERI PROCESS → Anterior Process  
- ANT PROC/POST TUBER → Anterior Process – Posterior Tuberosity

🔹 Offset  
1. Plus Pattern with OFFSET/INF/LAT
    - If text contains "+<number>" and keywords "OFFSET", "INF", or "LAT" → extract this value as Offset.
    - Example: "39+12 OFFSET" → Offset = 12.
    - Do not assign the same "+<number>" to Height or Thickness.
2. Slash-Plus Pattern
    - Extract number after "+".
    - Example: "42/+6" → Offset = 6.
3. Ignore keyword-only mentions
    - If the text contains the word “OFFSET” but no numeric value is present with the + or /+ pattern, do not extract anything.
    - Example:
        - "Three Prong Right Offset Inserter (Sterile)" → Offset = None
        - "39+12 OFFSET" → Offset = 12 (still extracted as before)

🔹 Headed
- Headed present → Yes  
- Else → blank

🔹 Dimensions
- Always None

🔹 Other
- All non categorized strings put in this field.

🔹 Color
- write the name of color if any present.

---

📌 OUTPUT FORMAT

Return strictly in this structure:

{
 "product": "",
 "length": "",
 "diameter": "",
 "height": "",
 "width": "",
 "coated": "",
 "thickness": "",
 "constrained": "",
 "material": "",
 "cannulated": "",
 "cancellous": "",
 "thread": "",
 "locking": "",
 "size": "",
 "compression": "",
 "shape": "",
 "loop": "",
 "bone": "",
 "side": "",
 "angle": "",
 "position": "",
 "offset": "",
 "headed": "",
 "dimensions": "",
 "other": "",
 "color": ""
}

---

⚠️ Important:
- If a field is not found, leave it as an empty string.
- Never guess values — only extract if explicitly present.
- Follow the normalization rules exactly as defined.
"""


# The EXACT output fields you requested:
OUTPUT_FIELDS = [
    "company","product","length","diameter","height","width", "coated",
    "thickness","constrained", "material", "cannulated","cancellous","thread","locking",
    "size","compression","shape","loop","bone","side","angle","position","offset","sterile",
    "headed", "dimensions", "other", "color"
]

# Helper: small rule-based fallback/normalization (keeps your mappings)
PRODUCT_MAP = {
    "COMP PLATE":"compression plate",
    "FRAG SCRW":"fragment screw",
    "FRAC PLT SCRW":"fracture plate screw",
    "CONTURLK HTO PLT":"countourlock high tibial osteotomy plate",
    "OSTEO SUPPORT PLT":"Osteotomy Support Plate",
    "PLT,OPENG WEDG OSTEO":"opening wedge osteotomy plate",
    "PLT,LO-PRO":"low profile plate",
    "LPS":"low profile plate",
    "LP SCREW":"low profile screw",
    "LO-PRO SCRW":"low profile screw",
    "LOW PROF SCRW":"low profile screw",
    "L-PLATE":"l-shape plate",
    "LO-PRO STR PLT":"low profile straight plate",
    "LO-PRO MTP PLT":"low profile metatarsophalangeal plate",
    "FIB PLT":"fibula plate",
    "DBL COMP PLATES":"double compression plate",
    "BTB":"bone-tendon-bone",
    "TIB A/P SLPD OSTEO PLT":"tibial osteotomy plate",
    "HTO IMPL,IBAL":"iBalance high tibial ostetomy implant",
    "MTP PLT":"metatarsophalangeal plate",
    "CONTURLK FEM OS-TEOTOMY PLT":"contourlock femoral osteotomy plate",
    "HUM INSERT":"humerla insert",
    "PLATE, POW, LOCKING":"proximal opening wedge \"pow\" plate",
    "T-ROPE SYNDESMO BUTTRESS PLATE":"tightrope syndesmosis buttress plate",
    "UNIVERS REVERS SPACER":"univers revers spacer",
    "UNIVERS REVERS GLENO":"univers revers gleno", 
    "UNIVERS REVS CUP":"univers revers suture cup",
    "UNIVERS REVERS STEM":"univers revers stem",
    "UNIVERSAL GLENOID - CENTRAL SCREW":"universal glenoid central screw",
    "HUMERAL INSERT": "humerla insert"
}

# Rule-based extraction helpers (used if model fails or for normalization)
#---------------------------------------------------
def rb_extract_diameter(text: str):
    text_upper = text.upper().strip()

    if re.search(r'\bSIZE\s*\d+', text_upper):
        return None

    if re.search(r'\b\d{5,}\b(?!\s*(MM|CM|IN))', text_upper):
        return None

    if re.search(r'\b\d+(?:\.\d+)?(?:\s*|\-)*(?:HOLE|HOLES|PLATE|PLATES|DEGREE)\b', text_upper):
        return None

    if re.search(r'#\d+', text_upper):
        return None

    m = re.search(r'(\d+(?:\.\d+)?\s*/\s*(?:\d+(?:\.\d+)?|\+))\s*MM', text_upper)
    if m:
        return m.group(1).replace(" ", "")

    m = re.search(r'(\d+(?:\.\d+)?)\s*\+\s*\d+(?:\.\d+)?\s*MM', text_upper)
    if m:
        return m.group(1)

    if re.search(r'\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?', text_upper):
        pass
    else:
        m = re.search(r'(\d+(?:\.\d+)?)(?:\s*MM)?\s*[x×]\s*(\d+(?:\.\d+)?)(?:\s*MM)?', text_upper)
        if m:
            return m.group(1)

    if not re.search(r'\b(PLT|PLATE)\b', text_upper):
        nums = re.findall(r'\b\d+(?:\.\d+)?\b', text_upper)
        if len(nums) == 1:
            quantity_keywords = ["EACH", "PCS", "SET", "POSITION"]
            if any(k in text_upper for k in quantity_keywords):
                return None
            return nums[0]


    return None


def rb_extract_length(text: str):
    text_upper = text.upper().strip()

    if re.search(r'\bSIZE\s*\d+', text_upper):
        return None

    if re.search(r'\d+(?:\.\d+)?\s*\+\s*\d+(?:\.\d+)?\s*MM', text_upper):
        return None
    
    if re.search(r'\d+(?:\.\d+)?\s*MM?\s*(TO|–|-)\s*\d+(?:\.\d+)?\s*MM', text_upper):
        return None

    if "LOOP" not in text_upper and not re.search(r'\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?', text_upper):
        m = re.search(r'(\d+(?:\.\d+)?)(?:MM)?\s*[x×]\s*(\d+(?:\.\d+)?)(?:MM)?', text_upper)
        if m:
            return m.group(2)

    if any(k in text_upper for k in ["PLT", "PLATE"]) and "STEP" not in text_upper and "LOOP" not in text_upper:
        m = re.search(r'(\d+(?:\.\d+)?)\s*MM', text_upper)
        if m:
            return m.group(1)

    m_inch = re.search(r'(\d+(?:\.\d+)?)\s*INCH(?:ES)?(?:\s*\(\s*\d+(?:\.\d+)?\s*CM\s*\))?', text_upper)
    if m_inch:
        return m_inch.group(1)

    if not re.search(r'[×x+]', text_upper):
        m = re.findall(r'(\d+(?:\.\d+)?)(?:\s*(MM|CM|INCH(?:ES)?))', text_upper)
        if len(m) >= 2:
            return m[1][0]

    return None


def rb_extract_height(text: str):
    text_upper = text.upper()

    # Rule 1: Three-number pattern (A x B x CMM) → Height = first number
    m1 = re.search(r'(\d+(?:\.\d+)?)\s*[x×]\s*\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?\s*MM', text_upper)
    if m1:
        return m1.group(1)

    # Rule 2: Plus pattern (A + BMM) → Height = second number with "+" sign
    if not any(keyword in text_upper for keyword in ["INF", "LAT", "OFFSET", "TO FIT IN"]):
        m2 = re.search(r'\d+(?:\.\d+)?\s*(\+\s*\d+(?:\.\d+)?)\s*MM', text_upper)
        if m2:
            return m2.group(1).replace(" ", "")  # remove any spaces around '+'

    # Rule 3: Single number with STEP → Height = that number
    m3 = re.search(r'(\d+(?:\.\d+)?)\s*MM\s*STEP', text_upper)
    if m3:
        return m3.group(1)

    return None


def rb_extract_width(text: str):
    text = text.upper()
    # Match patterns like 17x34x12MM → width = middle number
    m = re.search(r'(\d+(?:\.\d+)?)\s*[X×]\s*(\d+(?:\.\d+)?)\s*[X×]\s*(\d+(?:\.\d+)?)\s*MM', text)
    if m:
        return m.group(2)  # middle number is width
    return None


def rb_coated(text):
    if re.search(r'\bCAP CTD\b', text) or re.search(r'\bCAP COATED\b', text):
        return "Cap Coated"
    if re.search(r'\bCTD\b', text):
        return "Coated"
    return None


def rb_thickness(text):
    """
    Extracts thickness values like +3, +6 (without MM) only if text contains "TO FIT IN".
    """
    text_upper = text.upper()

    # Only proceed if "TO FIT IN" is present
    if "TO FIT IN" in text_upper:
        # Match +<number> not followed by MM
        m = re.search(r'(\+\d+(?:\.\d+)?)(?!\s*MM)', text_upper)
        if m:
            return m.group(1)

    return None


def rb_constrained(text):
    return "Yes" if re.search(r'\bCONST\b', text) else None


def rb_material(text):
    if re.search(r'\bTI\b', text) or re.search(r'\bTITANIUM\b', text):
        return "Titanium"
    if re.search(r'\bSS\b', text):
        return "Stainless Steel"
    return None


def rb_cannulated(text):
    return "cannulated" if re.search(r'\bCANN\b', text) else None


def rb_cancellous(text):
    if re.search(r'\bCANC\b', text): return "Cancellous"
    if re.search(r'\bCORTICAL\b', text): return "Cortical"
    if re.search(r'\bCORTEX\b', text): return "Cortex"
    if re.search(r'\bNEAR CORTEX\b', text): return "Near Cortex"
    
    return None

#---------------------------------------------------
def rb_thread(text):
    text = text.upper() 
    if re.search(r'PT\s*THD', text):
        return "Partially Threaded"
    if re.search(r'FULLY\s*(?:THD|THRDED|THREADED)', text):
        return "Fully Threaded"
    m = re.search(r'(\d+(?:\.\d+)?)\s*MM\s*THD', text)
    if m:
        return m.group(1)
    return None


def rb_locking(text):
    return "Yes" if re.search(r'\bLOCK\b', text) or re.search(r'LOCKING', text) else None


def rb_size(text):
    m = re.search(r'(\d+)\s*HOLE', text)
    if m: return f"{m.group(1)}-Hole"
    if re.search(r'\bS\b', text): return "Small"
    if re.search(r'\bM\b', text): return "Medium"
    if re.search(r'\bL\b', text): return "Large"
    if re.search(r'\bS/M\b', text): return "Small–Medium"
    if re.search(r'\bL/XL\b', text): return "Large–X-Large"
    if re.search(r'\b6H\b', text): return "6-Hole"
    if re.search(r'\bSTD\b', text): return "Standard"
    if re.search(r'\bLNG\b', text): return "Long"
    if re.search(r'\bLong\b', text): return "Long"
    m2 = re.search(r'SIZE\s*(\d+)', text)
    if m2: return "Size " + m2.group(1)
    return None


def rb_compression(text):
    return "Double" if re.search(r'\bDBL\b', text) else None

#---------------------------------------------------
def rb_shape(text):
    shapes = {
        "SQUARE":"Square","STR":"Straight","HEXALOBE":"Hexalobe","A/P SLPD":"Antero-Posterior Sloped Wedge",
        "META OPEN WDG":"Metatarsal Opening Wedge","NAR":"Narrow","WIDE":"Wide","CONTRD":"Contoured","10MM WEDGE":"10 mm Wedge",
        "CLOSING WEDG": "Closing Wedge", "OPENING WEDGE": "Opening Wedge", "FLAT": "Flat"
    }
    for k,v in shapes.items():
        if re.search(re.escape(k), text):
            return v
    return None


def rb_loop(text):
    m = re.search(r'LOOP[\s:-]*?(\d+)', text)
    if m:
        return m.group(1)
    # sometimes "LOOP 40" or "40 LOOP"
    m2 = re.search(r'(\d+)\s*LOOP', text)
    if m2:
        return m2.group(1)
    return None

#---------------------------------------------------
def rb_bone(text):
    if re.search(r'HUMERAL', text): return "Humerus"
    if re.search(r'TIBIAL', text): return "Tibia"
    if re.search(r'FEMORAL', text): return "Femur"
    if re.search(r'RADIUS', text): return "Radius"
    if re.search(r'CALCANEUS', text): return "calcanues"
    if re.search(r'TTC', text): return "tibia - talus - calcaneus"
    if re.search(r'TT', text): return "tibia - talus"
    if re.search(r'MIDFOOT', text): return "mid-foot"
    return None

#---------------------------------------------------
def rb_side(text):
    if re.search(r'\bRT\b', text): return "Right"
    if re.search(r'\bRGHT\b', text): return "Right"
    if re.search(r'\bR\b', text): return "Right"
    if re.search(r'\bLT\b', text): return "Left"
    if re.search(r'\bLFT\b', text): return "Left"
    if re.search(r'\bL\b', text): return "Left"
    return None


def rb_angle(text):
    t = text.upper()  # make it case-insensitive
    m = re.search(r'(\d+)\s*°', t)
    if not m:
        m = re.search(r'(\d+)\s*DEG', t)
    if not m:
        m = re.search(r'(\d+)\s*LOR', t)
    if m:
        return m.group(1) + "°"
    return None

#----------------------------------------------------
def rb_position(text):
    if re.search(r'\bLAT\b', text): return "lateral"
    if re.search(r'\bINF\b', text): return "Inferior"
    if re.search(r'\bANTERIOR\b', text): return "anterior"
    if re.search(r'\bDISTAL\b', text): return "distal"
    if re.search(r'\bPOSTERIOR\b', text): return "posterior"
    if re.search(r'\bANTERI PROCESS\b', text): return "anterior process"
    if re.search(r'\bANT PROC/POST TUBER\b', text): return "anterior process - posterior tuberosity"
    return None

#---------------------------------------------------
def rb_headed(text: str):
    """
    Detect if the product is 'Headed'.
    """
    if re.search(r'\bHEADED\b', text.upper()):
        return "Yes"
    return None
 
 
def rb_color(text: str):
    """
    Extracts any explicit color mention.
    """
    colors = [
        "BLUE", "BLACK", "GREEN", "RED", "YELLOW", "WHITE",
        "SILVER", "GOLD", "GREY", "GRAY", "ORANGE", "PURPLE",
        "BROWN", "PINK"
    ]
    text_upper = text.upper()
    for c in colors:
        if c in text_upper:
            return c.capitalize()
    return None
 
 
def rb_other(text: str, extracted_fields: dict):
    """
    Catch-all extractor:
    - Anything not captured by defined fields goes here.
    - Remove already extracted field values.
    """
    clean_text = text
    for v in extracted_fields.values():
        if v and isinstance(v, str):
            clean_text = clean_text.replace(v, "", 1)
 
    # If text left after cleaning is still meaningful
    clean_text = clean_text.strip(",;:.- ").strip()
    return clean_text if clean_text else None


def rb_offset(text: str):
    text_upper = text.upper()

    # Rule 1: Plus pattern with OFFSET/INF/LAT
    if any(keyword in text_upper for keyword in ["OFFSET", "INF", "LAT"]):
        m1 = re.search(r'\+\s*(\d+(?:\.\d+)?)', text_upper)
        if m1:
            return m1.group(1)  # only the number, no '+' sign

    # Rule 2: Slash-Plus pattern (e.g., 42/+6)
    m2 = re.search(r'/\+\s*(\d+(?:\.\d+)?)', text_upper)
    if m2:
        return m2.group(1)  # only the number

    return None


def rb_sterile(text):
    return "Yes" if re.search(r'\bSTERILE\b', text) else "No"

#---------------------------------------------------
def rule_based_parse(text: str) -> dict:
    """Extract all OUTPUT_FIELDS using regex/rule-based logic as fallback."""
    t = text.upper()
    out = {f: "" for f in OUTPUT_FIELDS}

    out["diameter"]      = rb_extract_diameter(t) or ""
    out["length"]        = rb_extract_length(t) or ""
    out["height"]        = rb_extract_height(t) or ""
    out["width"]         = rb_extract_width(t) or ""
    out["thickness"]     = rb_thickness(t) or ""
    out["coated"]        = rb_coated(t) or ""
    out["constrained"]   = rb_constrained(t) or ""
    out["material"]      = rb_material(t) or ""
    out["cannulated"]    = rb_cannulated(t) or ""
    out["cancellous"]    = rb_cancellous(t) or ""
    out["thread"]        = rb_thread(t) or ""
    out["locking"]       = rb_locking(t) or ""
    out["size"]          = rb_size(t) or ""
    out["compression"]   = rb_compression(t) or ""
    out["shape"]         = rb_shape(t) or ""
    out["loop"]          = rb_loop(t) or ""
    out["bone"]          = rb_bone(t) or ""
    out["side"]          = rb_side(t) or ""
    out["angle"]         = rb_angle(t) or ""
    out["position"]      = rb_position(t) or ""
    out["offset"]        = rb_offset(t) or ""
    out["sterile"]       = rb_sterile(t) or ""
    out["other"]         = rb_other(t) or ""
    out["headed"]        = rb_headed(t) or ""
    out["dimensions"]    = ""
    out["color"]         = rb_color(t) or ""

    # Try to map product name from PRODUCT_MAP
    for k,v in PRODUCT_MAP.items():
        if k in t:
            out["product"] = v
            break

    # Company and warranty usually not present in text, leave blank
    out["company"] = ""

    return out

# Utility: find first JSON blob inside text
def extract_json_from_text(s):
    if not s:
        return None
    m = re.search(r'\{[\s\S]*\}', s)
    if not m:
        return None
    blob = m.group(0)
    # quick cleaning of trailing commas
    blob = re.sub(r',\s*}', '}', blob)
    blob = re.sub(r',\s*\]', ']', blob)
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def process_excel(input_path, output_path, max_rows=None):
    try:
        df = pd.read_excel(input_path)
    except Exception as e:
        df = pd.read_csv(input_path)

    parsed_rows = []

    for i, row in df.iterrows():
        if max_rows and i >= max_rows:
            break

        desc = str(row.get("Device Description", "")).strip()
        print(":: desc ::", desc)
        if not desc:
            continue

        # Step 1: LLM Extraction
        prompt = PROMPT_RULES + "\n\nNow parse the following Device Description using ONLY the rules above and return a single JSON object with these exact keys: " + ", ".join(OUTPUT_FIELDS) + ". Use empty string \"\" for fields that cannot be determined.\n\nDevice Description:\n" + desc
        resp_text = call_gemini_chat(prompt)
        # resp_text = call_openai_chat(prompt)
        parsed_json = extract_json_from_text(resp_text or "")

        # Step 2A: Fallback if LLM fails completely
        if not parsed_json:
            parsed = rule_based_parse(desc)
        else:
            # Step 2B: Normalize
            normalized = {f: "" for f in OUTPUT_FIELDS}
            for k, v in parsed_json.items():
                if k.lower() in [x.lower() for x in OUTPUT_FIELDS]:
                    normalized[k.lower()] = str(v).strip()

            # Step 2C: Fill missing fields using rule-based functions
            text_up = desc.upper()
            if not normalized.get("diameter"):      normalized["diameter"]    = rb_extract_diameter(text_up) or ""
            if not normalized.get("length"):        normalized["length"]      = rb_extract_length(text_up) or ""
            if not normalized.get("height"):        normalized["height"]      = rb_extract_height(text_up) or ""
            if not normalized.get("width"):         normalized["width"]       = rb_extract_width(text_up) or ""
            if not normalized.get("thickness"):     normalized["thickness"]   = rb_thickness(text_up) or ""
            if not normalized.get("coated"):        normalized["coated"]      = rb_coated(text_up) or ""
            if not normalized.get("constrained"):   normalized["constrained"] = rb_constrained(text_up) or ""
            if not normalized.get("material"):      normalized["material"]    = rb_material(text_up) or ""
            if not normalized.get("cannulated"):    normalized["cannulated"]  = rb_cannulated(text_up) or ""
            if not normalized.get("cancellous"):    normalized["cancellous"]  = rb_cancellous(text_up) or ""
            if not normalized.get("thread"):        normalized["thread"]      = rb_thread(text_up) or ""
            if not normalized.get("locking"):       normalized["locking"]     = rb_locking(text_up) or ""
            if not normalized.get("size"):          normalized["size"]        = rb_size(text_up) or ""
            if not normalized.get("compression"):   normalized["compression"] = rb_compression(text_up) or ""
            if not normalized.get("shape"):         normalized["shape"]       = rb_shape(text_up) or ""
            if not normalized.get("loop"):          normalized["loop"]        = rb_loop(text_up) or ""
            if not normalized.get("bone"):          normalized["bone"]        = rb_bone(text_up) or ""
            if not normalized.get("side"):          normalized["side"]        = rb_side(text_up) or ""
            if not normalized.get("angle"):         normalized["angle"]       = rb_angle(text_up) or ""
            if not normalized.get("position"):      normalized["position"]    = rb_position(text_up) or ""
            if not normalized.get("offset"):        normalized["offset"]      = rb_offset(text_up) or ""
            if not normalized.get("sterile"):       normalized["sterile"]     = rb_sterile(text_up) or ""
            if not normalized.get("headed"):        normalized["headed"]      = rb_headed(text_up) or ""
            if not normalized.get("dimensions"):    normalized["dimensions"]  = ""
            if not normalized.get("color"):         normalized["color"]       = rb_color(text_up) or ""
            if not normalized.get("other"):         normalized["other"]       = rb_other(desc, normalized)
            
            # Fill product using PRODUCT_MAP if empty
            if not normalized.get("product"):
                for k,v in PRODUCT_MAP.items():
                    if k in text_up:
                        normalized["product"] = v
                        break

            parsed = normalized
        
        combined = {**row.to_dict(), **parsed}
        parsed_rows.append(combined)

        sleep_time = random.uniform(10, 20)
        print(f"      😴 Sleeping {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)

    # Write output
    out_df = pd.DataFrame(parsed_rows)
    out_df.to_excel(output_path, index=False)
    print(f"✅ Saved parsed output to {output_path}")


def process_stream_excel(input_stream, output_stream, max_rows=None):
    """
    Process an Excel file in memory.
    - input_stream: BytesIO containing Excel file
    - output_stream: BytesIO to write processed Excel
    """

    global current_model, model_cycle
    df = pd.read_excel(input_stream)
    parsed_rows = []

    for field in OUTPUT_FIELDS:
        if field not in df.columns:
            df[field] = ""

    for i, row in df.iterrows():

        if max_rows and i >= max_rows:
            break
        
        already_processed = any(
            str(row.get(field, "")).strip() != "" for field in OUTPUT_FIELDS
        )
        if already_processed:
            parsed_rows.append(row.to_dict())  # keep as-is
            continue

        desc = str(row.get("Device Description", "")).strip()
        if not desc:
            continue

        # Step 1: LLM Extraction
        prompt = PROMPT_RULES + "\n\nNow parse the following Device Description using ONLY the rules above and return a single JSON object with these exact keys: " + ", ".join(OUTPUT_FIELDS) + ". Use empty string \"\" for fields that cannot be determined.\n\nDevice Description:\n" + desc
        retries = 0
        while retries < 5:
            try:
                resp_text = call_gemini_chat(prompt)
                break
            except Exception as e:
                retries += 1
                current_model = next(model_cycle)
                print(f"⚠️ API error: {e}. Waiting 30 seconds before retrying with {current_model} model")
                time.sleep(30)
        parsed_json = extract_json_from_text(resp_text or "")

        # Step 2A: Fallback if LLM fails completely
        if not parsed_json:
            parsed = rule_based_parse(desc)
        else:
            # Step 2B: Normalize
            normalized = {f: "" for f in OUTPUT_FIELDS}
            for k, v in parsed_json.items():
                if k.lower() in [x.lower() for x in OUTPUT_FIELDS]:
                    normalized[k.lower()] = str(v).strip()

            # Step 2C: Fill missing fields (rule-based)
            text_up = desc.upper()
            if not normalized.get("diameter"):      normalized["diameter"]    = rb_extract_diameter(text_up) or ""
            if not normalized.get("length"):        normalized["length"]      = rb_extract_length(text_up) or ""
            if not normalized.get("height"):        normalized["height"]      = rb_extract_height(text_up) or ""
            if not normalized.get("width"):         normalized["width"]       = rb_extract_width(text_up) or ""
            if not normalized.get("thickness"):     normalized["thickness"]   = rb_thickness(text_up) or ""
            if not normalized.get("coated"):        normalized["coated"]      = rb_coated(text_up) or ""
            if not normalized.get("constrained"):   normalized["constrained"] = rb_constrained(text_up) or ""
            if not normalized.get("material"):      normalized["material"]    = rb_material(text_up) or ""
            if not normalized.get("cannulated"):    normalized["cannulated"]  = rb_cannulated(text_up) or ""
            if not normalized.get("cancellous"):    normalized["cancellous"]  = rb_cancellous(text_up) or ""
            if not normalized.get("thread"):        normalized["thread"]      = rb_thread(text_up) or ""
            if not normalized.get("locking"):       normalized["locking"]     = rb_locking(text_up) or ""
            if not normalized.get("size"):          normalized["size"]        = rb_size(text_up) or ""
            if not normalized.get("compression"):   normalized["compression"] = rb_compression(text_up) or ""
            if not normalized.get("shape"):         normalized["shape"]       = rb_shape(text_up) or ""
            if not normalized.get("loop"):          normalized["loop"]        = rb_loop(text_up) or ""
            if not normalized.get("bone"):          normalized["bone"]        = rb_bone(text_up) or ""
            if not normalized.get("side"):          normalized["side"]        = rb_side(text_up) or ""
            if not normalized.get("angle"):         normalized["angle"]       = rb_angle(text_up) or ""
            if not normalized.get("position"):      normalized["position"]    = rb_position(text_up) or ""
            if not normalized.get("offset"):        normalized["offset"]      = rb_offset(text_up) or ""
            if not normalized.get("sterile"):       normalized["sterile"]     = rb_sterile(text_up) or ""
            if not normalized.get("headed"):        normalized["headed"]      = rb_headed(text_up) or ""
            if not normalized.get("dimensions"):    normalized["dimensions"]  = ""
            if not normalized.get("color"):         normalized["color"]       = rb_color(text_up) or ""
            if not normalized.get("other"):         normalized["other"]       = rb_other(desc, normalized)

            # Fill product using PRODUCT_MAP if empty
            if not normalized.get("product"):
                for k, v in PRODUCT_MAP.items():
                    if k in text_up:
                        normalized["product"] = v
                        break

            parsed = normalized

        combined = {**row.to_dict(), **parsed}
        parsed_rows.append(combined)

        print(f" finising {i} row...")
        # sleep_time = random.uniform(0, 0.5)
        # print(f"  😴 Sleeping {sleep_time:.2f} seconds...")
        # time.sleep(sleep_time)
    out_df = pd.DataFrame(parsed_rows)
    out_df.to_excel(output_stream, index=False)
    output_stream.seek(0)


def process_row_regex(row, parsed_json=None):
    """
    Fill missing fields in a row using rule-based regex extraction.
    
    Args:
        row (pd.Series or dict): Original row from the Excel.
        parsed_json (dict or None): Optional JSON from LLM.
        
    Returns:
        dict: Row with OUTPUT_FIELDS filled using regex rules.
    """

    # Initialize normalized dictionary with empty values
    normalized = {f: "" for f in OUTPUT_FIELDS}

    # Device description text in uppercase
    desc_r = str(row.get("Device Description", "")).strip()
    desc = re.sub(r'\s+', ' ', desc_r.strip())
    text_up = desc.upper()

    # Step 1: Fill from LLM if available
    if parsed_json:
        for k, v in parsed_json.items():
            if k.lower() in [x.lower() for x in OUTPUT_FIELDS]:
                normalized[k.lower()] = str(v).strip()

    # Step 2: Fill missing fields using rule-based functions
    if not normalized.get("diameter"):      normalized["diameter"]    = rb_extract_diameter(text_up) or ""
    if not normalized.get("length"):        normalized["length"]      = rb_extract_length(text_up) or ""
    if not normalized.get("height"):        normalized["height"]      = rb_extract_height(text_up) or ""
    if not normalized.get("width"):         normalized["width"]       = rb_extract_width(text_up) or ""
    if not normalized.get("thickness"):     normalized["thickness"]   = rb_thickness(text_up) or ""
    if not normalized.get("coated"):        normalized["coated"]      = rb_coated(text_up) or ""
    if not normalized.get("constrained"):   normalized["constrained"] = rb_constrained(text_up) or ""
    if not normalized.get("material"):      normalized["material"]    = rb_material(text_up) or ""
    if not normalized.get("cannulated"):    normalized["cannulated"]  = rb_cannulated(text_up) or ""
    if not normalized.get("cancellous"):    normalized["cancellous"]  = rb_cancellous(text_up) or ""
    if not normalized.get("thread"):        normalized["thread"]      = rb_thread(text_up) or ""
    if not normalized.get("locking"):       normalized["locking"]     = rb_locking(text_up) or ""
    if not normalized.get("size"):          normalized["size"]        = rb_size(text_up) or ""
    if not normalized.get("compression"):   normalized["compression"] = rb_compression(text_up) or ""
    if not normalized.get("shape"):         normalized["shape"]       = rb_shape(text_up) or ""
    if not normalized.get("loop"):          normalized["loop"]        = rb_loop(text_up) or ""
    if not normalized.get("bone"):          normalized["bone"]        = rb_bone(text_up) or ""
    if not normalized.get("side"):          normalized["side"]        = rb_side(text_up) or ""
    if not normalized.get("angle"):         normalized["angle"]       = rb_angle(text_up) or ""
    if not normalized.get("position"):      normalized["position"]    = rb_position(text_up) or ""
    if not normalized.get("offset"):        normalized["offset"]      = rb_offset(text_up) or ""
    if not normalized.get("sterile"):       normalized["sterile"]     = rb_sterile(text_up) or ""
    if not normalized.get("headed"):        normalized["headed"]      = rb_headed(text_up) or ""
    if not normalized.get("dimensions"):    normalized["dimensions"]  = ""
    if not normalized.get("color"):         normalized["color"]       = rb_color(text_up) or ""
    if not normalized.get("other"):         normalized["other"]       = rb_other(desc, normalized)

    # Step 3: Fill product from PRODUCT_MAP if empty
    if not normalized.get("product"):
        for k, v in PRODUCT_MAP.items():
            if k in text_up:
                normalized["product"] = v
                break

    # Step 4: Combine original row with extracted fields
    combined = {**row.to_dict(), **normalized} if isinstance(row, pd.Series) else {**row, **normalized}
    return combined


def process_stream_pipelined(input_stream, output_stream, max_rows=None, regex_workers=4):
    df = pd.read_excel(input_stream)
    for field in OUTPUT_FIELDS:
        if field not in df.columns:
            df[field] = ""

    regex_results = [None] * len(df)  # to preserve order
    queue = Queue()

    # Worker for regex processing
    def regex_worker():
        while True:
            item = queue.get()
            if item is None:
                break
            idx, row, parsed_json = item
            print(f"  🧩 Extracting data with Regex for the {idx}...")
            regex_results[idx] = process_row_regex(row, parsed_json)
            queue.task_done()

    # Start regex worker pool
    threads = []
    for _ in range(regex_workers):
        t = Thread(target=regex_worker)
        t.start()
        threads.append(t)

    # Sequential LLM calls + push to regex queue
    for i, row in df.iterrows():
        print(f"  🤖 Extracting data with gemini for the {i}...")
        if max_rows and i >= max_rows:
            break

        desc_r = str(row.get("Device Description", "")).strip()
        desc = re.sub(r'\s+', ' ', desc_r.strip())
        if not desc:
            queue.put((i, row, None))
            continue

        prompt = PROMPT_RULES + "\n\nNow parse the following Device Description using ONLY the rules above and return a single JSON object with these exact keys: " + ", ".join(OUTPUT_FIELDS) + ". Use empty string \"\" for fields that cannot be determined.\n\nDevice Description:\n" + desc

        retries = 0
        while retries < 5:
            try:
                resp_text = call_gemini_chat(prompt)
                break
            except Exception as e:
                retries += 1
                current_model = next(model_cycle)
                print(f"⚠️ API error: {e}. Waiting 30s before retrying with {current_model}")
                time.sleep(30)

        parsed_json = extract_json_from_text(resp_text or "")
        queue.put((i, row, parsed_json))  # push immediately to regex workers

    # Stop workers
    queue.join()
    for _ in range(regex_workers):
        queue.put(None)
    for t in threads:
        t.join()

    # Save output
    out_df = pd.DataFrame(regex_results)
    out_df.to_excel(output_stream, index=False)
    output_stream.seek(0)


def process_container_files(
    output_prefix="AI-data-extract-output/", 
    allowed_folders = []
):
    """
    Process only files from specific folders in Azure blob storage.
    - Saves into structure:
      AI-review-rating-output01/{date}_review-rating/<file>-AI-Review&Rating.csv
    """

    print("📂 Fetching files from Azure container...")

    fda_allowed_file = pd.read_excel(r"D:\Surgzon\FDA Codes to Retrieve.xlsx", usecols=["PRODUCTCODE"])
    allowed_prefix = fda_allowed_file["PRODUCTCODE"].tolist()
    # keywords = ["Foot", "Ankle", "Plate", "Screws", "Knee", "Hip", "Screw"]

    folders = {}
    file_count = 0
    for blob in container_client.list_blobs():
        if not any(blob.name.startswith(f"{folder}/") for folder in allowed_folders):
            continue

        if not (blob.name.endswith(".csv") or blob.name.endswith(".xlsx")):
            continue

        # if "/output/" not in blob.name:
        #     continue

        filename = os.path.basename(blob.name)
        if not any(filename.startswith(f"{pf}") for pf in allowed_prefix):
            continue
        
        file_count += 1
        folder_name = blob.name.split("/")[0]  # e.g., "20250214"
        if folder_name not in folders:
            folders[folder_name] = []
        folders[folder_name].append(blob)

    print(f"📂 Found {file_count} matching files")

    for folder_name, blobs in folders.items():
        output_folder = f"{output_prefix}{folder_name}_data-extract/"
        n = len(blobs)
        start = int(n * 0.0)
        end = int(n * 0.35)
        filtered_blobs = blobs[start:end]
        # blobs.sort(key=lambda b: b.name, reverse=True)
        print(f"📂 Filtered {len(blobs)} matching files")
        for blob in filtered_blobs:
            print(f"📥 Processing file: {blob.name}")

            blob_client = container_client.get_blob_client(blob.name)
            output_blob_name = (
                f"{output_folder}{os.path.basename(blob.name).replace('.csv', '-AI-Extracted.xlsx')}"
            )
            output_blob_client = container_client.get_blob_client(output_blob_name)

            # Download input file
            data = blob_client.download_blob().readall()
            if blob.name.endswith(".csv"):
                df = pd.read_csv(StringIO(data.decode("utf-8")))
            else:
                df = pd.read_excel(BytesIO(data))

            # Resume logic (if output already exists)
            try:
                existing_data = output_blob_client.download_blob().readall()
                df_out = pd.read_excel(BytesIO(existing_data))

                print(f"🔄 Resuming {blob.name} ({len(df_out)} rows already processed)")

                # Merge processed results into df
                for col in PARSED_FIELDS:
                    if col in df_out.columns:
                        df[col] = df_out[col]

                # Count completed rows = any parsed field non-empty
                completed_rows = df[
                    df[PARSED_FIELDS].notna().any(axis=1) &
                    (df[PARSED_FIELDS].astype(str).apply(lambda x: x.str.strip() != "").any(axis=1))
                ].shape[0]

                if completed_rows == len(df):
                    print(f"⏩ Skipping...✅ Already fully processed: {blob.name}")
                    continue

                print(f"➡️ Resuming {blob.name}: {completed_rows}/{len(df)} rows done")

            except Exception:
                print(f"➡️ Starting fresh for {blob.name}")

            # --- Run your existing processing function ---
            with BytesIO() as temp_in, BytesIO() as temp_out:
                # Save df locally in memory (Excel format) so process_excel can use it
                df.to_excel(temp_in, index=False)
                temp_in.seek(0)

                # Run your processor
                process_stream_pipelined(temp_in, temp_out)

                # Upload processed output to Azure
                temp_out.seek(0)
                output_blob_client.upload_blob(temp_out, overwrite=True)

            print(f"✅ Finished processing & uploaded: {output_blob_name}\n\n")


# Example usage:
if __name__ == "__main__":
    allowed_folders = [
        '20251201', '20251202', '20251203', '20251205', '20251208',
        '20251209', '20251210', '20251211', '20251212', '20251215',
        '20251216', '20251217', '20251218', '20251219', '20251222',
        '20251223', '20251224', '20251225', '20251226', '20251229',
        '20251230', '20251231',

        '20260101', '20260102', '20260105', '20260106', '20260108',
        '20260109', '20260112', '20260113', '20260114', '20260115', '20260116'
    ]
    process_container_files(allowed_folders=allowed_folders)

    # print("\n ::: rule-based JSON Response ::: \n", parsed)