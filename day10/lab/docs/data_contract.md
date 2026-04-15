# Data Contract — Lab Day 10
## Nhóm 05-E402 · Phiên bản 1.1

> Đồng bộ với `contracts/data_contract.yaml` (nguồn chính thống).

---

## 1. Nguồn dữ liệu (Source Map)

| Nguồn | doc_id | Phương thức ingest | Failure mode chính | Metric / Alert |
|-------|--------|-------------------|-------------------|----------------|
| `data/docs/policy_refund_v4.txt` | `policy_refund_v4` | CSV export (`data/raw/policy_export_dirty.csv`) | Stale refund window "14 ngày" thay vì "7 ngày" | E3 `refund_no_stale_14d_window` (halt), Rule 6 fix tự động |
| `data/docs/sla_p1_2026.txt` | `sla_p1_2026` | CSV export | Missing chunk trong export | E8 `min_chunks_per_expected_doc` (warn) |
| `data/docs/it_helpdesk_faq.txt` | `it_helpdesk_faq` | CSV export | Encoding corruption (BOM) | Rule 7 quarantine + E7 (halt) |
| `data/docs/hr_leave_policy.txt` | `hr_leave_policy` | CSV export | Bản 2025 stale (10 ngày phép) vẫn trong export | Rule 3 quarantine + E6/E7 (halt) |

**Tổng: 4 nguồn canonical**, tất cả qua cùng 1 file raw CSV export.

---

## 2. Schema Cleaned

| Cột | Kiểu | Bắt buộc | Ràng buộc | Ghi chú |
|-----|------|----------|-----------|---------|
| `chunk_id` | string | ✅ | sha256 hex 16 ký tự | `sha256(doc_id\|chunk_text\|seq)[:16]` — stable across reruns |
| `doc_id` | string | ✅ | Phải trong allowlist 4 doc_id | Reject unknown doc_id → quarantine |
| `chunk_text` | string | ✅ | min_length=20, no BOM, no U+FFFD | Pydantic + Rule 7/8 kiểm tra |
| `effective_date` | date | ✅ | Format YYYY-MM-DD, không quá xa tương lai | Parse từ DD/MM/YYYY hoặc YYYY-MM-DD |
| `exported_at` | datetime | ✅ | ISO 8601 | Dùng để tính freshness `latest_exported_at` |

---

## 3. Quy tắc Quarantine vs Drop

### Quarantine (ghi vào `artifacts/quarantine/*.csv`)
Record bị flag nhưng **giữ lại bằng chứng** để audit:
- `unknown_doc_id` — doc_id không trong allowlist
- `missing_effective_date` — trường trống
- `invalid_effective_date_format` — không parse được
- `stale_hr_policy_effective_date` — HR bản cũ < 2026-01-01
- `future_effective_date_exceeds_threshold` — tương lai > 365 ngày
- `missing_chunk_text` — chunk_text rỗng
- `chunk_text_too_short` — < 20 ký tự
- `encoding_corruption_in_chunk_text` — BOM hoặc U+FFFD
- `duplicate_chunk_text` — trùng nội dung

### Drop (không ghi vào đâu)
Không có — tất cả record bị loại đều vào quarantine CSV để audit.

### Approve để merge lại
1. Mở `artifacts/quarantine/*.csv`
2. Filter theo `reason`
3. Sửa nguồn (fix raw export hoặc cập nhật allowlist)
4. Re-run `python etl_pipeline.py run` với run_id mới

---

## 4. Phiên bản & Canonical

| Tài liệu | Source of truth | Version hiện tại | Cutoff rule |
|---------|----------------|-----------------|-------------|
| Refund policy | `data/docs/policy_refund_v4.txt` | v4 (2026) | 7 ngày làm việc |
| HR Leave policy | `data/docs/hr_leave_policy.txt` | 2026-01-01+ | Min 12 ngày phép năm |
| SLA P1 | `data/docs/sla_p1_2026.txt` | 2026 | First response 15 phút |
| IT FAQ | `data/docs/it_helpdesk_faq.txt` | Current | Lockout sau 5 lần |

### Rule Versioning (Distinction criterion d)
Thay vì hardcode cutoff date trong code, nhóm đọc từ env var:
```python
# cleaning_rules.py — Rule 3
import os
HR_LEAVE_MIN_DATE = os.environ.get("HR_LEAVE_MIN_EFFECTIVE_DATE", "2026-01-01")
```

Thay đổi cutoff → chỉ cần update `.env` hoặc `contracts/data_contract.yaml`, không sửa code.

---

## 5. Freshness SLA (2 Boundaries)

| Boundary | Field trong manifest | Ý nghĩa | SLA |
|---------|---------------------|---------|-----|
| Ingest | `ingest_boundary_at` | Sau khi đọc raw CSV xong | 24h |
| Publish | `publish_boundary_at` | Sau khi embed vào Chroma xong | 24h |

SLA mặc định 24h, override bằng env var `FRESHNESS_SLA_HOURS`.

---

## 6. Expectation Summary

| ID | Severity | Mô tả | Nhóm thêm? |
|----|---------|-------|-----------|
| `min_one_row` | halt | Ít nhất 1 row sau clean | baseline |
| `no_empty_doc_id` | halt | Không doc_id rỗng | baseline |
| `refund_no_stale_14d_window` | halt | Refund không chứa "14 ngày làm việc" | baseline |
| `chunk_min_length_8` | warn | chunk_text ≥ 8 chars | baseline |
| `effective_date_iso_yyyy_mm_dd` | halt | Date format YYYY-MM-DD | baseline |
| `hr_leave_no_stale_10d_annual` | halt | HR không "10 ngày phép năm" | baseline |
| `no_stale_leave_policy_any_doc` | **halt** | Cross-doc: toàn corpus không "10 ngày phép" | **Nhóm (E7)** |
| `min_chunks_per_expected_doc` | **warn** | Mỗi doc_id có ≥1 chunk | **Nhóm (E8)** |
| `pydantic_schema_validation` | **halt** | Pydantic validate 5 fields | **Nhóm (Bonus +2)** |
