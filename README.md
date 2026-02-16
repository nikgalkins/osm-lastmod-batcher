# OSM Last Modified Batcher (Overpass API + Google Sheets)

Production-ready batch processor that fetches last_modified timestamps for OSM relations and their direct members via the Overpass API and writes structured results into Google Sheets.

Designed for:

- Controlled API load
- Large relation lists
- Re-runnable batch execution
- Clean separation of configuration and code

## What it does

For each relation_id in Column A:

- Fetches:
  - relation timestamp
  - max timestamp among direct members
- Computes:
  - last_modified_final = max(relation_ts, members_ts)
- Writes results to the sheet in batch mode
- Skips rows already marked as OK

## Sheet format

- Column A: `relation_id`
- Script writes to columns B..G:
  - `osm_url`
  - `relation_last_modified`
  - `members_last_modified`
  - `last_modified_final`
  - `members_count`
  - `status`

Rows with `status` starting with `OK` are skipped on next runs.

## Architecture

```bash
src/osm_lastmod/
│
├── main.py        # Batch orchestration
├── settings.py    # Environment-based configuration
├── overpass.py    # Overpass client (retry + fallback logic)
├── sheets.py      # Google Sheets integration
├── utils.py       # Shared helpers
└── __main__.py    # CLI entry point
```

Key design goals:

- Explicit configuration via environment variables
- No secrets committed
- Resilient Overpass communication
- Controlled batch size and pacing

## Setup

### 1) Create Google Cloud service account

1. Create a new GCP project.
2. Enable APIs:
   - Google Sheets API
   - Google Drive API
3. Create a Service Account.
4. Create a JSON key and download it locally.
5. Share the target Google Sheet with the service account email (Editor access).

### 2) Configure environment

Copy example env file:

```bash
cp .env.example .env
```

Edit .env and set at minimum:

- GCP_SERVICE_ACCOUNT_FILE (absolute path to JSON key)
- SPREADSHEET_NAME
- SHEET_NAME

### 3) Installation
#### Option A — virtual environment
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```
Run:
```bash
python -m osm_lastmod
```

#### Option B — editable install (recommended)
```bash
pip install -e .
python -m osm_lastmod
```

Performance & Load Control

- Batch processing reduces Overpass pressure
- Automatic retry with exponential backoff
- Fallback to secondary Overpass instance
- Rows marked OK are skipped on future runs
- Batch splitting on failure (binary fallback)

Key parameters:

| Variable                  | Purpose                         |
| ------------------------- | ------------------------------- |
| `BATCH_SIZE`              | Relations per Overpass query    |
| `SLEEP_BETWEEN_BATCHES_S` | Delay between batches           |
| `RECURSION_DEPTH`         | Overpass member expansion depth |
| `COOLDOWN_*`              | 429/504 handling                |

## Logging
Each batch logs:
- batch_size
- used_host
- total_elements
- elapsed_s
This allows monitoring API pressure and response size.

## Security
- Service account JSON must NOT be committed
- .env is ignored by git
- .env.example is safe template only
- No hardcoded credentials in repository

## Requirements
- Python 3.10+
- Internet access to:
  - Overpass API
  - Google Sheets API

## License
MIT License