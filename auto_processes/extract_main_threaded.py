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
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from folder_fetcher import get_recent_folders
from auto_config import *

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

# Gemini Setup for threading
try:
    import google.generativeai as genai
except Exception:
    genai = None

if not genai:
    raise RuntimeError("google.generativeai not installed or importable in this environment.")

# Use single API key for threading
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_CLIENT")  # Single API key
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Single model

# Thread-safe configuration lock
config_lock = Lock()

# Thread-safe progress tracking
progress_lock = Lock()
save_lock = Lock()

def call_gemini_threaded(prompt_text, max_attempts: int = 3):
    """Thread-safe Gemini API call using single API key"""
    for attempt in range(max_attempts):
        try:
            # Thread-safe configuration - all threads use same API key
            with config_lock:
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel(GEMINI_MODEL)
            
            resp = model.generate_content(prompt_text, generation_config={"temperature": 0.0})
            return getattr(resp, "text", str(resp))

        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg or "exceeded" in error_msg:
                print(f"⚠️ API quota issue on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(30)  # Wait before retry
            else:
                print(f"⚠️ Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5)

    raise RuntimeError("All Gemini API attempts exhausted after retries.")

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
# PROMPT (exact block from original file)
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
    - If the number appears before words like "HOLE", "HOLES", do not treat it as a diameter.
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
    - Match when a number is directly followed or preceded by "HOLE", "HOLES", or "H".
    - Examples:
        - 6H, 10 HOLE, 08 Holes, 9 Hole
    - Convert format: → <number>-Hole
        - e.g., 6H → 6-Hole, 10 Holes → 10-Hole.
2. Explicit "SIZE" Keyword
    - Match when the word "SIZE" is followed by a number or short abbreviation.
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
        - Do not keep abbreviations in short form (e.g., "L/XL" → write "Large–X-Large").
        - Always detect both sides of the slash (/) if present.
4. Valid Context Requirement
    - Only consider size values if they appear in a clear context (e.g., near "SIZE" or "HOLE") or match the known abbreviations above.
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
    - If the text contains the word "OFFSET" but no numeric value is present with the + or /+ pattern, do not extract anything.
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
    out["other"]         = rb_other(t, out) or ""
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
def process_single_row(args):
    """Process a single row - extract data fields using AI and rule-based methods"""
    idx, row, thread_id = args
    
    try:
        description = row.get("Device Description", "")
        if pd.isna(description) or str(description).strip() == "":
            print(f"🧵 Thread-{thread_id}: ⚠️ Skipping row {idx+1} - Device Description missing")
            return idx, None, "missing_description"

        desc = str(description).strip()
        print(f"🧵 Thread-{thread_id}: 🤖 Processing row {idx+1}: {desc[:50]}...")

        # Step 1: LLM Extraction
        prompt = PROMPT_RULES + "\n\nNow parse the following Device Description using ONLY the rules above and return a single JSON object with these exact keys: " + ", ".join(OUTPUT_FIELDS) + ". Use empty string \"\" for fields that cannot be determined.\n\nDevice Description:\n" + desc
        
        resp_text = call_gemini_threaded(prompt)
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

        print(f"🧵 Thread-{thread_id}: ✅ Row {idx+1} completed")
        return idx, parsed, "success"

    except Exception as e:
        print(f"🧵 Thread-{thread_id}: ❌ Error processing row {idx+1}: {e}")
        return idx, None, f"error: {e}"


def save_batch_progress(df, output_blob_client, processed_results, batch_size=10):
    """Save progress in batches to avoid losing work"""
    try:
        # Update dataframe with processed results
        for idx, parsed_data, status in processed_results:
            if parsed_data and status == "success":
                for field, value in parsed_data.items():
                    if field in df.columns:
                        df.at[idx, field] = value

        # Save to Azure
        with BytesIO() as temp_out:
            df.to_excel(temp_out, index=False)
            temp_out.seek(0)
            
            with save_lock:
                output_blob_client.upload_blob(temp_out, overwrite=True)
        
        print(f"💾 Batch progress saved ({len(processed_results)} rows)")
        return True
        
    except Exception as e:
        print(f"❌ Error saving batch progress: {e}")
        return False


def process_container_files_threaded(
    output_prefix="AI-data-extract-output/",
    allowed_folders=None,
    max_workers=5,
    batch_save_size=10
):
    """
    Process files from Azure blob storage using threading for parallel row processing.
    """
    print(f"📂 Fetching files from Azure container with {max_workers} threads...")

    if allowed_folders is None:
        allowed_folders = []

    # Load FDA allowed files
    fda_allowed_file = pd.read_excel(r"D:\Surgzon\FDA Codes to Retrieve.xlsx", usecols=["PRODUCTCODE"])
    allowed_prefix = fda_allowed_file["PRODUCTCODE"].tolist()

    folders = {}
    file_count = 0
    row_count_total = 0

    # Collect files from Azure
    for blob in container_client.list_blobs():
        if not any(blob.name.startswith(f"{folder}/") for folder in allowed_folders):
            continue

        if not (blob.name.endswith(".csv") or blob.name.endswith(".xlsx")):
            continue

        filename = os.path.basename(blob.name)
        if not any(filename.startswith(f"{pf}") for pf in allowed_prefix):
            continue
        
        file_count += 1
        folder_name = blob.name.split("/")[0]
        if folder_name not in folders:
            folders[folder_name] = []
        folders[folder_name].append(blob)

    print(f"📂 Found {file_count} matching files")

    # Process each folder
    for folder_name, blobs in folders.items():
        output_folder = f"{output_prefix}{folder_name}_data-extract/"
        n = len(blobs)
        start = int(n * 0.0)
        end = int(n * 0.35)
        filtered_blobs = blobs[start:end]
        
        print(f"📂 Processing {len(filtered_blobs)} files from folder {folder_name}")
        
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

            # Add missing columns
            for field in OUTPUT_FIELDS:
                if field not in df.columns:
                    df[field] = ""

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

            # Find rows that need processing
            rows_to_process = []
            for i, row in df.iterrows():
                already_processed = any(
                    str(row.get(field, "")).strip() != "" for field in PARSED_FIELDS
                )
                if not already_processed:
                    rows_to_process.append((i, row))

            if not rows_to_process:
                print(f"⏩ All rows already processed in {blob.name}")
                continue

            print(f"🧵 Processing {len(rows_to_process)} rows with {max_workers} threads...")

            # Process rows in parallel using ThreadPoolExecutor
            processed_results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_row = {}
                for i, (idx, row) in enumerate(rows_to_process):
                    thread_id = i % max_workers + 1
                    future = executor.submit(process_single_row, (idx, row, thread_id))
                    future_to_row[future] = (idx, row)

                # Process completed tasks with progress bar
                with tqdm(total=len(rows_to_process), desc=f"🧵 Threading {os.path.basename(blob.name)}") as pbar:
                    for future in as_completed(future_to_row):
                        result = future.result()
                        processed_results.append(result)
                        pbar.update(1)

                        # Save progress in batches
                        if len(processed_results) >= batch_save_size:
                            save_batch_progress(df, output_blob_client, processed_results, batch_save_size)
                            processed_results = []  # Reset for next batch

            # Save any remaining results
            if processed_results:
                save_batch_progress(df, output_blob_client, processed_results, batch_save_size)

            row_count_total += len(rows_to_process)
            print(f"✅ Finished processing & uploaded: {output_blob_name}\n")

    # Summary
    print("\n🎉 Threaded processing completed!")
    print(f"📊 Total files processed: {file_count}")
    print(f"📑 Total rows processed: {row_count_total}")
    print(f"🧵 Used {max_workers} parallel threads")


def get_recent_folders_automatically(days=None, method="date_range"):
    """
    Automatically fetch recent folders from Azure blob storage.

    Args:
        days (int): Number of recent days to fetch folders for (default: from config)
        method (str): Method to use for fetching ("date_range", "modified", "created", "both")

    Returns:
        List[str]: List of recent folder names
    """
    if days is None:
        days = DAYS_TO_FETCH

    print(f"🔄 Auto-fetching folders using method '{method}' for last {days} days...")

    try:
        if method == "date_range":
            recent_folders = get_recent_folders(days=days)
        elif method == "modified":
            from folder_fetcher import get_folders_by_last_modified
            hours = days * 24
            recent_folders = get_folders_by_last_modified(hours_ago=hours)
        elif method == "created":
            from folder_fetcher import get_folders_by_creation_time
            hours = days * 24
            recent_folders = get_folders_by_creation_time(hours_ago=hours)
        elif method == "both":
            from folder_fetcher import get_newly_added_folders
            hours = days * 24
            recent_folders = get_newly_added_folders(hours_ago=hours, method="both")
        else:
            print(f"❌ Invalid method '{method}'. Using 'date_range' as fallback.")
            recent_folders = get_recent_folders(days=days)

        if recent_folders:
            print(f"✅ Auto-fetched {len(recent_folders)} recent folders: {recent_folders}")
        else:
            print(f"⚠️ No folders found using method '{method}' for last {days} days")

        return recent_folders

    except Exception as e:
        print(f"❌ Error auto-fetching folders: {e}")
        print("⚠️ Falling back to manual folder list...")
        return []


# Example usage:
if __name__ == "__main__":
    print("🚀 Starting AI Data Extraction with THREADING")
    print("=" * 70)

    # 🔄 Determine which folders to use
    if AUTO_FETCH_FOLDERS:
        print("🔄 AUTO_FETCH_FOLDERS enabled - fetching recent folders automatically...")
        print(f"   📅 Days to fetch: {DAYS_TO_FETCH}")
        print(f"   🔧 Method: {FOLDER_FETCH_METHOD}")

        allowed_folders = get_recent_folders_automatically(
            days=DAYS_TO_FETCH,
            method=FOLDER_FETCH_METHOD
        )

        if not allowed_folders and USE_MANUAL_FALLBACK:
            print("⚠️ Auto-fetch returned no folders, falling back to manual list")
            allowed_folders = MANUAL_ALLOWED_FOLDERS
        elif not allowed_folders:
            print("❌ No folders found and manual fallback is disabled")
            print("   Either enable USE_MANUAL_FALLBACK or check your Azure connection")
            exit(1)
    else:
        print("📂 Using manual folder list from config...")
        allowed_folders = MANUAL_ALLOWED_FOLDERS

    print(f"📂 Final folder list ({len(allowed_folders)} folders): {allowed_folders}")

    # 🧵 Threading configuration
    MAX_WORKERS_FINAL = MAX_WORKERS           # Number of parallel threads
    BATCH_SAVE_SIZE_FINAL = BATCH_SAVE_SIZE   # Save progress every N completed rows

    print(f"🧵 Using {MAX_WORKERS_FINAL} parallel threads")
    print(f"💾 Saving progress every {BATCH_SAVE_SIZE_FINAL} completed rows")
    print("=" * 70)

    # Run the threaded processing
    process_container_files_threaded(
        output_prefix="AI-data-extract-output/",
        allowed_folders=allowed_folders,
        max_workers=MAX_WORKERS_FINAL,
        batch_save_size=BATCH_SAVE_SIZE_FINAL
    )