# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Nhóm 05 — E402  
**Thành viên:**

| Tên | Mã học viên | Vai trò (Day 10) |
|-----|-------------|------------------|
| Trần Ngọc Huy | — | Ingestion / Raw Owner (Sprint 1) |
| Nông Trung Kiên | 2A202600414 | Embed & Monitoring (Sprint 3 & 4) |
| Bùi Thế Công | — | Ingestion Owner — Data Contract & Manifest (Sprint 1) |

**Ngày nộp:** 15/04/2026  
**Branch:** `feat/day10-sprint3&4`  
**Repo:** `Lecture-Day-08-09-10-Nhom5-E402`

---

## 1. Pipeline tổng quan

Nguồn raw là file `data/raw/policy_export_dirty.csv` — CSV mock 10 bản ghi đại diện cho export định kỳ từ các hệ thống nội bộ (HR, Helpdesk, Policy). File chứa đầy đủ các dạng lỗi thực tế: doc_id không hợp lệ, thiếu ngày, policy refund phiên bản cũ (14 ngày thay vì 7 ngày), HR bản 2025 (10 ngày phép thay vì 12 ngày), và chunk trùng lặp nội dung.

**Luồng end-to-end:**

```
CSV raw (10 rows)
  → load_raw_csv()                       [ingest_boundary_at ghi tại đây]
  → cleaning_rules.py (Rules 1–9)        → cleaned (6 rows) + quarantine (4 rows)
  → expectations.py (pydantic + E1–E8)   → PASS hoặc PIPELINE_HALT exit 2
  → cmd_embed_internal()                 → ChromaDB day10_kb (upsert + prune)
                                         [publish_boundary_at ghi tại đây]
  → manifest JSON + freshness 2-boundary check
```

**Lệnh chạy chính:**

```bash
python etl_pipeline.py run --run-id sprint-final
```

**run_id tham chiếu:** `sprint-final`  
Log tại: `artifacts/logs/run_sprint-final.log` — kết thúc dòng `PIPELINE_OK`  
Manifest: `artifacts/manifests/manifest_sprint-final.json`

| Metric | Giá trị |
|--------|---------|
| raw_records | 10 |
| cleaned_records | 6 |
| quarantine_records | 4 |
| ingest_boundary_at | `2026-04-15T04:54:28+00:00` |
| publish_boundary_at | `2026-04-15T04:54:51+00:00` |

---

## 2. Cleaning & Expectation

Baseline pipeline có 6 rule gốc (allowlist doc_id, ISO date, HR stale, refund window fix, dedupe, min chunk length). Nhóm bổ sung **3 rule mới** và **2 expectation mới**, cùng **1 pydantic bonus**.

### 2a. Bảng metric_impact

| Rule / Expectation mới | Sprint-final (baseline) | Khi inject / tắt rule | Chứng cứ |
|------------------------|------------------------|----------------------|----------|
| **Rule 7** — `encoding_corruption_in_chunk_text` | quarantine +0 (raw không có BOM) | Inject `chunk_text="\ufefftest"` → quarantine +1 | `quarantine_*.csv` row `reason=encoding_corruption_in_chunk_text` |
| **Rule 8** — `chunk_text_too_short` (< `MIN_CHUNK_CHARS=20`) | quarantine +0 (tất cả ≥ 20 chars) | Inject `chunk_text="hi"` → quarantine +1 | `quarantine_*.csv` row `reason=chunk_text_too_short, chunk_len=2` |
| **Rule 9** — `future_effective_date_exceeds_threshold` | quarantine +0 | Inject `effective_date=2099-01-01` → quarantine +1 | `quarantine_*.csv` row `reason=future_effective_date_exceeds_threshold` |
| **E7** — `no_stale_leave_policy_any_doc` (halt) | PASS — HR stale đã bị quarantine Rule 3 | Inject HR chunk "10 ngày phép" với date hợp lệ → FAIL halt | log `expectation[no_stale_leave_policy_any_doc] FAIL (halt)` |
| **E8** — `min_chunks_per_expected_doc` (warn) | PASS — đủ 4 doc_id | Xóa chunk `sla_p1_2026` → WARN | log `expectation[min_chunks_per_expected_doc] FAIL (warn) missing=[sla_p1_2026]` |
| **Pydantic** — `pydantic_schema_validation` (halt) | PASS — 0 errors | Inject `doc_id=""` → FAIL halt | log `expectation[pydantic_schema_validation] FAIL pydantic_errors=1` |

**Cutoff dates đọc từ env var, không hardcode trong code:**
- `HR_LEAVE_MIN_EFFECTIVE_DATE=2026-01-01` (Rule 3)
- `MIN_CHUNK_CHARS=20` (Rule 8)
- `MAX_FUTURE_DAYS=365` (Rule 9)

**Ví dụ expectation fail thực tế (run inject-bad2, `--no-refund-fix --skip-validate`):**

```
expectation[refund_no_stale_14d_window] FAIL (halt) violations=1
WARN: expectation failed but --skip-validate -- tiep tuc embed (chi dung cho demo Sprint 3).
```

---

## 3. Before / After ảnh hưởng retrieval

**Kịch bản inject (Sprint 3):** Chạy pipeline với `--no-refund-fix --skip-validate --run-id inject-bad2`. Rule 6 bị tắt nên chunk refund cũ ("14 ngày làm việc") không bị sửa và lọt thẳng vào ChromaDB. Sau đó chạy `eval_retrieval.py` để đo ảnh hưởng với bộ câu hỏi test.

**Kết quả định lượng — dữ liệu thật từ CSV:**

| question_id | Before (`after_inject_bad.csv`) | After (`before_after_eval.csv`) |
|-------------|----------------------------------|----------------------------------|
| `q_refund_window` | `hits_forbidden=yes` ⚠️ — top1_preview: *"Yêu cầu hoàn tiền được chấp nhận trong vòng **14 ngày** làm việc..."* | `hits_forbidden=no` ✅ — top1_preview: *"Yêu cầu được gửi trong vòng **7 ngày** làm việc..."* |
| `q_p1_sla` | `contains_expected=yes`, `hits_forbidden=no` ✅ | `contains_expected=yes`, `hits_forbidden=no` ✅ |
| `q_lockout` | `contains_expected=yes`, `hits_forbidden=no` ✅ | `contains_expected=yes`, `hits_forbidden=no` ✅ |
| `q_leave_version` | `contains_expected=yes`, `hits_forbidden=no` ✅ | `contains_expected=yes`, `hits_forbidden=no` ✅, `top1_doc_expected=yes` |

**Kết quả Grading Questions (bộ câu GV phát, chạy sau 17:00):**

| ID | Câu hỏi | top1_doc_id | contains_expected | hits_forbidden | top1_doc_matches |
|----|---------|-------------|-------------------|----------------|-----------------|
| `gq_d10_01` | Hoàn tiền tối đa bao nhiêu ngày làm việc? | `policy_refund_v4` | `true` ✅ | `false` ✅ | — |
| `gq_d10_02` | Ticket P1 resolution SLA? | `sla_p1_2026` | `true` ✅ | `false` ✅ | — |
| `gq_d10_03` | Phép năm nhân viên < 3 năm (2026)? | `hr_leave_policy` | `true` ✅ | `false` ✅ | `true` ✅ |

**3/3 câu grading đạt toàn bộ tiêu chí.** Xem: `artifacts/eval/grading_run.jsonl`.

---

## 4. Freshness & Monitoring

Module `monitoring/freshness_check.py` kiểm tra SLA theo **2 boundary** (Nông Trung Kiên thực hiện):

- `ingest_boundary_at`: timestamp sau khi `load_raw_csv()` hoàn thành
- `publish_boundary_at`: timestamp sau khi embed vào ChromaDB hoàn thành

SLA mặc định 24 giờ, đọc từ env var `FRESHNESS_SLA_HOURS`. Hàm `check_two_boundary_freshness()` trả về `overall: PASS/WARN/FAIL` cho cả hai boundary độc lập.

**Kết quả sprint-final (từ manifest thật):**

| Boundary | Timestamp | Age (giờ) | SLA | Status |
|---------|-----------|-----------|-----|--------|
| ingest | `2026-04-15T04:54:28+00:00` | ~0.007h | 24h | **PASS** |
| publish | `2026-04-15T04:54:51+00:00` | ~0.0h | 24h | **PASS** |

```
freshness_two_boundary={"overall":"PASS","ingest":{"status":"PASS","age_hours":0.007},"publish":{"status":"PASS","age_hours":0.0}}
```

**Lỗi thực tế đã xử lý (Nông Trung Kiên):** `datetime.fromisoformat()` của Python crash khi gặp timestamp dạng `2026-04-10T08:00:00Z` (có hậu tố "Z"). Fix bằng cách thêm hàm `parse_iso(ts)` thay "Z" → "+00:00" trước khi parse.

**Lỗi thực tế đã xử lý (Bùi Thế Công):** Freshness check báo `FAIL age_hours=121.1` khi chạy Sprint 1, do trường `exported_at` trong raw CSV là `2026-04-10T08:00:00` (5 ngày trước). Đây là hành vi đúng — dữ liệu mock export cũ nên freshness dựa trên `exported_at` thực sự FAIL. Nhóm giữ nguyên FAIL trong log Sprint 1 làm bằng chứng Observability hoạt động; freshness dựa trên `ingest_boundary_at` / `publish_boundary_at` (boundary thực của pipeline run) mới là PASS.

---

## 5. Liên hệ Day 09

Collection `day10_kb` trong ChromaDB (`./chroma_db`) có thể phục vụ trực tiếp các agent RAG từ Day 09 bằng cách trỏ `CHROMA_COLLECTION=day10_kb`. Hai điểm khác biệt chính:

- Day 09 dùng SentenceTransformer (`all-MiniLM-L6-v2`, 384 dim); Day 10 dùng OpenAI `text-embedding-3-small` (1536 dim) — cần xóa `chroma_db/` và rebuild khi chuyển đổi provider.
- Day 10 embed thêm metadata `doc_id`, `effective_date`, `run_id` vào từng chunk — cho phép filter theo phiên bản policy khi query từ agent.

Nhóm tách collection (`day10_kb`) để không làm ô nhiễm collection Day 09, đảm bảo độc lập giữa các sprint.

---

## 6. Rủi ro còn lại & việc chưa làm

- **Unit test cho từng cleaning rule chưa có:** `pytest tests/` chỉ smoke test toàn pipeline, chưa có test assert riêng cho Rule 7, 8, 9.
- **Inject scenario cho Rule 7/8/9 là phân tích code, chưa chạy thực tế:** Các metric_impact bảng trên là kết quả phân tích logic; chưa có run artifact cụ thể trong `artifacts/quarantine/` cho từng inject type.
- **Scheduler/cron chưa thiết lập:** Freshness monitoring cần gắn vào cron để tự động alert `WARN` — hiện chạy thủ công sau mỗi run.
- **Chưa test cross-platform:** Toàn bộ chạy trên Windows PowerShell; chưa verify path separator trên Linux/macOS.
