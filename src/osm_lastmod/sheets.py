from __future__ import annotations

from typing import Any, List, Tuple

import gspread
from oauth2client.service_account import ServiceAccountCredentials


SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def open_sheet(service_account_file: str, spreadsheet_name: str, sheet_name: str) -> gspread.Worksheet:
    creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_file, SCOPE)
    client = gspread.authorize(creds)
    spreadsheet = client.open(spreadsheet_name)
    return spreadsheet.worksheet(sheet_name)


def write_headers(sheet: gspread.Worksheet, header_range: str, headers: List[str]) -> None:
    sheet.update(range_name=header_range, values=[headers])


def group_contiguous_updates(
    updates: List[Tuple[int, List[Any]]]
) -> List[Tuple[int, int, List[List[Any]]]]:
    if not updates:
        return []

    updates_sorted = sorted(updates, key=lambda x: x[0])
    groups: List[Tuple[int, int, List[List[Any]]]] = []

    start_row = updates_sorted[0][0]
    prev_row = start_row
    matrix = [updates_sorted[0][1]]

    for row_num, vals in updates_sorted[1:]:
        if row_num == prev_row + 1:
            matrix.append(vals)
            prev_row = row_num
        else:
            groups.append((start_row, prev_row, matrix))
            start_row = row_num
            prev_row = row_num
            matrix = [vals]

    groups.append((start_row, prev_row, matrix))
    return groups
