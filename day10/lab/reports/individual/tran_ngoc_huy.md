# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Ngọc Huy  
**Vai trò:** Cleaning & Quality Owner (Sprint 2)  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `transform/cleaning_rules.py` — thêm Rule 7, 8, 9 vào hàm `clean_rows()`; viết hai hàm helper `_has_encoding_corruption()` và `_is_future_date()`; đọc ngưỡng `MIN_CHUNK_CHARS`, `MAX_FUTURE_DAYS`, `HR_LEAVE_MIN_EFFECTIVE_DATE` từ biến môi trường thay vì hard-code.
- `quality/expectations.py` — thêm E7 (`no_stale_leave_policy_any_doc`, severity `halt`) và E8 (`min_chunks_per_expected_doc`, severity `warn`) vào hàm `run_expectations()`; triển khai `run_pydantic_expectations()` để validate schema cleaned bằng pydantic thật (Bonus +2).

**Kết nối với thành viên khác:**

- **Bùi Thế Công (Sprint 1 — Ingestion Owner):** phụ trách đọc file raw CSV (`load_raw_csv`) và cấu hình `etl_pipeline.py`; output cleaned của tôi phụ thuộc vào đúng schema raw mà Cong đã thiết lập.
- **Nông Trung Kiên (Sprint 3, 4 — Embed & Monitoring Owner):** nhận `cleaned_*.csv` và kết quả expectation từ tôi để embed vào Chroma và chạy freshness check; nếu expectation của tôi halt, Kiên không embed được.

**Bằng chứng:**

Commit `d178bd3` trên nhánh `feat/day10-sprint2`: `feat: finish sprint 2, expectations and cleaning_rules logic`. Docstring mô tả Rule 7–9 và metric_impact nằm đầu file `cleaning_rules.py`; docstring E7–E8 nằm đầu file `expectations.py`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Quyết định: phân loại severity `halt` vs `warn` cho từng expectation, và đọc ngưỡng từ biến môi trường thay vì hard-code.**

Khi thêm E7 và E8, tôi phải quyết định expectation nào nên dừng pipeline (`halt`) và expectation nào chỉ cảnh báo (`warn`). E7 kiểm tra corpus còn chunk chứa "10 ngày phép" — nếu còn sót, agent sẽ trả lời sai nghiệp vụ ngay lập tức, nên tôi đặt `halt` để buộc pipeline dừng trước khi embed. E8 kiểm tra mỗi `doc_id` kỳ vọng có ít nhất 1 chunk; nếu thiếu doc có thể là lỗi ingest tạm thời chứ chưa chắc data sai, nên đặt `warn` để pipeline vẫn chạy nhưng log rõ cảnh báo.

Ngoài ra, các ngưỡng số như `MIN_CHUNK_CHARS`, `MAX_FUTURE_DAYS`, `HR_LEAVE_MIN_EFFECTIVE_DATE` được đọc từ biến môi trường thay vì ghi cứng trong code. Lý do: nếu policy thay đổi ngưỡng (ví dụ SLA mới cho phép chunk ngắn hơn), team chỉ cần sửa file `.env` mà không cần sửa và re-test code, đồng thời inject thử nghiệm cũng dễ hơn khi chạy với giá trị khác nhau giữa các lần test.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Anomaly: ngày định dạng `DD/MM/YYYY` làm expectation E5 halt nếu Rule 2 chạy sau expectation.**

**Triệu chứng:** Khi kiểm tra file `data/raw/policy_export_dirty.csv`, row 10 (`it_helpdesk_faq`) có trường `effective_date="01/02/2026"` — không phải ISO `YYYY-MM-DD`. Trong lần thử nghiệm đầu, tôi chạy expectation E5 (`effective_date_iso_yyyy_mm_dd`, severity `halt`) trên dữ liệu chưa qua normalize và pipeline dừng ngay với lỗi `non_iso_rows=1`.

**Metric phát hiện:** Log in ra `expectation[effective_date_iso_yyyy_mm_dd] FAIL (halt) :: non_iso_rows=1` — rõ ràng chỉ đúng 1 dòng vi phạm, khớp với row 10 trong raw CSV.

**Fix:** Xác nhận lại thứ tự trong `etl_pipeline.py`: hàm `clean_rows()` (bao gồm Rule 2 normalize ngày `DD/MM/YYYY` → `2026-02-01`) phải chạy **trước** khi `run_expectations()` nhận cleaned output. Sau khi đảm bảo đúng thứ tự, expectation E5 trả về `OK` vì row 10 đã được chuẩn hóa thành `2026-02-01`. `quarantine_records` không đổi (dòng này pass clean, chỉ là ngày được normalize), `cleaned_records` giữ nguyên 6.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**run_id:** `sprint2-huy`

**Trước (raw — 10 records, chưa qua cleaning):**

| chunk | doc_id | nội dung stale |
|-------|--------|----------------|
| row 3 | `policy_refund_v4` | "hoàn tiền trong vòng **14 ngày làm việc**" |
| row 7 | `hr_leave_policy` | "được **10 ngày phép năm** (bản HR 2025)", `effective_date=2025-01-01` |

**Sau (cleaned — run_id=sprint2-huy, 6 records):**

```
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
expectation[no_stale_leave_policy_any_doc] OK (halt) :: stale_leave_chunks=0 doc_ids=[]
quarantine_records=4
```

Row 3 được Rule 6 fix thành "7 ngày làm việc" trước khi embed; row 7 bị Rule 3 quarantine do `effective_date=2025-01-01 < 2026-01-01`. Kết quả: cả hai expectation halt đều `OK` — corpus không còn chunk stale có thể làm agent trả lời sai policy.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ viết **unit test riêng cho từng rule** trong `transform/cleaning_rules.py` bằng `pytest`. Hiện tại metric_impact chỉ được kiểm chứng bằng cách chạy toàn bộ pipeline và đếm `quarantine_records` — nếu một rule bị vô tình phá vỡ bởi thay đổi sau này, không có test nào bắt được. Cụ thể: test Rule 7 với string chứa `\ufeff`, test Rule 8 với chunk dài đúng bằng `MIN_CHUNK_CHARS - 1`, test Rule 9 với `effective_date` đặt cách hôm nay `MAX_FUTURE_DAYS + 1` ngày — mỗi case assert `quarantine` tăng đúng 1 và `reason` khớp.
