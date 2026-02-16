# OSM Last Modified Batcher (Overpass + Google Sheets)

Fetches `last_modified` timestamps for OSM relations and their direct members using Overpass API,
writes results into a Google Sheet in batches to reduce API pressure and speed up processing.

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

### 3) Install and run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt

python -m osm_lastmod.main
```
Notes

- Overpass may respond with 429/504 under load; the script retries and can fall back to another instance.
- BATCH_SIZE and SLEEP_BETWEEN_BATCHES_S control load.

