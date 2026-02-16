from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from .overpass import OverpassClient
from .settings import load_settings
from .sheets import group_contiguous_updates, open_sheet, write_headers
from .utils import chunked, fmt_dt, host_from_url, iso_to_dt, safe_int


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


HEADERS = [
    "osm_url",
    "relation_last_modified",
    "members_last_modified",
    "last_modified_final",
    "members_count",
    "status",
]


def index_elements(overpass_json: Dict[str, Any]) -> Tuple[Dict[int, Dict[str, Any]], Dict[Tuple[str, int], Any], int]:
    elements = overpass_json.get("elements", [])
    relations_by_id: Dict[int, Dict[str, Any]] = {}
    ts_by_key: Dict[Tuple[str, int], Any] = {}

    for el in elements:
        el_type = el.get("type")
        el_id = el.get("id")
        ts = el.get("timestamp")

        if el_type and isinstance(el_id, int) and ts:
            ts_by_key[(el_type, el_id)] = iso_to_dt(ts)

        if el_type == "relation" and isinstance(el_id, int):
            relations_by_id[el_id] = el

    return relations_by_id, ts_by_key, len(elements)


def compute_relation_lastmods(
    rel_id: int,
    relations_by_id: Dict[int, Dict[str, Any]],
    ts_by_key: Dict[Tuple[str, int], Any],
) -> Tuple[Optional[Any], Optional[Any], Optional[Any], int]:
    rel_el = relations_by_id.get(rel_id)
    if not rel_el:
        return None, None, None, 0

    relation_ts = ts_by_key.get(("relation", rel_id))

    members = rel_el.get("members") or []
    members_count = len(members)

    members_max_ts = None
    for m in members:
        m_type = m.get("type")
        m_ref = m.get("ref")
        if not m_type or not isinstance(m_ref, int):
            continue
        dt = ts_by_key.get((m_type, m_ref))
        if dt:
            members_max_ts = dt if members_max_ts is None else max(members_max_ts, dt)

    if relation_ts and members_max_ts:
        final_ts = max(relation_ts, members_max_ts)
    else:
        final_ts = relation_ts or members_max_ts

    return relation_ts, members_max_ts, final_ts, members_count


def process_batch(
    sess: requests.Session,
    client: OverpassClient,
    batch_targets: List[Tuple[int, int]],
    query_timeout_s: int,
    recursion_depth: int,
) -> Tuple[List[Tuple[int, List[Any]]], str, int, float]:
    ids = [rel_id for _, rel_id in batch_targets]
    query = client.build_query_batch(ids, query_timeout_s, recursion_depth)

    t0 = time.time()
    data, used_url = client.post(sess, query=query)
    elapsed_s = time.time() - t0

    relations_by_id, ts_by_key, total_elements = index_elements(data)
    used_host = host_from_url(used_url)

    updates: List[Tuple[int, List[Any]]] = []
    for row_num, rel_id in batch_targets:
        osm_url = f"https://www.openstreetmap.org/relation/{rel_id}"
        rel_ts, mem_ts, final_ts, members_count = compute_relation_lastmods(rel_id, relations_by_id, ts_by_key)

        if rel_ts is None and mem_ts is None:
            vals = [osm_url, "", "", "", "", f"ERROR: missing in response ({used_host})"]
        else:
            vals = [
                osm_url,
                fmt_dt(rel_ts),
                fmt_dt(mem_ts),
                fmt_dt(final_ts),
                str(members_count),
                f"OK ({used_host})",
            ]
        updates.append((row_num, vals))

    return updates, used_host, total_elements, elapsed_s


def process_batch_with_split(
    sess: requests.Session,
    client: OverpassClient,
    batch_targets: List[Tuple[int, int]],
    query_timeout_s: int,
    recursion_depth: int,
) -> List[Tuple[int, List[Any]]]:
    try:
        updates, used_host, total_elements, elapsed_s = process_batch(
            sess, client, batch_targets, query_timeout_s, recursion_depth
        )
        logging.info(
            "Batch OK: batch_size=%d, used_host=%s, total_elements=%d, elapsed_s=%.1f, rows %d..%d",
            len(batch_targets),
            used_host,
            total_elements,
            elapsed_s,
            batch_targets[0][0],
            batch_targets[-1][0],
        )
        return updates

    except Exception as e:
        if len(batch_targets) == 1:
            row_num, rel_id = batch_targets[0]
            osm_url = f"https://www.openstreetmap.org/relation/{rel_id}"
            logging.error("Single relation failed (row %d, id %d): %s", row_num, rel_id, e)
            return [(row_num, [osm_url, "", "", "", "", f"ERROR: {str(e)[:120]}"])]

        mid = len(batch_targets) // 2
        left = batch_targets[:mid]
        right = batch_targets[mid:]
        logging.warning(
            "Batch failed (size=%d). Split into %d + %d. Reason: %s",
            len(batch_targets),
            len(left),
            len(right),
            e,
        )
        out: List[Tuple[int, List[Any]]] = []
        out.extend(process_batch_with_split(sess, client, left, query_timeout_s, recursion_depth))
        out.extend(process_batch_with_split(sess, client, right, query_timeout_s, recursion_depth))
        return out


def main() -> None:
    s = load_settings()

    sheet = open_sheet(
        service_account_file=str(s.gcp_service_account_file),
        spreadsheet_name=s.spreadsheet_name,
        sheet_name=s.sheet_name,
    )

    try:
        write_headers(sheet, s.output_header_range, HEADERS)
    except Exception as e:
        logging.warning("Failed to write headers: %s", e)

    rows = sheet.get_all_values()

    targets: List[Tuple[int, int]] = []
    for row_num, row in enumerate(rows[s.start_row - 1:], start=s.start_row):
        rel_raw = row[s.relation_id_col - 1] if len(row) >= s.relation_id_col else ""
        rel_id = safe_int(rel_raw)
        if not rel_id:
            continue

        status_val = row[s.status_col_index_0based].strip() if len(row) > s.status_col_index_0based else ""
        if status_val.upper().startswith("OK"):
            continue

        targets.append((row_num, rel_id))

    logging.info("Loaded %d relation ids to process from '%s' column A.", len(targets), s.sheet_name)
    if not targets:
        logging.info("Nothing to do.")
        return

    client = OverpassClient(
        urls=s.overpass_urls,
        user_agent=s.user_agent,
        request_timeout=s.request_timeout,
        cooldown_429_min_s=s.cooldown_429_min_s,
        cooldown_429_max_s=s.cooldown_429_max_s,
        cooldown_504_min_s=s.cooldown_504_min_s,
        cooldown_504_max_s=s.cooldown_504_max_s,
    )

    sess = requests.Session()

    total_done = 0
    total_targets = len(targets)

    for batch in chunked(targets, s.batch_size):
        logging.info("Processing batch: size=%d rows %d..%d", len(batch), batch[0][0], batch[-1][0])

        updates = process_batch_with_split(
            sess=sess,
            client=client,
            batch_targets=batch,
            query_timeout_s=s.overpass_query_timeout_s,
            recursion_depth=s.recursion_depth,
        )

        groups = group_contiguous_updates(updates)
        for start_row, end_row, matrix in groups:
            range_name = (
                f"{s.output_start_col_letter}{start_row}:"
                f"{s.output_end_col_letter}{end_row}"
            )
            try:
                sheet.update(range_name=range_name, values=matrix)
                logging.info("Sheet updated: %s (%d rows)", range_name, len(matrix))
            except Exception as e:
                logging.error("Failed to update sheet range %s: %s", range_name, e)

        total_done += len(batch)
        logging.info("Progress: %d/%d done. Sleep %.1fs", total_done, total_targets, s.sleep_between_batches_s)
        time.sleep(s.sleep_between_batches_s)

    logging.info("Done.")


if __name__ == "__main__":
    main()
