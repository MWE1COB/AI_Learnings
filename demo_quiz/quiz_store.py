"""Excel-backed storage for demo quiz attempts (admin dashboard + export)."""
import os
import threading
from datetime import datetime
from openpyxl import Workbook, load_workbook

EXCEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_results.xlsx")

HEADERS = ["Name", "NTID", "Topic", "Level", "Score", "Total Questions",
           "Percentage", "Duration (sec)", "Submitted At"]

_lock = threading.Lock()


def _ensure_workbook():
    if not os.path.exists(EXCEL_PATH):
        wb = Workbook()
        ws = wb.active
        ws.title = "Results"
        ws.append(HEADERS)
        wb.save(EXCEL_PATH)
        return

    # Migrate older workbooks saved with a "Phone" column to the current schema.
    with _lock:
        wb = load_workbook(EXCEL_PATH)
        ws = wb["Results"]
        header = [c.value for c in ws[1]]
        if header == HEADERS:
            return
        if "Phone" in header:
            phone_idx = header.index("Phone")
            rows = list(ws.iter_rows(min_row=2, values_only=True))
            ws.delete_rows(1, ws.max_row)
            ws.append(HEADERS)
            for row in rows:
                ws.append([v for i, v in enumerate(row) if i != phone_idx])
            wb.save(EXCEL_PATH)


def save_attempt(name, ntid, topic, level_name, score, total, duration_sec):
    """Append a completed quiz attempt to the Excel workbook. Returns the saved record."""
    _ensure_workbook()
    percentage = round((score / total) * 100, 1) if total else 0
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [name, ntid, topic, level_name, score, total, percentage, duration_sec, submitted_at]

    with _lock:
        wb = load_workbook(EXCEL_PATH)
        ws = wb["Results"]
        ws.append(row)
        wb.save(EXCEL_PATH)

    return dict(zip(
        ["name", "ntid", "topic", "level", "score", "total", "percentage", "duration_sec", "submitted_at"],
        row,
    ))


def get_all_attempts():
    """Return all saved attempts (most recent first) for the admin dashboard."""
    _ensure_workbook()
    with _lock:
        wb = load_workbook(EXCEL_PATH)
        ws = wb["Results"]
        rows = list(ws.iter_rows(min_row=2, values_only=True))

    keys = ["name", "ntid", "topic", "level", "score", "total", "percentage", "duration_sec", "submitted_at"]
    attempts = [dict(zip(keys, row)) for row in rows if row and row[0]]
    attempts.reverse()
    return attempts
