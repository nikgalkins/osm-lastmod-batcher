from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _col_to_index(letter: str) -> int:
    """
    Converts Excel-style column letter (e.g. 'A', 'B', 'G')
    to 1-based numeric index.
    """
    return ord(letter.upper()) - ord("A") + 1


def _index_to_col(index: int) -> str:
    """
    Converts 1-based numeric index to Excel-style column letter.
    """
    return chr(ord("A") + index - 1)


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    # -------------------------
    # Google Sheets
    # -------------------------
    spreadsheet_name: str
    sheet_name: str
    relation_id_col: int
    start_row: int
    gcp_service_account_file: Path

    # -------------------------
    # Overpass
    # -------------------------
    overpass_urls: List[str]
    user_agent: str
    overpass_query_timeout_s: int
    request_timeout: Tuple[int, int]  # (connect_timeout, read_timeout)

    # -------------------------
    # Batch
    # -------------------------
    batch_size: int
    recursion_depth: int
    sleep_between_batches_s: float

    # -------------------------
    # Cooldowns
    # -------------------------
    cooldown_429_min_s: float
    cooldown_429_max_s: float
    cooldown_504_min_s: float
    cooldown_504_max_s: float

    # -------------------------
    # Output sheet mapping
    # -------------------------
    output_header_range: str
    output_start_col_letter: str
    output_end_col_letter: str
    output_cols_count: int
    status_col_index_0based: int


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_settings() -> Settings:
    """
    Loads configuration from:
      1. ENV_FILE (if provided)
      2. .env in repository root (optional)
      3. system environment variables

    No secrets are committed to Git.
    """

    # Detect repo root (two levels above src/osm_lastmod/)
    base_dir = Path(__file__).resolve().parents[2]

    env_file = os.environ.get("ENV_FILE", "").strip()
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv(base_dir / ".env")

    # -----------------------------------------------------------------------
    # Google Sheets
    # -----------------------------------------------------------------------

    spreadsheet_name = os.environ.get("SPREADSHEET_NAME", "OSM Routes")
    sheet_name = os.environ.get("SHEET_NAME", "relation_ids")

    relation_id_col = int(os.environ.get("RELATION_ID_COL", "1"))
    start_row = int(os.environ.get("START_ROW", "2"))

    key_path_raw = os.environ.get("GCP_SERVICE_ACCOUNT_FILE", "").strip()
    if not key_path_raw:
        raise RuntimeError(
            "GCP_SERVICE_ACCOUNT_FILE is not set. "
            "Provide absolute path to service account JSON."
        )

    gcp_service_account_file = Path(key_path_raw).expanduser().resolve()

    if not gcp_service_account_file.exists():
        raise RuntimeError(
            f"GCP service account file not found: {gcp_service_account_file}"
        )

    # -----------------------------------------------------------------------
    # Overpass
    # -----------------------------------------------------------------------

    primary_url = os.environ.get(
        "OVERPASS_URL",
        "https://overpass-api.de/api/interpreter",
    )

    overpass_urls = [
        primary_url,
        "https://overpass.kumi.systems/api/interpreter",
    ]

    user_agent = os.environ.get(
        "OVERPASS_USER_AGENT",
        "osm-lastmod-batcher/1.0 (contact: team@example.com)",
    )

    overpass_query_timeout_s = int(
        os.environ.get("OVERPASS_QUERY_TIMEOUT_S", "300")
    )

    request_timeout = (10, 240)

    # -----------------------------------------------------------------------
    # Batch
    # -----------------------------------------------------------------------

    batch_size = int(os.environ.get("BATCH_SIZE", "20"))
    recursion_depth = int(os.environ.get("RECURSION_DEPTH", "1"))
    sleep_between_batches_s = float(
        os.environ.get("SLEEP_BETWEEN_BATCHES_S", "8.0")
    )

    # -----------------------------------------------------------------------
    # Cooldowns
    # -----------------------------------------------------------------------

    cooldown_429_min_s = float(os.environ.get("COOLDOWN_429_MIN_S", "30"))
    cooldown_429_max_s = float(os.environ.get("COOLDOWN_429_MAX_S", "60"))
    cooldown_504_min_s = float(os.environ.get("COOLDOWN_504_MIN_S", "1"))
    cooldown_504_max_s = float(os.environ.get("COOLDOWN_504_MAX_S", "3"))

    # -----------------------------------------------------------------------
    # Output mapping
    # -----------------------------------------------------------------------

    output_header_range = os.environ.get("OUTPUT_HEADER_RANGE", "B1:G1")

    output_start_col_letter = os.environ.get("OUTPUT_START_COL", "B")
    output_cols_count = int(os.environ.get("OUTPUT_COLS_COUNT", "6"))

    start_index = _col_to_index(output_start_col_letter)
    end_index = start_index + output_cols_count - 1
    output_end_col_letter = _index_to_col(end_index)

    status_col_index_0based = int(
        os.environ.get("STATUS_COL_INDEX_0BASED", "6")
    )

    # -----------------------------------------------------------------------
    # Return settings
    # -----------------------------------------------------------------------

    return Settings(
        spreadsheet_name=spreadsheet_name,
        sheet_name=sheet_name,
        relation_id_col=relation_id_col,
        start_row=start_row,
        gcp_service_account_file=gcp_service_account_file,
        overpass_urls=overpass_urls,
        user_agent=user_agent,
        overpass_query_timeout_s=overpass_query_timeout_s,
        request_timeout=request_timeout,
        batch_size=batch_size,
        recursion_depth=recursion_depth,
        sleep_between_batches_s=sleep_between_batches_s,
        cooldown_429_min_s=cooldown_429_min_s,
        cooldown_429_max_s=cooldown_429_max_s,
        cooldown_504_min_s=cooldown_504_min_s,
        cooldown_504_max_s=cooldown_504_max_s,
        output_header_range=output_header_range,
        output_start_col_letter=output_start_col_letter,
        output_end_col_letter=output_end_col_letter,
        output_cols_count=output_cols_count,
        status_col_index_0based=status_col_index_0based,
    )
