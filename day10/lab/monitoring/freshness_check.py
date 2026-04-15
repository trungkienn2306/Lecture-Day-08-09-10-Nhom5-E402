"""
Kiểm tra freshness từ manifest pipeline — hỗ trợ 2 boundaries (ingest + publish).

Bonus +1: log cả ingest_boundary_at và publish_boundary_at trong manifest,
so sánh từng boundary với SLA riêng.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def check_manifest_freshness(
    manifest_path: Path,
    *,
    sla_hours: float = 24.0,
    now: datetime | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Đo freshness dựa trên 1 boundary (publish) — backward compatible.

    Trả về ("PASS" | "WARN" | "FAIL", detail dict).
    Đọc trường `latest_exported_at` hoặc `publish_boundary_at` hoặc `run_timestamp`.
    """
    now = now or datetime.now(timezone.utc)
    if not manifest_path.is_file():
        return "FAIL", {"reason": "manifest_missing", "path": str(manifest_path)}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Ưu tiên publish_boundary_at (2-boundary), fallback về latest_exported_at
    ts_raw = (
        data.get("publish_boundary_at")
        or data.get("latest_exported_at")
        or data.get("run_timestamp")
    )
    dt = parse_iso(str(ts_raw)) if ts_raw else None
    if dt is None:
        return "WARN", {"reason": "no_timestamp_in_manifest", "manifest": data}

    age_hours = (now - dt).total_seconds() / 3600.0
    detail = {
        "boundary": "publish",
        "latest_exported_at": ts_raw,
        "age_hours": round(age_hours, 3),
        "sla_hours": sla_hours,
    }
    if age_hours <= sla_hours:
        return "PASS", detail
    return "FAIL", {**detail, "reason": "freshness_sla_exceeded"}


def check_two_boundary_freshness(
    manifest_path: Path,
    *,
    ingest_sla_hours: float = 24.0,
    publish_sla_hours: float = 24.0,
    now: datetime | None = None,
) -> Dict[str, Any]:
    """
    Đo freshness ở CẢ 2 boundaries: ingest + publish (Bonus +1).

    manifest phải có:
      - ingest_boundary_at: UTC ISO timestamp sau khi đọc raw CSV xong
      - publish_boundary_at: UTC ISO timestamp sau khi embed vào Chroma xong

    Trả về dict với:
      - ingest: {status, age_hours, sla_hours, timestamp}
      - publish: {status, age_hours, sla_hours, timestamp}
      - overall: "PASS" nếu cả 2 PASS, "WARN" nếu thiếu timestamp, "FAIL" nếu có SLA vi phạm
    """
    now = now or datetime.now(timezone.utc)

    if not manifest_path.is_file():
        return {
            "overall": "FAIL",
            "reason": "manifest_missing",
            "path": str(manifest_path),
        }

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))

    def _check_boundary(ts_key: str, sla: float) -> Dict[str, Any]:
        ts_raw = data.get(ts_key)
        if not ts_raw:
            return {"status": "WARN", "reason": f"missing_{ts_key}", "sla_hours": sla}
        dt = parse_iso(str(ts_raw))
        if dt is None:
            return {
                "status": "WARN",
                "reason": f"unparseable_{ts_key}",
                "raw": ts_raw,
                "sla_hours": sla,
            }
        age_hours = (now - dt).total_seconds() / 3600.0
        status = "PASS" if age_hours <= sla else "FAIL"
        result = {
            "status": status,
            "timestamp": ts_raw,
            "age_hours": round(age_hours, 3),
            "sla_hours": sla,
        }
        if status == "FAIL":
            result["reason"] = "freshness_sla_exceeded"
        return result

    ingest_result = _check_boundary("ingest_boundary_at", ingest_sla_hours)
    publish_result = _check_boundary("publish_boundary_at", publish_sla_hours)

    statuses = {ingest_result["status"], publish_result["status"]}
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "WARN" in statuses:
        overall = "WARN"
    else:
        overall = "PASS"

    return {
        "overall": overall,
        "run_id": data.get("run_id", ""),
        "ingest": ingest_result,
        "publish": publish_result,
    }
