"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Nhóm 05-E402 thêm 3 rule mới (Rule 7–9):
  Rule 7: Loại chunk_text chứa BOM hoặc ký tự thay thế Unicode (encoding corruption).
  Rule 8: Quarantine chunk_text quá ngắn (< MIN_CHUNK_CHARS) — không đủ ngữ nghĩa khi embed.
  Rule 9: Quarantine nếu effective_date nằm trong tương lai xa (> MAX_FUTURE_DAYS từ ngày export).

metric_impact (xem reports/group_report.md § 2a):
  Rule 7: Inject chunk "BOM\ufefftest" → quarantine tăng 1; không inject → quarantine giữ nguyên.
  Rule 8: Inject chunk_text="hi" (2 ký tự) → quarantine tăng 1 so với baseline.
  Rule 9: Inject effective_date="2099-01-01" → quarantine tăng 1.
"""

from __future__ import annotations

import csv
import hashlib
import os
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

# Rule 8: độ dài tối thiểu chunk (ký tự) để embed có ý nghĩa
# Đọc từ env var để versioning không cần sửa code (Distinction criterion d)
MIN_CHUNK_CHARS: int = int(os.environ.get("MIN_CHUNK_CHARS", "20"))

# Rule 9: ngưỡng tương lai tối đa (ngày) so với ngày export hoặc hôm nay
MAX_FUTURE_DAYS: int = int(os.environ.get("MAX_FUTURE_DAYS", "365"))

# Rule 3: ngày hiệu lực tối thiểu cho HR leave policy
# Đọc từ env var — thay đổi mà không cần sửa code (Distinction criterion d)
HR_LEAVE_MIN_EFFECTIVE_DATE: str = os.environ.get("HR_LEAVE_MIN_EFFECTIVE_DATE", "2026-01-01")

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")

# Rule 7: BOM U+FEFF và ký tự thay thế U+FFFD (encoding corruption)
_ENCODING_CORRUPTION = re.compile(r"[\ufeff\ufffd]")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _has_encoding_corruption(text: str) -> bool:
    """Rule 7: phát hiện BOM hoặc ký tự thay thế Unicode trong chunk_text."""
    return bool(_ENCODING_CORRUPTION.search(text))


def _is_future_date(iso_date: str, max_future_days: int = MAX_FUTURE_DAYS) -> bool:
    """Rule 9: kiểm tra effective_date quá xa trong tương lai."""
    try:
        d = date.fromisoformat(iso_date)
        return d > date.today() + timedelta(days=max_future_days)
    except (ValueError, TypeError):
        return False


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.

    Nhóm 05-E402 (Rule 7–9):
    7) Quarantine: chunk_text chứa BOM hoặc ký tự thay thế Unicode (encoding corruption).
    8) Quarantine: chunk_text quá ngắn sau trim (< MIN_CHUNK_CHARS) — không đủ ngữ nghĩa.
    9) Quarantine: effective_date nằm quá xa trong tương lai (> MAX_FUTURE_DAYS kể từ hôm nay).
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        # Rule 1: allowlist
        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        # Rule 7: encoding corruption (BOM / replacement char) — trước khi parse date
        if _has_encoding_corruption(text):
            quarantine.append({**raw, "reason": "encoding_corruption_in_chunk_text"})
            continue

        # Rule 2: date parse
        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        # Rule 3: HR stale version — cutoff từ env var (Distinction criterion d)
        if doc_id == "hr_leave_policy" and eff_norm < HR_LEAVE_MIN_EFFECTIVE_DATE:
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        # Rule 9: effective_date quá xa tương lai
        if _is_future_date(eff_norm):
            quarantine.append(
                {
                    **raw,
                    "reason": "future_effective_date_exceeds_threshold",
                    "effective_date_normalized": eff_norm,
                    "max_future_days": MAX_FUTURE_DAYS,
                }
            )
            continue

        # Rule 4: chunk_text rỗng
        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # Rule 8: chunk_text quá ngắn
        if len(text.strip()) < MIN_CHUNK_CHARS:
            quarantine.append(
                {
                    **raw,
                    "reason": "chunk_text_too_short",
                    "chunk_len": len(text.strip()),
                    "min_required": MIN_CHUNK_CHARS,
                }
            )
            continue

        # Rule 5: dedupe
        key = _norm_text(text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        # Rule 6: fix stale refund
        fixed_text = text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at or "",
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
