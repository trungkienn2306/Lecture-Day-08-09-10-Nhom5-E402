# Quality Report — Lab Day 10
## Nhóm 05-E402 | Data Pipeline & Data Observability

**Run tham chiếu chính:** `sprint-final` (clean run)  
**Run inject:** `inject-bad2` (no-refund-fix + skip-validate)  
**Ngày:** 2026-04-15

---

## 1. Executive Summary

Pipeline Day 10 xử lý raw CSV export (`policy_export_dirty.csv`) qua 3 bước: **clean** → **validate** → **embed** vào ChromaDB `day10_kb`.

| Metric | Sprint-final (clean) | inject-bad2 (corrupted) |
|--------|---------------------|------------------------|
| raw_records | 10 | 10 |
| cleaned_records | 6 | 6 |
| quarantine_records | 4 | 4 |
| Expectations passed | tất cả PASS | E3 FAIL (halt — bỏ qua do --skip-validate) |
| Freshness (1-boundary) | PASS, age_hours=0.0 | PASS |
| Freshness (2-boundary) | PASS (ingest≈0.007h, publish≈0.0h) | PASS |

**Kết luận:** Pipeline clean run đạt tất cả expectation. Inject-bad run cố tình tạo trạng thái "before" xấu để chứng minh before/after retrieval effect.

---

## 2. Expectation Pass/Fail — Sprint-final Run

| Expectation | Severity | Kết quả | Detail |
|-------------|---------|---------|--------|
| `pydantic_schema_validation` | halt | **PASS** | pydantic validates 5 fields, 0 errors |
| `min_one_row` | halt | **PASS** | cleaned_rows=6 ≥ 1 |
| `no_empty_doc_id` | halt | **PASS** | empty_doc_id_count=0 |
| `refund_no_stale_14d_window` | halt | **PASS** | violations=0 (Rule 6 đã fix 14→7) |
| `chunk_min_length_8` | warn | **PASS** | short_chunks=0 |
| `effective_date_iso_yyyy_mm_dd` | halt | **PASS** | non_iso_rows=0 |
| `hr_leave_no_stale_10d_annual` | halt | **PASS** | violations=0 (Rule 3 quarantine bản 2025) |
| `no_stale_leave_policy_any_doc` | halt | **PASS** | stale_leave_chunks=0 |
| `min_chunks_per_expected_doc` | warn | **PASS** | missing_or_insufficient=[] |

---

## 3. Expectation Pass/Fail — inject-bad2 Run

| Expectation | Severity | Kết quả | Detail |
|-------------|---------|---------|--------|
| `pydantic_schema_validation` | halt | **PASS** | No schema violations |
| `min_one_row` | halt | **PASS** | có rows |
| `no_empty_doc_id` | halt | **PASS** | |
| `refund_no_stale_14d_window` | halt | **FAIL ❌** | violations>0 (--no-refund-fix) |
| `chunk_min_length_8` | warn | **PASS** | |
| `effective_date_iso_yyyy_mm_dd` | halt | **PASS** | |
| `hr_leave_no_stale_10d_annual` | halt | **PASS** | (HR bản cũ vẫn bị quarantine qua Rule 3) |
| `no_stale_leave_policy_any_doc` | halt | **PASS** | |
| `min_chunks_per_expected_doc` | warn | **PASS** | |

> **Ghi chú:** inject-bad2 dùng `--skip-validate` → pipeline tiếp tục embed dù E3 FAIL. Đây là chủ đích để demo "before" state.

---

## 4. Metric Impact Table (Bắt buộc — chống trivial rules)

| Rule / Expectation | Baseline (sprint-final) | Inject / Thiếu fix | Chứng cứ |
|-------------------|------------------------|--------------------|---------|
| **Rule 7** — encoding_corruption | quarantine +0 (không có BOM trong raw) | Inject chunk `"\ufefftest"` → quarantine +1 | `quarantine_*.csv` row `reason=encoding_corruption_in_chunk_text` |
| **Rule 8** — chunk_text_too_short | quarantine +0 (tất cả chunk ≥ 20 chars) | Inject `chunk_text="hi"` → quarantine +1 | quarantine row `reason=chunk_text_too_short, chunk_len=2, min_required=20` |
| **Rule 9** — future_effective_date | quarantine +0 | Inject `effective_date=2099-01-01` → quarantine +1 | quarantine row `reason=future_effective_date_exceeds_threshold` |
| **E7** — no_stale_leave_policy_any_doc (halt) | PASS (HR stale quarantined by Rule 3) | Inject HR chunk "10 ngày phép" với date hợp lệ → FAIL halt | log `expectation[no_stale_leave_policy_any_doc] FAIL (halt) stale_leave_chunks=1` |
| **E8** — min_chunks_per_expected_doc (warn) | PASS, all 4 docs present | Xóa chunk sla_p1_2026 → WARN | log `expectation[min_chunks_per_expected_doc] FAIL (warn) missing=[sla_p1_2026]` |
| **Pydantic** — schema_validation (halt) | PASS, 0 errors | Inject row `doc_id=""` → FAIL halt | log `expectation[pydantic_schema_validation] FAIL pydantic_errors=1` |

---

## 5. Cleaning Summary (Sprint-final — dữ liệu thực)

| Rule | Records bị quarantine | Reason |
|------|----------------------|--------|
| Rule 1 — unknown_doc_id | 1 | `legacy_catalog_xyz_zzz` không trong allowlist |
| Rule 2/4 — missing_effective_date | 1 | `exported_at` có nhưng `effective_date` rỗng |
| Rule 3 — stale_hr_policy | 1 | HR bản 2025 (`effective_date=2025-01-01 < 2026-01-01`) |
| Rule 5 — duplicate_chunk_text | 1 | Chunk refund trùng nội dung |
| **Tổng quarantine** | **4** | raw=10, cleaned=6, quarantine=4 |

Xem đầy đủ: `artifacts/quarantine/quarantine_sprint-final.csv`

---

## 6. Before/After Retrieval Effect

**Kịch bản:** Chạy `python eval_retrieval.py` sau inject-bad2 (before) vs sau sprint-final (after).

| Question | Before (inject-bad2) `after_inject_bad.csv` | After (sprint-final) `before_after_eval.csv` |
|---------|---------------------------------------------|----------------------------------------------|
| `q_refund_window` — Hoàn tiền bao nhiêu ngày? | `hits_forbidden=yes` ⚠️ ("14 ngày làm việc" lọt top-k) | `hits_forbidden=no` ✅, `contains_expected=yes` ("7 ngày") |
| `q_p1_sla` — SLA P1? | `contains_expected=yes`, `hits_forbidden=no` ✅ | `contains_expected=yes`, `hits_forbidden=no` ✅ |
| `q_lockout` — Đăng nhập sai bị khóa? | `contains_expected=yes`, `hits_forbidden=no` ✅ | `contains_expected=yes`, `hits_forbidden=no` ✅ |
| `q_leave_version` — HR phép năm 2026? | `contains_expected=yes`, `hits_forbidden=no` ✅ | `contains_expected=yes`, `hits_forbidden=no` ✅, `top1_doc_expected=yes` |

**Bằng chứng:** `artifacts/eval/before_after_eval.csv` (sprint-final) — tất cả 4 câu `contains_expected=yes, hits_forbidden=no`.

---

## 7. Grading Questions — Kết quả chính thức (sau 17:00)

Bộ câu hỏi GV phát: `data/grading_questions.json` (3 câu).  
Chạy bằng: `python grading_run.py --out artifacts/eval/grading_run.jsonl --top-k 5`

| ID | Câu hỏi (tóm tắt) | top1_doc_id | contains_expected | hits_forbidden | top1_doc_matches |
|----|-------------------|-------------|-------------------|----------------|-----------------|
| `gq_d10_01` | Hoàn tiền tối đa bao nhiêu ngày? | `policy_refund_v4` | `true` ✅ | `false` ✅ | — |
| `gq_d10_02` | Ticket P1 resolution SLA? | `sla_p1_2026` | `true` ✅ | `false` ✅ | — |
| `gq_d10_03` | Phép năm nhân viên < 3 năm (2026)? | `hr_leave_policy` | `true` ✅ | `false` ✅ | `true` ✅ |

**Kết quả: 3/3 câu đạt toàn bộ tiêu chí grading.**  
- `gq_d10_01`: keyword "7" xuất hiện trong top-5, không có "14 ngày làm việc" → Rule 6 hoạt động đúng.  
- `gq_d10_02`: keyword "4 giờ" / "4h" xuất hiện trong top-5 → chunk `sla_p1_2026` được embed đúng.  
- `gq_d10_03`: keyword "12 ngày" xuất hiện, không có "10 ngày phép năm", top-1 đúng doc `hr_leave_policy` → Rule 3 + versioning hoạt động.

Xem đầy đủ: `artifacts/eval/grading_run.jsonl`.

---

## 8. Idempotency Test

Chạy pipeline 2 lần liên tiếp với cùng input:

| Lần chạy | cleaned_records | embed_upsert count | embed_prune_removed |
|---------|----------------|---------------------|---------------------|
| sprint-final | 6 | 6 | 1 (từ inject-bad2 trước đó) |
| verify-final | 6 | 6 | 0 (cùng chunk_ids) |

**Kết quả:** Collection count không đổi giữa lần 2 và lần 3 → idempotency xác nhận ✅

---

## 9. Freshness 2-Boundary (Bonus +1)

Từ `manifest_sprint-final.json`:

| Boundary | Timestamp | Age (giờ) | SLA | Status |
|---------|-----------|-----------|-----|--------|
| ingest | `2026-04-15T04:54:28+00:00` | 0.007 | 24h | PASS |
| publish | `2026-04-15T04:54:51+00:00` | 0.0 | 24h | PASS |

> **Ghi chú:** `latest_exported_at` trong raw CSV là `2026-04-10T08:00:00` (5 ngày trước) — đây là mock export lab. Trong production, freshness sẽ tính từ `exported_at` của data source.
