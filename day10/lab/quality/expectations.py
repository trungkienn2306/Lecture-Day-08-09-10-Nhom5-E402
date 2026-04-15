"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.

Nhóm 05-E402 thêm 2 expectation mới (E7, E8):
  E7 (halt): Không có chunk nào chứa "10 ngày phép năm" trong hr_leave_policy
             (bản cũ HR 2025 — conflict với policy 2026 là 12 ngày).
  E8 (warn): Số lượng chunk per doc_id không lệch quá lớn so với expectation tối thiểu
             (phát hiện "ingest chạy nhưng thiếu doc").

Pydantic real validation (Bonus +2):
  run_pydantic_expectations() — import pydantic thật, validate từng dòng cleaned.
  Fallback sang custom nếu pydantic chưa cài.

metric_impact:
  E7: Inject chunk hr_leave_policy với text "10 ngày phép năm" → expectation FAIL halt.
      Sau clean bình thường → PASS (bản cũ bị quarantine ở cleaning_rules rule 3).
  E8: Inject CSV không có chunk sla_p1_2026 → warn "doc_id sla_p1_2026 absent".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# E8: số chunk tối thiểu mỗi doc_id kỳ vọng (warn nếu không đủ)
MIN_CHUNKS_PER_DOC: Dict[str, int] = {
    "policy_refund_v4": 1,
    "sla_p1_2026": 1,
    "it_helpdesk_faq": 1,
    "hr_leave_policy": 1,
}


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Trả về (results, should_halt).

    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    results: List[ExpectationResult] = []

    # E1: có ít nhất 1 dòng sau clean
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # E2: không doc_id rỗng
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (r.get("chunk_text") or "")
    ]
    ok3 = len(bad_refund) == 0
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            ok3,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    # E4: chunk_text đủ dài
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            ok5,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    # E6: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (r.get("chunk_text") or "")
    ]
    ok6 = len(bad_hr_annual) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            ok6,
            "halt",
            f"violations={len(bad_hr_annual)}",
        )
    )

    # E7 (Nhóm 05-E402 — HALT): chunk HR không được chứa "10 ngày phép năm" (bản 2025 conflict)
    # Ghi chú: E6 đã check, E7 là alias với severity rõ hơn để dễ đọc trong log.
    # Thêm check cross-doc: toàn bộ corpus không chứa "10 ngày phép" trong bất kỳ doc nào
    bad_stale_leave = [
        r
        for r in cleaned_rows
        if "10 ngày phép" in (r.get("chunk_text") or "")
    ]
    ok7 = len(bad_stale_leave) == 0
    results.append(
        ExpectationResult(
            "no_stale_leave_policy_any_doc",
            ok7,
            "halt",
            f"stale_leave_chunks={len(bad_stale_leave)} "
            f"doc_ids={list({r.get('doc_id') for r in bad_stale_leave})}",
        )
    )

    # E8 (Nhóm 05-E402 — WARN): kiểm tra mỗi doc_id kỳ vọng có ít nhất MIN_CHUNKS_PER_DOC chunk
    doc_counts: Dict[str, int] = {}
    for r in cleaned_rows:
        did = r.get("doc_id", "")
        doc_counts[did] = doc_counts.get(did, 0) + 1

    missing_docs = [
        did
        for did, min_cnt in MIN_CHUNKS_PER_DOC.items()
        if doc_counts.get(did, 0) < min_cnt
    ]
    ok8 = len(missing_docs) == 0
    results.append(
        ExpectationResult(
            "min_chunks_per_expected_doc",
            ok8,
            "warn",
            f"missing_or_insufficient={missing_docs} counts={doc_counts}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt


# ---------------------------------------------------------------------------
# Pydantic real validation (Bonus +2)
# ---------------------------------------------------------------------------

def run_pydantic_expectations(
    cleaned_rows: List[Dict[str, Any]],
) -> Tuple[List[ExpectationResult], bool]:
    """
    Validate cleaned rows bằng pydantic thật (Bonus +2).

    Nếu pydantic chưa cài → fallback về run_expectations() với warning.
    Trả về (results, should_halt) theo cùng interface.
    """
    try:
        from pydantic import BaseModel, field_validator, ValidationError  # type: ignore

        class CleanedChunk(BaseModel):
            chunk_id: str
            doc_id: str
            chunk_text: str
            effective_date: str
            exported_at: str

            @field_validator("chunk_id")
            @classmethod
            def chunk_id_not_empty(cls, v: str) -> str:
                if not v.strip():
                    raise ValueError("chunk_id must not be empty")
                return v

            @field_validator("doc_id")
            @classmethod
            def doc_id_not_empty(cls, v: str) -> str:
                if not v.strip():
                    raise ValueError("doc_id must not be empty")
                return v

            @field_validator("chunk_text")
            @classmethod
            def chunk_text_min_length(cls, v: str) -> str:
                if len(v.strip()) < 8:
                    raise ValueError(f"chunk_text too short: {len(v.strip())} chars (min 8)")
                return v

            @field_validator("effective_date")
            @classmethod
            def effective_date_iso(cls, v: str) -> str:
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", v.strip()):
                    raise ValueError(f"effective_date must be YYYY-MM-DD, got: {v!r}")
                return v

        errors: List[str] = []
        for i, row in enumerate(cleaned_rows):
            try:
                CleanedChunk(**{k: str(v) for k, v in row.items() if k in CleanedChunk.model_fields})
            except ValidationError as e:
                for err in e.errors():
                    errors.append(f"row[{i}] {err['loc']}: {err['msg']}")

        pydantic_ok = len(errors) == 0
        results = [
            ExpectationResult(
                name="pydantic_schema_validation",
                passed=pydantic_ok,
                severity="halt",
                detail=f"pydantic_errors={len(errors)}"
                + (f" first={errors[0]}" if errors else ""),
            )
        ]
        halt = not pydantic_ok
        return results, halt

    except ImportError:
        # pydantic not installed — fallback to custom validation
        fallback_results, fallback_halt = run_expectations(cleaned_rows)
        fallback_results.insert(
            0,
            ExpectationResult(
                name="pydantic_schema_validation",
                passed=True,
                severity="warn",
                detail="pydantic_not_installed: fallback to custom expectations",
            ),
        )
        return fallback_results, fallback_halt
