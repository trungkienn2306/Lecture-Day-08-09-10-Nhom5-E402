# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Policy Engine Export | CSV (Raw Ingest) | Sai cửa sổ hoàn tiền (14 ngày thay vì 7) | `expectation[refund_no_stale_14d_window]` |
| HR Portal | CSV (Raw Ingest) | Phiên bản chính sách nghỉ phép cũ (< 2026) | `quarantine_reason: stale_hr_policy_effective_date` |
| IT Helpdesk FAQ | CSV (Raw Ingest) | Định dạng ngày không đồng nhất | `quarantine_reason: invalid_effective_date_format` |
| System Specs (SLA) | CSV (Raw Ingest) | doc_id không nằm trong allowlist | `quarantine_reason: unknown_doc_id` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Hash ổn định từ doc_id + text + seq |
| doc_id | string | Có | Khóa định danh tài liệu (vd: policy_refund_v4) |
| chunk_text | string | Có | Nội dung văn bản (min 8 chars) |
| effective_date | date | Có | Ngày hiệu lực (ISO: YYYY-MM-DD) |
| exported_at | datetime | Có | Thời điểm export dữ liệu từ hệ nguồn |

---

## 3. Quy tắc quarantine vs drop

- **Quarantine**: Bản ghi được đẩy vào `artifacts/quarantine/` nếu vi phạm:
    - `unknown_doc_id`: doc_id lạ.
    - `invalid_effective_date_format`: Không parse được ngày.
    - `stale_hr_policy_effective_date`: Chính sách HR cũ.
    - `missing_chunk_text`: Thiếu nội dung.
    - `duplicate_chunk_text`: Trùng lặp nội dung (Drop bản sau, giữ bản đầu).
- **Halt**: Pipeline sẽ dừng (halt) nếu không đạt expectation mức "halt" (vd: không còn bản ghi nào sau clean).

---

## 4. Phiên bản & canonical

- **Source of truth**: Các file `.txt` trong `data/docs/`.
- **Version Control**: Sử dụng `effective_date` và `run_id` để theo dõi phiên bản dữ liệu được ingest.
