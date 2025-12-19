import os
import re
import json
import time
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# --- Load API key ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY environment variable before running.")
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"

# --- Gemini client (google.generativeai) example usage ---
load_dotenv()
try:
    import google.generativeai as genai
except Exception:
    genai = None
    # If your environment uses a different library name/version, adapt the client calls below.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)
if not GEMINI_API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY environment variable before running.")
MODEL = "gemini-2.5-flash-lite"  # suggested strong model
if genai:
    genai.configure(api_key=GEMINI_API_KEY)


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

# Call Gemini chat (adjust if your client API differs)
def call_gemini_chat(prompt_text):
    if not genai:
        raise RuntimeError("google.generativeai not installed or importable in this environment.")

    try:
        # ✅ Create a chat model and send content
        model = genai.GenerativeModel(MODEL)
        resp = model.generate_content(prompt_text, generation_config={"temperature": 0.0})
    except Exception as e:
        print("Gemini API error:", e)
        return None

    # ✅ Extract text from response
    content = None
    if hasattr(resp, "text"):
        content = resp.text
    elif hasattr(resp, "candidates") and resp.candidates:
        # fallback shape
        content = resp.candidates[0].content.parts[0].text if resp.candidates[0].content.parts else ""
    else:
        content = str(resp)

    return content




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
company, product, warranty, length, diameter, height, coated, thickness, constrained, material,
cannulated, cancellous, thread, locking, size, compression, shape, loop, bone, side, angle,
position, offset, sterile

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
- If abbreviation exists, expand it (e.g., SCRW → Screw, PLT → Plate, CANN → Cannulated, DBL COMP PLATES → double compression plate, BTB → bone-tendon-bone,FIB PLT → fibula plate).
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
1. Dimension Pattern (D x LMM — only two numbers allowed)
- If the text has a pattern like (6.7 x 95MM) or (6.7 × 95MM) with exactly two numbers:
    - Extract second number as length.
    - Example: (6.7 X 95MM) → Length = 95, (6.0MMX 60MM) → Length = 60
- Ignore patterns with three numbers (e.g., 17x34x12MM, 10x28x11mm, 12x28x11mm, 15x40x13mm, etc).
2. Plus Pattern (D + HMM)
- If the text has a pattern like (42 + 12MM):
    - Second number (after +) is not length (it belongs to height).
    - Do not extract length (second number is height).
    - Example: 42 + 12MM → Diameter = 42, Length = None.
3. Single Number Pattern:
- Only one number with or without MM.
- Do not extract length (length = None).
4. Ignore SIZE Values
- If a number appears with/after SIZE, do not consider it as diameter.
- Example: SIZE 14 → Length = None.


🔹 Diameter 
Extract diameter based on the following rules:
1. Dimension Pattern (D x LMM — only two numbers allowed):
- If the text has a pattern like (6.7 x 95MM) or (6.0MMX 65MM) with exactly two numbers:
    - Extract first number as diameter.
    - Example: (6.7 X 95MM) → diameter = 6.7, (6.0MMX 60MM)) → diameter = 6.0, 
- Ignore patterns with three numbers (<number>x<number>x<number>mm) (e.g., 17x34x12MM, 10x28x11mm, 12x28x11mm, 15x40x13mm, etc), Do not extract diameter from this type of pattern.

2. Plus Pattern (D + HMM):
- If the text has a pattern like (42 + 12MM)
    - Extract first number as diameter.
    - Second number is height, not diameter.

3. Single Number Pattern:
- Only one number with or without MM.
- If only a single number is present with/without "MM", it is treated as diameter.
- Treat it as diameter (e.g., 8MM → diameter = 8, 39 → diameter = 39, 36 → diameter = 36).

4. Ignore SIZE Values
- If a number appears with/after SIZE, do not consider it as diameter.
- Example: SIZE 14 → Diameter = None
If none of the above patterns match, return None.


🔹 Height  
Extract height based on the following rules:
1. Dimension Pattern (A x B x C mm):
    - If the text contains a pattern in the form <number>x<number>x<number>mm (or × instead of x),
    - The first number is the height. 
    - Do not consider any other number as heigth from this pattern, like middle and last number not a height.
    - Example: 17x34x12mm → Height = 17, 15x40x13mm → Height = 15, 10x28x11mm → Height = 10, 07x34x12mm → Height = 7
2. Plus Pattern (A+ BMM):
    - If the text contains a pattern <number>+<number>MM (e.g., 42+15MM, 39+12MM, 42+15.5MM),
    - Then the second number (after +) is the height.
    - Return only the numeric part with the + sign.
    - Consider only this pattern, do not consider any other number with + sign.
    - Example: 42+15MM → +15, 39+15.5MM → +15.5.
3. Ignore Invalid Cases:
    - Do not extract standalone numbers like 42, 39, or 24MM unless they appear in one of the two valid patterns above.
    - If no valid pattern is found, return None.


🔹 Width 
- pattern: - Pattern: `17x34x12mm` → length = 12mm, width = 34mm, height = 17mm
- In this pattern middle number is treated as width. do not consider any other value for width.
- Example: (13x40x13mm) → width = 40, (08x28x11mm) → width = 28, (07x34x12mm) → width = 34.
- If only two values like `15x52mm` then do not consider any number as width, because first one is diameter and second is length.

🔹 Coated  
- CAP CTD / CAP COATED → Cap Coated  
- CTD → Coated

🔹 Thickness  
- Matches `+3`, `+6` etc. (without MM) → thickness = +<number>

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
Extract size only if it matches one of the following recognized patterns or abbreviations:
- ((number)+\s*HOLE) → e.g., 6H, 10 HOLE → convert to <number>-Hole
- SIZE\s*(number)+ → e.g., SIZE 14 → keep as Size 14
- Fixed abbreviations:
    L/XL → Large–X-Large
    S/M → Small–Medium,
    STD → Standard,
    LNG → Long,
    S → Small,
    M → Medium,
    L → Large
- Write full mapped label like L/XL → Large–X-Large, S/M → Small–Medium, detect the / and after / letter, do not check only first charecter.
- Do not only consider only first charecter, consider full abbreviation such as "S/M" = "Small-Medium", "L/XL" = "Large-X-Large".
- Do not assume and not write abbreviations in short like "L/XL", "S/M".
- Do not treat numbers (e.g., 42, 39, 24, 15.0MM) as size unless they are explicitly prefixed with SIZE, postfix with HOLE, or match one of the above abbreviations.
- If none of the valid patterns are present, return None.

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
- LOOP 40 / 40 LOOP → 40

🔹 Bone  
- HUMERAL → Humerus  
- TIBIAL → Tibia  
- FEMORAL → Femur  
- RADIUS → Radius  
- CALCANEUS → Calcaneus  
- TTC → Tibia - Talus - Calcaneus  
- TT → Tibia - Talus  
- MIDFOOT → Mid-foot

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
- +<number> or +<number>MM → Offset

🔹 Headed
- Headed present → Yes  
- Else → blank

🔹 Dimensions
- populate when PLATE size is aaMM X bbMM

🔹 Other
- All non categorized strings put in this field.

🔹 Color
- write the name of color if mention color in the field.

🔹 Headed  
- If the word "Headed" appears → Yes  
- Else → ""

🔹 Dimensions  
- Populate only when PLATE size is explicitly given as `<number>MM X <number>MM`  
  (e.g., "20MM X 150MM" → Dimensions = "20MM X 150MM")

🔹 Other  
- Capture all non-categorized text strings that do not match any other rule.

🔹 Color  
- If a color name (e.g., Blue, Black, Silver, Grey, Gold, Green, etc.) appears, extract it.

---

📌 OUTPUT FORMAT

Return strictly in this structure:

{
 "product": "",
 "warranty": "",
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
    "company","product","warranty","length","diameter","height","width", "coated",
    "thickness","constrained", "material", "cannulated","cancellous","thread","locking",
    "size","compression","shape","loop","bone","side","angle","position","offset","sterile", "headed", "dimensions", "other", "color",
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
def rb_extract_diameter(text: str):
    text_upper = text.upper()

    # Rule 4: Ignore SIZE
    if re.search(r'\bSIZE\s*\d+', text_upper):
        return None

    # Rule 1: Dimension Pattern (D x LMM)
    m = re.search(r'(\d+(?:\.\d+)?)(?:\s*MM)?\s*[xX]\s*(\d+(?:\.\d+)?)(?:\s*MM)?', text)
    if m:
        return m.group(1) + "MM"

    # Rule 2: Plus Pattern (D + HMM)
    m2 = re.search(r'(\d+(?:\.\d+)?)\s*\+\s*\d+(?:\.\d+)?\s*MM', text_upper, re.IGNORECASE)
    if m2:
        return m2.group(1)

    # Rule 3: Single number
    m3 = re.search(r'^.*?(\d+(?:\.\d+)?)\s*', text_upper, re.IGNORECASE)
    if m3:
        return m3.group(1)

    return None


def rb_extract_length(text: str):
    text_upper = text.upper()
    # Rule 1: Three-number pattern (D x W x LMM)
    m1 = re.search(r'(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*MM', text_upper, re.IGNORECASE)
    if m1:
        return m1.group(3)
    # Rule 2: Two-number pattern (D x LMM)
    m2 = re.search(r'(\d+(?:\.\d+)?)(?:\s*MM)?\s*[xX]\s*(\d+(?:\.\d+)?)(?:\s*MM)?', text_upper, re.IGNORECASE)
    if m2:
        return m2.group(2)
    # Rule 3: Plus pattern (D + HMM)
    m3 = re.search(r'(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)\s*MM', text_upper, re.IGNORECASE)
    if m3:
        return m3.group(2)
    return None

#------------- done -------------
def rb_extract_height(text: str):
    text_upper = text.upper()

    # Rule 1: Three-number pattern (D x W x HMM)
    m1 = re.search(r'(\d+(?:\.\d+)?)\s*[x×]\s*\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?\s*MM', text_upper, re.IGNORECASE)
    if m1:
        return m1.group(1) 
    # Rule 2: Plus pattern (D + HMM)
    m2 = re.search(r'\d+(?:\.\d+)?\s*\+\s*(\d+(?:\.\d+)?)\s*MM', text_upper, re.IGNORECASE) #(?<=\d)\+(\d+(?:\.\d+)?)\s*MM
    if m2:
        return m2.group(1)
    # # Rule 3: NumberMM STEP pattern
    # m3 = re.search(r'(\d+(?:\.\d+)?)\s*MM\s*STEP', text_upper, re.IGNORECASE)
    # if m3:
    #     return f"{m3.group(1)}MM STEP"
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
    Extracts thickness values like +3, +6 (without MM).
    """
    text = text.upper()
    m = re.search(r'\+(\d+(?:\.\d+)?)(?!\s*MM)', text)  # +number not followed by MM
    if m:
        return f"+{m.group(1)}"
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

#--------------------------------------------------------------
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

#---------------------------------------------------------------------------
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

#------------------------------------------------------------------
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
    
#-------- done ------
def rb_offset(text):
    m = re.search(r'(?<!\d)\+\s*\d+(?:\.\d+)?(?:MM)?', text)
    if m:
        return f"{m.group(0)}"
    return None

def rb_sterile(text):
    return "Yes" if re.search(r'\bSTERILE\b', text) else "No"

def rb_headed(text: str):
    """
    Detect if the product is 'Headed'.
    """
    if re.search(r'\bHEADED\b', text.upper()):
        return "Yes"
    return None


def rb_dimensions(text: str):
    """
    Extract dimensions specifically for PLATE sizes in aaMM X bbMM format.
    - Only consider when 'PLATE' or 'PLT' mentioned.
    - Return as normalized 'aaMM x bbMM'.
    """
    text_upper = text.upper()
    if "PLATE" in text_upper or "PLT" in text_upper:
        m = re.search(r'(\d+(?:\.\d+)?)\s*MM\s*[X×]\s*(\d+(?:\.\d+)?)\s*MM', text_upper)
        if m:
            return f"{m.group(1)}MM x {m.group(2)}MM"
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


def rule_based_parse(text: str) -> dict:
    """Extract all OUTPUT_FIELDS using regex/rule-based logic as fallback."""
    t = text.upper()
    out = {f: "" for f in OUTPUT_FIELDS}

    out["diameter"]      = rb_extract_diameter(t) or ""
    out["length"]        = rb_extract_length(t) or ""
    out["height"]        = rb_extract_height(t) or ""
    out["width"]       = rb_extract_width(t) or ""
    out["thickness"]     = rb_thickness(t) or ""
    out["coated"]       = rb_coated(t) or ""
    out["constrained"]   = rb_constrained(t) or ""
    out["material"]      = rb_material(t) or ""
    out["cannulated"]    = rb_cannulated(t) or ""
    out["cancellous"]    = rb_cancellous(t) or ""
    out["thread"]   = rb_thread(t) or ""
    out["locking"]       = rb_locking(t) or ""
    out["size"]           = rb_size(t) or ""
    out["compression"]   = rb_compression(t) or ""
    out["shape"]         = rb_shape(t) or ""
    out["loop"]           = rb_loop(t) or ""
    out["bone"]           = rb_bone(t) or ""
    out["side"]           = rb_side(t) or ""
    out["angle"]          = rb_angle(t) or ""
    out["position"]       = rb_position(t) or ""
    out["offset"]         = rb_offset(t) or ""
    out["sterile"]         = rb_sterile(t) or ""
    out["headed"]        = rb_headed(t) or ""
    out["dimensions"]    = rb_dimensions(t) or ""
    out["color"]         = rb_color(t) or ""

    # Try to map product name from PRODUCT_MAP
    for k,v in PRODUCT_MAP.items():
        if k in t:
            out["product"] = v
            break

    # Fallback: "other"
    out["other"] = rb_other(text, out)

    # Company and warranty usually not present in text, leave blank
    out["company"] = ""
    out["warranty"] = ""

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
    df = pd.read_excel(input_path)
    parsed_rows = []

    for i, row in df.iterrows():
        if max_rows and i >= max_rows:
            break

        desc = str(row.get("Device Description", "")).strip()
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
            if not normalized.get("diameter"):      normalized["diameter"] = rb_extract_diameter(text_up) or ""
            if not normalized.get("length"):        normalized["length"]   = rb_extract_length(text_up) or ""
            if not normalized.get("height"):        normalized["height"]   = rb_extract_height(text_up) or ""
            if not normalized.get("width"):        normalized["width"]   = rb_extract_width(text_up) or ""
            if not normalized.get("thickness"):     normalized["thickness"]= rb_thickness(text_up) or ""
            if not normalized.get("coated"):        normalized["coated"]   = rb_coated(text_up) or ""
            if not normalized.get("constrained"):   normalized["constrained"] = rb_constrained(text_up) or ""
            if not normalized.get("material"):      normalized["material"] = rb_material(text_up) or ""
            if not normalized.get("cannulated"):    normalized["cannulated"] = rb_cannulated(text_up) or ""
            if not normalized.get("cancellous"):    normalized["cancellous"] = rb_cancellous(text_up) or ""
            if not normalized.get("thread"):        normalized["thread"] = rb_thread(text_up) or ""
            if not normalized.get("locking"):       normalized["locking"]  = rb_locking(text_up) or ""
            if not normalized.get("size"):          normalized["size"]     = rb_size(text_up) or ""
            if not normalized.get("compression"):   normalized["compression"] = rb_compression(text_up) or ""
            if not normalized.get("shape"):         normalized["shape"]    = rb_shape(text_up) or ""
            if not normalized.get("loop"):          normalized["loop"]     = rb_loop(text_up) or ""
            if not normalized.get("bone"):          normalized["bone"]     = rb_bone(text_up) or ""
            if not normalized.get("side"):          normalized["side"]     = rb_side(text_up) or ""
            if not normalized.get("angle"):         normalized["angle"]    = rb_angle(text_up) or ""
            if not normalized.get("position"):      normalized["position"] = rb_position(text_up) or ""
            if not normalized.get("offset"):        normalized["offset"]   = rb_offset(text_up) or ""
            if not normalized.get("sterile"):       normalized["sterile"]  = rb_sterile(text_up) or ""
            if not normalized.get("headed"):     normalized["headed"]     = rb_headed(text_up) or ""
            if not normalized.get("dimensions"): normalized["dimensions"] = rb_dimensions(text_up) or ""
            if not normalized.get("color"):      normalized["color"]      = rb_color(text_up) or ""

            if not normalized.get("other"):
                normalized["other"] = rb_other(desc, normalized)

            # Fill product using PRODUCT_MAP if empty
            if not normalized.get("product"):
                for k,v in PRODUCT_MAP.items():
                    if k in text_up:
                        normalized["product"] = v
                        break

            parsed = normalized
        
        combined = {**row.to_dict(), **parsed}
        parsed_rows.append(combined)

    # Write output
    out_df = pd.DataFrame(parsed_rows)
    out_df.to_excel(output_path, index=False)
    print(f"✅ Saved parsed output to {output_path}")


# Example usage:
if __name__ == "__main__":
    INPUT_FILE = "sample_mid-30_from_SZO-Filtered_File.xlsx"   
    OUTPUT_FILE = "te3st_data03.xlsx"
    process_excel(INPUT_FILE, OUTPUT_FILE, max_rows=None)

# # Main runner
# def process_excel(input_path, output_path, text_column="Device Description", batch_sleep=0.5, max_rows=None):
#     df = pd.read_excel(input_path)
#     rows = df.shape[0] if max_rows is None else min(max_rows, df.shape[0])

#     parsed_rows = []
#     for idx in range(rows):
#         desc = str(df.loc[idx, text_column]) if text_column in df.columns else str(df.iloc[idx, 0])

#         prompt_for_row = PROMPT_RULES + "\n\nNow parse the following Device Description using ONLY the rules above and return a single JSON object with these exact keys: " + ", ".join(OUTPUT_FIELDS) + ". Use empty string \"\" for fields that cannot be determined.\n\nDevice Description:\n" + desc

#         # resp_text = call_gemini_chat(prompt_for_row)
#         resp_text = call_openai_chat(prompt_for_row)
#         parsed_json = extract_json_from_text(resp_text)

#         if parsed_json is None:
#             # fallback
#             diam = rb_extract_diameter(desc.upper())
#             length = rb_extract_length(desc.upper())
#             parsed = {k: "" for k in OUTPUT_FIELDS}
#             parsed["product"] = ""
#             for short, full in PRODUCT_MAP.items():
#                 if short in desc.upper():
#                     parsed["product"] = full
#                     break
#             parsed["diameter"] = diam or "" 
#             parsed["length"] = length or ""
#             parsed["sterile"] = rb_sterile(desc.upper())
#             parsed["offset"] = rb_offset(desc.upper())
#             parsed_rows.append(parsed)
#         else:
#             normalized = {k: "" for k in OUTPUT_FIELDS}
#             for k, v in parsed_json.items():
#                 for target in OUTPUT_FIELDS:
#                     if target.lower() == k.strip().lower():
#                         normalized[target] = v if v is not None else ""
#                         break
#             if not normalized.get("product"):
#                 t = desc.upper()
#                 for short, full in PRODUCT_MAP.items():
#                     if short in t:
#                         normalized["product"] = full
#                         break
#             if not normalized.get("diameter") or not normalized.get("length"):
#                 diam = rb_extract_diameter(desc.upper())
#                 length = rb_extract_length(desc.upper())
#                 if diam and not normalized.get("diameter"):
#                     normalized["diameter"] = diam
#                 if length and not normalized.get("length"):
#                     normalized["length"] = length
#             if normalized.get("sterile") == "":
#                 normalized["sterile"] = rb_sterile(desc.upper()) or ""
#             if normalized.get("offset") == "":
#                 normalized["offset"] = rb_offset(desc.upper()) or ""
#             parsed_rows.append(normalized)

#         time.sleep(batch_sleep)

#     parsed_df = pd.DataFrame(parsed_rows)
#     out_df = pd.concat([df.head(rows).reset_index(drop=True), parsed_df.reset_index(drop=True)], axis=1)
#     out_df.to_excel(output_path, index=False)
#     print(f"Saved parsed output to: {output_path}")