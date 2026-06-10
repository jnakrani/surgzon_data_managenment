# Surgzon

End-to-end pipeline that pulls daily-uploaded medical-device CSV/XLSX files from
**Azure Blob Storage**, runs **AI-based field extraction** (rule-rich orthopaedic
attributes) and **AI-generated review + 1–5 star rating** on each row, then
writes the enriched files back into the same container.

This README is the single source of truth for getting a new developer productive
without a hand-over session.

---

## 1. What the project actually does

The Surgzon Azure container (`surgzondata`) receives **daily folders** in the
form `YYYYMMDD/` (e.g. `20250602/`). Each daily folder holds many CSV/XLSX files
of orthopaedic device records (Brand Name, Device Description, GMDN PT
Definition, FDA Product Code, etc.).

There are two independent processing pipelines that both consume those files:

| Pipeline | Purpose | Input columns it reads | Output columns it writes | Output location in Azure |
| --- | --- | --- | --- | --- |
| **AI Review & Rating** | Generates a human-like 7-8 line product review and a strict 1–5 star rating for every row that has a `Device Description`. | `Brand Name`, `Device Description` | `AI_review`, `AI_rating` | `AI-review-rating-output01/{YYYYMMDD}_review-rating/<originalname>-AI-Review&Rating.csv` |
| **Data Extractor** | Extracts structured orthopaedic fields (length, diameter, material, thread, bone, cannulated, …) using a long REGEX-rule prompt + LLM. | `Device Description`, `Brand Name`, `GMDN PT Definition`, `FDA Product Code Name`, … | 25+ parsed columns (see `PARSED_FIELDS`) | `AI-data-extract-output/...` |

Both pipelines:
- **resume safely** — they download the existing output blob (if any), merge
  already-completed rows, and only fill missing rows
- **rotate** Gemini API keys + models on quota errors
- **log** to a per-pipeline log file (`AI-Review-Rating.log`) via
  `logger_functionality.py`

The `auto_processes/` folder is the **automation layer** that, when run daily,
queries Azure for the most recent 7 days of folders and patches the
`allowed_folders` list inside the runner scripts before launching them.

---

## 2. Repository layout

```
Surgzon/
├── AI_review_rating/         # Pipeline 1 — Gemini-powered review + rating
│   ├── review_rating_production.py     ⭐ canonical single-thread runner
│   ├── review_rating_threaded.py       ⭐ multi-thread runner (5 workers)
│   ├── review_rating_basic.py          earliest minimal version
│   ├── review_rating_all_files.py      same logic, no keyword filter
│   ├── review_rating_keyword_filter.py same logic, keyword-filtered
│   ├── review_rating_single_folder.py  run against one folder
│   ├── review_rating_selected_folders.py  hard-coded folder list
│   ├── review_rating_automated.py      same as production, cron-friendly
│   ├── review_rating_with_status_check.py preview / dry-run helper
│   ├── cronjob_folder_fetcher.py       discovers YYYYMMDD folders, patches runner
│   ├── run_daily_processing.py         pipeline wrapper (fetch → run)
│   ├── setup_daily_cronjob.bat         Windows Task Scheduler installer (23:59)
│   ├── qc_validation.py                Gemini-based QC for "is lower limb"
│   ├── logger_functionality.py         logger used by every script here
│   └── archive/                        old/openai/groq variants — reference only
│
├── Data_Extractor/           # Pipeline 2 — field extraction (rule + LLM)
│   ├── extract_main_file.py            ⭐ canonical extractor (OpenAI + Gemini)
│   ├── extract_main_threaded.py        threaded extractor (single Gemini key)
│   ├── extract_main_specific_2.py      run against a specific folder/file
│   ├── extract_main.py                 minimal first version
│   ├── extract_openai.py               OpenAI-only variant
│   ├── clean_file.py                   trims a raw CSV to the input columns
│   ├── logger_functionality.py
│   └── data/                           local sample input/output XLSX/CSV
│
├── auto_processes/           # Daily automation layer
│   ├── run_auto_processing.py          ⭐ entrypoint: updates folders → runs review/rating
│   ├── auto_folder_updater.py          rewrites `allowed_folders` in review_rating_threaded.py
│   ├── auto_config.py                  knobs (DAYS_TO_FETCH, MAX_WORKERS, …)
│   ├── folder_fetcher.py               Azure folder discovery utility (many helpers)
│   ├── review_rating_threaded.py       local copy that the updater patches
│   ├── extract_main_threaded.py        local copy for the extractor flavor
│   └── logger_functionality.py
│
├── utils/
│   └── logger.py                       generic logger (separate from pipeline ones)
│
├── azure_blob.py             # CLI to list/count folders & files in the container
├── azure_csv_fetcher.py      # Reusable function to download CSVs from any container
├── example_usage.py          # Demo of azure_csv_fetcher
├── quick_count.py            # Fast count of files in the four output folders
├── calculate_requests.py     # Helper: estimate Gemini API requests needed
├── requirements.txt          # Full dependency pin list
├── requirements_csv_fetcher.txt   # Slim deps for just the fetcher
├── .env                      # Secrets (Azure conn-string, all GEMINI_API_KEY*)
├── .gitignore
└── Data/                     # Local sample CSVs (gitignored)
```

`⭐` marks the files a new developer should actually read first.

---

## 3. Azure container conventions

| Path prefix in `surgzondata` container | What lives here |
| --- | --- |
| `YYYYMMDD/` | Daily-uploaded raw device CSVs/XLSXs (input) |
| `AI-review-rating-output01/{YYYYMMDD}_review-rating/` | Review+rating output |
| `AI-data-extract-output/...` | Field-extraction output |
| `latest_full_release/` | Aggregated latest release files |
| `latest_full_release_review-rating/` | Aggregated latest review+rating files |

Azure Blob has no real folders — everything is prefix matching on blob name.
`folder_fetcher.list_folders()` and `azure_blob.list_folders()` both build the
"folder list" by splitting on `/`.

---

## 4. Setup

### 4.1 Requirements

- Python 3.11+ on Windows (project was developed on Windows 11 with PowerShell;
  scripts use forward slashes and work on Linux too).
- A virtualenv (project ships one in `venv/`, gitignored).

### 4.2 Install

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Key libs: `azure-storage-blob`, `pandas`, `openai`, `google-generativeai`,
`python-dotenv`, `tqdm`, `spacy` (only used by `Data_Extractor/data/train_nre.py`).

### 4.3 `.env`

Already populated in this repo for convenience (it is **gitignored**). It
contains:

```
AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=surgzondata;…"
AZURE_BLOB_CONTAINER_NAME       = surgzondata
OPENAI_API_KEY                  = sk-proj-…
GEMINI_API_KEY_CLIENT           = AIza…
GEMINI_API_KEY1 … GEMINI_API_KEY30   # rotating pool, owner noted in comments
```

> ⚠️ **Never commit `.env`.** Each Gemini key has a free-tier quota; pipelines
> rotate them automatically when a `quota` / `429` / `exceeded` error fires.

---

## 5. Running the pipelines

### 5.1 Quick smoke test (read-only)

```powershell
python azure_blob.py --folders          # list all top-level "folders"
python azure_blob.py                    # full breakdown of output files
python quick_count.py                   # only counts in the 4 output folders
python AI_review_rating\review_rating_production.py
#   ↑ set `check_status_only = True` in __main__ first for a dry-run
```

### 5.2 AI Review & Rating (single-threaded, canonical)

[AI_review_rating/review_rating_production.py](AI_review_rating/review_rating_production.py)

Edit the `allowed_folders` list at the bottom (cron writes to this — see §6),
then run:

```powershell
cd d:\Surgzon
python AI_review_rating\review_rating_production.py
```

Behavior:
1. `check_processed_files(...)` summarizes fully/partial/not-started.
2. `process_container_files(...)` iterates blobs in `allowed_folders`:
   - skips files whose output blob already has both `AI_review` and `AI_rating`
     for every row
   - merges any partial output to resume
   - calls `generate_review()` then `generate_rating()` per row
   - uploads the CSV **after every row** (durable resume)
3. Logs go to `AI-Review-Rating.log` and stdout.

Flags in `__main__`:
- `check_status_only = True` — just print the summary, no work.
- `preview_only = True` — list files that would be processed.
- `run_automated = True` — used by the cron wrapper.

### 5.3 AI Review & Rating (threaded, 5 workers)

[AI_review_rating/review_rating_threaded.py](AI_review_rating/review_rating_threaded.py)

Same logic, parallel row processing. Saves are guarded by `save_lock`. Use this
in production for speed.

### 5.4 Data Extractor

[Data_Extractor/extract_main_file.py](Data_Extractor/extract_main_file.py)

- Loads OpenAI (`gpt-4o-mini`) **and** Gemini clients.
- Long `PROMPT_RULES` block encodes the orthopaedic regex rules (length,
  diameter, height, thread, material, …).
- Writes 25+ structured columns alongside the original row data.

For a folder-scoped run, prefer
[Data_Extractor/extract_main_specific_2.py](Data_Extractor/extract_main_specific_2.py)
or the threaded variant
[Data_Extractor/extract_main_threaded.py](Data_Extractor/extract_main_threaded.py).

[Data_Extractor/clean_file.py](Data_Extractor/clean_file.py) is a one-off that
strips a raw CSV down to the 30 columns the extractor expects — adjust
`file_path` / `output_file` at the top before running.

### 5.5 Daily automation

End-to-end nightly job, wired up via Windows Task Scheduler:

```
auto_processes\run_auto_processing.py
   └─► auto_folder_updater.py
         └─► folder_fetcher.get_recent_folders(days=7)
               └─► rewrites `allowed_folders = [...]` in review_rating_threaded.py
   └─► review_rating_threaded.py
```

Install the scheduled task once (run as Administrator):

```powershell
AI_review_rating\setup_daily_cronjob.bat
```

The task is named **Azure_Daily_Processing** and fires at **23:59** daily. Manage it with:

```powershell
schtasks /query  /tn "Azure_Daily_Processing"
schtasks /run    /tn "Azure_Daily_Processing"
schtasks /delete /tn "Azure_Daily_Processing" /f
```

---

## 6. How the `allowed_folders` list is updated

Two tools do this, depending on which runner you're targeting:

- [AI_review_rating/cronjob_folder_fetcher.py](AI_review_rating/cronjob_folder_fetcher.py)
  patches `AI_review_rating/review_rating_production.py` (recent 30 days, skips
  fully-processed folders).
- [auto_processes/auto_folder_updater.py](auto_processes/auto_folder_updater.py)
  patches `auto_processes/review_rating_threaded.py` (recent 7 days, always
  rewrites). It also creates a timestamped `.backup_YYYYMMDD_HHMMSS` next to
  the patched file.

Both use a regex against the literal text `allowed_folders = [ ... ]` — keep
that exact assignment shape if you edit by hand.

---

## 7. Gemini key rotation & quota handling

`API_KEYS` cycle (via `itertools.cycle`) across keys numbered 14–20 (plus
`GEMINI_API_KEY_CLIENT`). The model list also cycles:

```python
gemini_models = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
```

Any of `quota`, `429`, `exceeded`, `api_key_invalid` in an error message
triggers an advance of both cycles and a 2-second sleep. Hard 25-second sleep
on generic API errors. There's an optional `validate_api_keys()` helper if you
want to ping each key with a 1-token request at startup.

> If you add a new key to `.env`, also append `os.getenv("GEMINI_API_KEYxx")`
> to the `API_KEYS` list in every runner you want to use it from.

---

## 8. Output schema cheat-sheet

**Review & Rating output** keeps every input column and adds:
- `AI_review`  — 7-8 line, 70–120 word paragraph, opening phrase randomized
  from `orthopedic_user_review_phrases_varied` (66 templates) to keep
  diversity.
- `AI_rating` — strict integer 1..5 from a separate Gemini prompt; falls back
  to `None` if the model returns anything else.

**Data Extractor output** appends the 25+ `PARSED_FIELDS`:

```
diameter, length, height, width, thickness, coated, constrained, material,
cannulated, cancellous, thread, locking, size, compression, shape, loop, bone,
side, angle, position, offset, sterile, product, headed, dimensions, other, color
```

Rules for each field are documented inline in
[Data_Extractor/extract_main_threaded.py](Data_Extractor/extract_main_threaded.py)
inside `PROMPT_RULES`. Skim that block before changing any extraction
behavior — every entry there matches a real edge case.

---

## 9. Logging

Each pipeline package has its own `logger_functionality.py` that creates the
shared `logger` and a sibling `AI-Review-Rating.log` file (rotated by date in
`.gitignore`, never committed). Logs go to both file and stdout. Use it like:

```python
from logger_functionality import logger
logger.info("...")
```

There is also a generic [utils/logger.py](utils/logger.py) that writes to
`surgzon.log` — not currently imported by the active pipelines.

---

## 10. Common operational tasks

| Need | Command |
| --- | --- |
| List all folders in container | `python azure_blob.py --folders` |
| Count output files | `python quick_count.py` |
| Get recent-N-days folders as Python list | `python auto_processes\folder_fetcher.py --recent 7` |
| Preview which review/rating files would be processed | edit `preview_only = True` in `review_rating_production.py`, run it |
| Estimate API requests for a workload | `python calculate_requests.py` |
| Download all `output/` blobs for one date folder | `azure_blob.download_all_output_files("20250620")` |
| Rerun a single folder | use `review_rating_single_folder.py` (set the folder name in `__main__`) |

---

## 11. Gotchas / things that already burned us

- **Resume relies on column matching.** Don't rename `AI_review` / `AI_rating`
  — partial outputs will be ignored and the file will reprocess from row 0.
- **CSV vs XLSX.** Both pipelines read `.csv` (`StringIO`) and `.xlsx`
  (`BytesIO`) but **always write CSV** to the output blob. The output filename
  is built by `replace('.csv', '-AI-Review&Rating.csv')` — so an XLSX input
  still becomes a CSV output and the substitution is essentially a no-op (the
  original `.xlsx` extension is kept in the blob name).
- **Per-row save.** Every row triggers an Azure upload. For a 5 000-row file
  that's 5 000 PUTs — fine for cost, but don't be surprised by network noise.
- **Manual `allowed_folders` edits** must keep the `allowed_folders = [ … ]`
  shape intact or the cron/auto updater regex will fail to find it.
- **`venv/`, `Data/`, `*.csv`, `*.xlsx`, `.env`, `server-cred/`** are all
  gitignored. Don't accidentally `git add` data dumps.
- **`review_rating_production.py` and `auto_processes/review_rating_threaded.py`
  are *two different copies* of nearly the same runner.** The cron updaters
  patch only the one they target — keep them in sync if you change behavior.

---

## 12. Where to look next

- New to the codebase? Read in this order:
  1. [auto_processes/run_auto_processing.py](auto_processes/run_auto_processing.py) — top-level orchestration
  2. [auto_processes/folder_fetcher.py](auto_processes/folder_fetcher.py) — how folders are discovered
  3. [AI_review_rating/review_rating_production.py](AI_review_rating/review_rating_production.py) — the canonical worker
  4. [Data_Extractor/extract_main_threaded.py](Data_Extractor/extract_main_threaded.py) — the other pipeline + the long rules prompt
  5. [azure_blob.py](azure_blob.py) — handy CLI utilities

- Adding a new folder by hand? Edit `allowed_folders` at the bottom of the
  runner you want to use, or run the cron updater once and let it write the
  list for you.

- Onboarding a new Gemini key? Add it to `.env` and add a corresponding
  `os.getenv("GEMINI_API_KEYxx")` line to the `API_KEYS` list in every runner
  that should use it.
