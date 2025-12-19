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

# PROMPT (exact block you provided — DO NOT CHANGE THIS BLOCK)
PROMPT_RULES = """You are an AI data extraction expert. 
Your task is to extract the following structured fields from medical device text data:

Target Fields:
- company
- product
- warranty
- length
- diameter
- height
- coated
- thickness
- constrained
- material
- cannulated
- cancellous
- thread
- locking
- size
- compression
- shape
- loop
- bone
- side
- angle
- position
- offset
- sterile

-----------------------------
📌 PRODUCT NAME MAPPING RULES
-----------------------------
Some rows contain the full product name in the Device Description field, while others use abbreviations. 
You must accurately map these abbreviations to their full product names:

- COMP PLATE → compression plate
- FRAG SCRW → fragment screw
- FRAC PLT SCRW → fracture plate screw
- CONTURLK HTO PLT → contourlock high tibial osteotomy plate
- OSTEO SUPPORT PLT → osteotomy support plate
- PLT,OPENG WEDG OSTEO → opening wedge osteotomy plate

- PLT,LO-PRO → low profile plate
- LPS → low profile plate  # same product name has multiple short forms

- LP SCREW → low profile screw
- LO-PRO SCRW → low profile screw
- LOW PROF SCRW → low profile screw  # same product name has multiple short forms

- L-PLATE → l-shape plate
- LO-PRO STR PLT → low profile straight plate
- LO-PRO MTP PLT → low profile metatarsophalangeal plate
- FIB PLT → fibula plate
- DBL COMP PLATES → double compression plate
- BTB → bone-tendon-bone
- TIB A/P SLPD OSTEO PLT → tibial osteotomy plate
- HTO IMPL,IBAL → iBalance high tibial osteotomy implant
- MTP PLT → metatarsophalangeal plate
- CONTURLK FEM OS-TEOTOMY PLT → contourlock femoral osteotomy plate
- HUM INSERT → humeral insert
- PLATE, POW, LOCKING → proximal opening wedge "pow" plate
- LO-PRO STR PLT → low profile straight plate
- T-ROPE SYNDESMO BUTTRESS PLATE → tightrope syndesmosis buttress plate

-----------------------------
📌 FIELD-SPECIFIC EXTRACTION RULES
-----------------------------

Length / Diameter:
- If text like "(6.7 X 95MM)" appears, assume first value is diameter and second is length.
- If text like "(42 + 12MM)" appears, assume first is diameter.

Height:
- If prefix includes "+" with MM or postfix includes "STEP", extract as height.

Thickness:
- Use the format "+(number)".

Coated:
- CTD → Coated
- CAP CTD / COATED → Cap Coated

Constrained:
- CONST → Yes

Material:
- TI / TITANIUM → Titanium
- SS → Stainless Steel

Cannulated:
- CANN → Cannulated / Yes

Cancellous:
- CANC → Cancellous
- CORTICAL → Cortical
- CORTEX / NEAR CORTEX → Cortex

Thread:
- PT THD → Partially Threaded
- FULLY THRDED → Fully Threaded

Locking:
- "Lock" present → Locking = Yes

Size:
- 6H → 6-Hole
- 10 HOLE → 10-Hole
- L/XL → Large–X-Large
- S/M → Small–Medium
- STD → Standard
- LNG → Long
- SIZE 14 → Size 14
- S → Small
- M → Medium
- L → Large
🔹 Size  
Extract size only if it matches one of the following recognized patterns or abbreviations:
- ((number)+\s*HOLE) → e.g., 6H, 10 HOLE → convert to <number>-Hole
- SIZE\s*(number)+ → e.g., SIZE 14 → keep as Size 14
- Fixed abbreviations:
    S/M → Small–Medium
    L/XL → Large–X-Large
    STD → Standard
    LNG → Long
    S → Small
    M → Medium
    L → Large
- Do not treat plain numbers (e.g., 42, 39, 24) as size unless they are explicitly prefixed with SIZE, suffixed with HOLE, or match one of the above abbreviations.
- If none of the valid patterns are present, return None.

Compression:
- DBL → Double

Shape:
- SQUARE → Square
- STR → Straight
- HEXALOBE → Hexalobe
- A/P SLPD → Antero-Posterior Sloped Wedge
- META OPEN WDG → Metatarsal Opening Wedge
- NAR → Narrow
- WIDE → Wide
- CONTRD → Contoured
- 10MM WEDGE → 10 mm Wedge

Loop:
- LOOP → Extract numeric values (e.g., 40, 35, 30)

Bone:
- HUMERAL → Humerus
- TIBIAL → Tibia
- FEMORAL → Femur
- RADIUS → Radius

Side:
- RT → Right
- LT → Left

Angle:
- Values like 14°, 15° etc. → Angle

Position:
- INF → Inferior

Offset:
- Use the format "+(number)"

Sterile:
- STERILE → Yes / No

-----------------------------
📌 OUTPUT FORMAT
-----------------------------
Return the result strictly as a JSON object with these keys:

{
 "company": "",
 "product": "",
 "warranty": "",
 "length": "",
 "diameter": "",
 "height": "",
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
 "sterile": ""
}

If a field is not found, return an empty string for it.

"""

# The EXACT output fields you requested:
OUTPUT_FIELDS = [
    "company","product","warranty","length","diameter","height","coated",
    "thickness","constrained", "material", "cannulated","cancellous","thread","locking",
    "size","compression","shape","loop","bone","side","angle","position","offset","sterile"
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
    text = text.upper()

    m = re.search(r'(\d+(?:\.\d+)?)\s*[x×]\s*\d+(?:\.\d+)?\s*MM', text, re.IGNORECASE)
    if m:
        return m.group(1) + "MM"

    # Case 2: Matches "42 + 12MM" → diameter = first number
    m = re.search(r'(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)(\s*MM)', text)
    if m:
        return m.group(1) + "MM"

    # Case 3: Only single number (with/without MM) → diameter    ^.*?(\d+(?:\.\d+)?)\s*
    m = re.search(r'(\d+(?:\.\d+)?)(\s*MM)?', text)
    if m:
        return m.group(1) + "MM"

    return None

def rb_extract_length(text: str):
    text = text.upper()

    # Case 1: Matches "6.7 X 95MM" → length = second number
    m = re.search(r'(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)(\s*MM)', text)
    if m:
        return m.group(2) + "MM"

    # Case 2: Matches "42 + 12MM" → length = second number
    # m = re.search(r'(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)(\s*MM)', text)
    # if m:
    #     return m.group(2) + "MM"

    # Case 3: Single number → no length
    return None

def rb_extract_height(text: str):
    text = text.upper()

    # Case 1: +numberMM  (e.g., "+12MM")
    m = re.search(r'(?<=\d)\+(\d+(?:\.\d+)?)\s*MM', text)
    if m:
        return f"+{m.group(1)}MM"

    # Case 2: numberMM STEP (e.g., "12MM STEP")
    m2 = re.search(r'(\d+(?:\.\d+)?)\s*MM\s*STEP', text)
    if m2:
        return f"{m2.group(1)}MM STEP"

    return None

def rb_thickness(text):
    m = re.search(r'\+(\d+(\.\d+)?)\b TO', text)
    if m:
        return "+" + m.group(1)
    return None

def rb_coated(text):
    if re.search(r'\bCAP CTD\b', text) or re.search(r'\bCAP COATED\b', text):
        return "Cap Coated"
    if re.search(r'\bCTD\b', text):
        return "Coated"
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
    return "Yes" if re.search(r'\bCANN\b', text) else None

def rb_cancellous(text):
    if re.search(r'\bCANC\b', text): return "Cancellous"
    if re.search(r'\bCORTICAL\b', text): return "Cortical"
    if re.search(r'\bCORTEX\b', text) or re.search(r'NEAR CORTEX', text): return "Cortex"
    return None

def rb_thread(text):
    if re.search(r'PT THD', text): return "Partially Threaded"
    if re.search(r'FULLY THRDED', text): return "Fully Threaded"
    return None

def rb_locking(text):
    return "Yes" if re.search(r'\bLOCK\b', text) or re.search(r'LOCKING', text) else None

def rb_size(text):
    m = re.search(r'(\d+)\s*HOLE', text)
    if m: return f"{m.group(1)}-Hole"
    if re.search(r'\b6H\b', text): return "6-Hole"
    if re.search(r'\bL/XL\b', text): return "Large–X-Large"
    if re.search(r'\bS/M\b', text): return "Small–Medium"
    if re.search(r'\bSTD\b', text): return "Standard"
    if re.search(r'\bS\b', text): return "Small"
    if re.search(r'\bM\b', text): return "Medium"
    if re.search(r'\bL\b', text): return "Large"
    if re.search(r'\bLNG\b', text): return "Long"
    m2 = re.search(r'SIZE\s*(\d+)', text)
    if m2: return "Size " + m2.group(1)
    return None

def rb_compression(text):
    return "Double" if re.search(r'\bDBL\b', text) else None

def rb_shape(text):
    shapes = {
        "SQUARE":"Square","STR":"Straight","HEXALOBE":"Hexalobe","A/P SLPD":"Antero-Posterior Sloped Wedge",
        "META OPEN WDG":"Metatarsal Opening Wedge","NAR":"Narrow","WIDE":"Wide","CONTRD":"Contoured","10MM WEDGE":"10 mm Wedge"
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

def rb_bone(text):
    if re.search(r'HUMERAL', text): return "Humerus"
    if re.search(r'TIBIAL', text): return "Tibia"
    if re.search(r'FEMORAL', text): return "Femur"
    if re.search(r'RADIUS', text): return "Radius"
    return None

def rb_side(text):
    if re.search(r'\bRT\b', text): return "Right"
    if re.search(r'\bLT\b', text): return "Left"
    if re.search(r'\bLFT\b', text): return "Left"
    return None

def rb_angle(text):
    m = re.search(r'(\d+)\s*°', text)
    if not m:
        m = re.search(r'(\d+)\s*DEG', text)
    if m: return m.group(1) + "°"
    return None

def rb_position(text):
    if re.search(r'\INF\b', text): return "Inferior"
    if re.search(r'\LAT\b', text): return "lateral"
    return None
    

def rb_offset(text):
    m = re.search(r'\+(\d+)\s*MM', text)
    if m: return "+" + m.group(1) + "MM"
    return None

def rb_sterile(text):
    return "Yes" if re.search(r'\bSTERILE\b', text) else "No"


# High level fallback parser (applies the rule-based helpers)
def rule_based_parse(text):
    t = (text or "").upper()
    out = {k:"" for k in OUTPUT_FIELDS}

    # product mapping (best-effort)
    for short, fullname in PRODUCT_MAP.items():
        if short in t:
            out["product"] = fullname
            break

    out["diameter"] = rb_extract_diameter(t) or ""
    out["length"] = rb_extract_length or ""
    out["height"] = rb_extract_height(t) or ""
    out["thickness"] = rb_thickness(t) or ""
    out["coated"] = rb_coated(t) or ""
    out["constrained"] = rb_constrained(t) or ""
    out["cannulated"] = rb_cannulated(t) or ""
    out["material"] = rb_material(t) or ""
    out["cancellous"] = rb_cancellous(t) or ""
    out["thread"] = rb_thread(t) or ""
    out["locking"] = rb_locking(t) or ""
    out["size"] = rb_size(t) or ""
    out["compression"] = rb_compression(t) or ""
    out["shape"] = rb_shape(t) or ""
    out["loop"] = rb_loop(t) or ""
    out["bone"] = rb_bone(t) or ""
    out["side"] = rb_side(t) or ""
    out["angle"] = rb_angle(t) or ""
    out["position"] = rb_position(t) or ""
    out["offset"] = rb_offset(t) or ""
    out["sterile"] = rb_sterile(t) or ""
    # company/warranty are left empty by rule-based fallback unless present explicitly
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

# Main runner
def process_excel(input_path, output_path, text_column="Device Description", batch_sleep=0.5, max_rows=None):
    df = pd.read_excel(input_path)
    rows = df.shape[0] if max_rows is None else min(max_rows, df.shape[0])

    parsed_rows = []
    for idx in range(rows):
        desc = str(df.loc[idx, text_column]) if text_column in df.columns else str(df.iloc[idx, 0])

        prompt_for_row = PROMPT_RULES + "\n\nNow parse the following Device Description using ONLY the rules above and return a single JSON object with these exact keys: " + ", ".join(OUTPUT_FIELDS) + ". Use empty string \"\" for fields that cannot be determined.\n\nDevice Description:\n" + desc

        # resp_text = call_gemini_chat(prompt_for_row)
        resp_text = call_openai_chat(prompt_for_row)
        parsed_json = extract_json_from_text(resp_text)

        if parsed_json is None:
            # fallback
            diam = rb_extract_diameter(desc.upper())
            length = rb_extract_length(desc.upper())
            parsed = {k: "" for k in OUTPUT_FIELDS}
            parsed["product"] = ""
            for short, full in PRODUCT_MAP.items():
                if short in desc.upper():
                    parsed["product"] = full
                    break
            parsed["diameter"] = diam or ""
            parsed["length"] = length or ""
            parsed["sterile"] = rb_sterile(desc.upper())
            parsed["offset"] = rb_offset(desc.upper())
            parsed_rows.append(parsed)
        else:
            normalized = {k: "" for k in OUTPUT_FIELDS}
            for k, v in parsed_json.items():
                for target in OUTPUT_FIELDS:
                    if target.lower() == k.strip().lower():
                        normalized[target] = v if v is not None else ""
                        break
            if not normalized.get("product"):
                t = desc.upper()
                for short, full in PRODUCT_MAP.items():
                    if short in t:
                        normalized["product"] = full
                        break
            if not normalized.get("diameter") or not normalized.get("Length"):
                diam = rb_extract_diameter(desc.upper())
                length = rb_extract_length(desc.upper())
                if diam and not normalized.get("diameter"):
                    normalized["diameter"] = diam
                if length and not normalized.get("length"):
                    normalized["length"] = length
            if normalized.get("sterile") == "":
                normalized["sterile"] = rb_sterile(desc.upper()) or ""
            if normalized.get("offset") == "":
                normalized["offset"] = rb_offset(desc.upper()) or ""
            parsed_rows.append(normalized)

        time.sleep(batch_sleep)

    parsed_df = pd.DataFrame(parsed_rows)
    out_df = pd.concat([df.head(rows).reset_index(drop=True), parsed_df.reset_index(drop=True)], axis=1)
    out_df.to_excel(output_path, index=False)
    print(f"Saved parsed output to: {output_path}")

# Example usage:
if __name__ == "__main__":
    INPUT_FILE = "sample_rows_from_SZO-Filtered_File.xlsx"   
    # Data_Extractor/sample_rows_from_SZO-Filtered_File.xlsx
    OUTPUT_FILE = "parsed_output_gemini_sample_test04.xlsx"
    process_excel(INPUT_FILE, OUTPUT_FILE, text_column="Device Description", batch_sleep=0.35, max_rows=None)