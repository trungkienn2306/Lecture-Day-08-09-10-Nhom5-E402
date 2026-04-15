# Implementation Plan — Lab Day 10: Data Pipeline & Data Observability
## Nhóm 05-E402 | Trạng thái: HOÀN THÀNH ✅

> **Mục đích tài liệu này:** Giải thích chi tiết bài tập lab Day 10, cách tính điểm, hướng dẫn nộp bài,
> và trạng thái implement hiện tại — đủ để AI agent khác đọc và tiếp tục mà không cần hỏi thêm.
>
> **Primary Reference:** `day10/lab/README.md` + `day10/lab/SCORING.md`

---

## 1. TÓM TẮT BÀI TẬP

### Bối cảnh
Lab Day 10 xây dựng **lớp data pipeline** cho hệ thống CS/HR đã có từ Day 08-09. Nguồn dữ liệu là file CSV export "bẩn" (`data/raw/policy_export_dirty.csv`) chứa nhiều lỗi thực tế: duplicate, encoding sai, bản policy cũ (HR 2025 vs 2026), refund window sai (14 ngày vs 7 ngày), date format không nhất quán.

### Mục tiêu
Xây dựng pipeline **Ingest → Clean → Validate → Embed → Monitor** với:
- Log đầy đủ (run_id, raw_records, cleaned_records, quarantine_records)
- Cleaning rules có tác động đo được
- Expectation suite với halt/warn phân biệt
- Idempotent embed vào ChromaDB
- Freshness monitoring với 2 boundaries (ingest + publish)
- Before/after retrieval evidence
- Grading JSONL 3 câu hỏi

### 4 Sprint
| Sprint | Nội dung | DoD |
|--------|---------|-----|
| Sprint 1 | Ingest + log + manifest | `run_id`, `raw_records`, `cleaned_records`, `quarantine_records` trong log |
| Sprint 2 | Clean (≥3 rule mới) + Validate (≥2 expectation mới) + Embed idempotent | `etl_pipeline.py run` exit 0 |
| Sprint 3 | Inject corruption + before/after eval | CSV chứng minh retrieval xấu → tốt |
| Sprint 4 | Monitoring + 3 docs + reports | Runbook, data_contract, pipeline_architecture, quality_report |

---

## 2. CÁCH TÍNH ĐIỂM CHI TIẾT

### Tổng điểm: 100 (+ bonus 3)

### Phần Nhóm — 60 điểm

#### Mục 1: ETL & Pipeline (27 điểm)
| Tiêu chí | Điểm | Status |
|----------|------|--------|
| `python etl_pipeline.py run` exit 0 | 10 | ✅ PASS |
| Log có run_id, raw_records, cleaned_records, quarantine_records khớp artifact | 5 | ✅ PASS |
| `cleaning_rules.py` có ≥3 rule mới vs baseline (Rule 7, 8, 9) — không trivial | 6 | ✅ PASS |
| Embed idempotent: upsert chunk_id + prune stale IDs + rerun 2 lần không phình | 6 | ✅ PASS |
| **Subtotal** | **27/27** | ✅ |

#### Mục 2: Documentation (15 điểm)
| Tiêu chí | Điểm | Status |
|----------|------|--------|
| `docs/pipeline_architecture.md` có sơ đồ + ranh giới ingest/clean/embed | 5 | ✅ PASS |
| `docs/data_contract.md` có source map ≥2 nguồn + schema/owner | 5 | ✅ PASS |
| `docs/runbook.md` đủ 5 mục Symptom→Prevention | 5 | ✅ PASS |
| **Subtotal** | **15/15** | ✅ |

#### Mục 3: Quality Evidence (18 điểm)
| Tiêu chí | Điểm | Status |
|----------|------|--------|
| `expectations.py` có ≥2 expectation mới + warn/halt phân biệt (E7, E8) | 6 | ✅ PASS |
| Before/after: ≥2 dòng chứng cứ eval CSV + inject vs clean | 6 | ✅ PASS |
| Quality report (theo template) có run_id + interpret | 6 | ✅ PASS |
| **Subtotal** | **18/18** | ✅ |

#### Mục 4: Grading JSONL (12 điểm)
| Tiêu chí | Điểm | Status |
|----------|------|--------|
| `grading_run.jsonl` tồn tại, đúng 3 dòng gq_d10_01…gq_d10_03, JSON hợp lệ | 2 | ✅ PASS |
| `gq_d10_01`: contains_expected=true, hits_forbidden=false | 4 | ✅ PASS |
| `gq_d10_02`: contains_expected=true | 3 | ✅ PASS |
| `gq_d10_03`: contains_expected=true, hits_forbidden=false, top1_doc_matches=true | 3 | ✅ PASS |
| **Subtotal** | **12/12** | ✅ |

### Phần Cá nhân — 40 điểm
| Tiêu chí | Điểm/người | Status |
|----------|-----------|--------|
| Mục 5 — Individual report (400-650 từ, 5 phần) | 30 | ✅ 3/3 reports đủ |
| Mục 6 — Code contribution khớp commit/role | 10 | ✅ Roles nhất quán |

### Bonus — tối đa +3
| Hành động | Điểm | Status |
|-----------|------|--------|
| Pydantic `BaseModel` + `@field_validator` thật (không placeholder) | +2 | ✅ `run_pydantic_expectations()` |
| Freshness 2 boundary (ingest + publish) có log minh chứng | +1 | ✅ `check_two_boundary_freshness()` |
| **Subtotal Bonus** | **+3** | ✅ |

### Phân hạng
| Hạng | Điều kiện | Status |
|------|-----------|--------|
| **Pass** | Đủ checklist mục 1-3, grading JSONL hợp lệ, gq_d10_01 + gq_d10_02 đúng | ✅ |
| **Merit** | Pass + gq_d10_03 đủ + có chứng cứ q_leave_version | ✅ |
| **Distinction** | Merit + ≥1 bằng chứng "vượt baseline": (a) pydantic/GE thật, (b) freshness 2 boundary, (d) rule versioning env | ✅ (a)+(b)+(d) |

### **TỔNG ƯỚC TÍNH: 103/100 (Distinction)**

---

## 3. HƯỚNG DẪN NỘP BÀI

### Timeline
| Thời điểm | Sự kiện |
|-----------|---------|
| 17:00 | Public `data/grading_questions.json` (nếu GV ẩn trước đó) |
| 17:00-18:00 | Chạy `python grading_run.py --out artifacts/eval/grading_run.jsonl` |
| **18:00** | **Deadline** code + artifact bắt buộc |
| Sau 18:00 | Chỉ `reports/*.md` (nếu cho phép) |

### Danh sách file phải nộp (commit trước 18:00)

#### Code (bắt buộc)
| File | Nội dung cần có |
|------|----------------|
| `etl_pipeline.py` | cmd_run() với 2 boundary timestamps, cmd_embed_internal() với upsert+prune, cmd_freshness() |
| `transform/cleaning_rules.py` | Rules 1-9 (6 baseline + 3 mới: R7 encoding corruption, R8 chunk too short, R9 future date) |
| `quality/expectations.py` | E1-E8 (6 baseline + E7 no_stale_leave_any_doc halt, E8 min_chunks_per_doc warn) + run_pydantic_expectations() |
| `monitoring/freshness_check.py` | check_manifest_freshness() + check_two_boundary_freshness() |
| `contracts/data_contract.yaml` | Điền owner, SLA, source |

#### Artifacts (bắt buộc)
| File | Nội dung cần có |
|------|----------------|
| `artifacts/eval/grading_run.jsonl` | Đúng 3 dòng JSON: gq_d10_01, gq_d10_02, gq_d10_03 |
| `artifacts/eval/before_after_eval.csv` | Bảng so sánh inject-bad vs clean run |
| `artifacts/manifests/manifest_*.json` | Ít nhất manifest_sprint-final.json với đủ fields + 2 boundaries |
| `artifacts/logs/run_*.log` | Ít nhất run_sprint1.log + run_inject-bad.log |
| `artifacts/quarantine/quarantine_*.csv` | Ít nhất quarantine_sprint-final.csv |
| `artifacts/cleaned/cleaned_*.csv` | Ít nhất cleaned_sprint-final.csv |

#### Docs (bắt buộc)
| File | Nội dung cần có |
|------|----------------|
| `docs/pipeline_architecture.md` | Sơ đồ DAG + bảng ranh giới ingest/clean/embed + idempotency |
| `docs/data_contract.md` | Source map ≥2 nguồn + schema + owner + SLA |
| `docs/runbook.md` | 5 mục: Symptom → Detection → Diagnosis → Mitigation → Prevention |
| `docs/quality_report.md` | run_id + expectation pass/fail table + metric_impact + before/after + idempotency |

#### Reports (theo quy định lớp — có thể nộp muộn)
| File | Nội dung cần có |
|------|----------------|
| `reports/group_report.md` | §1 Pipeline tổng quan, §2 Cleaning+Expectation+metric_impact table, §3 Before/After, §4 Freshness, §5 Liên hệ Day09, §6 Rủi ro |
| `reports/individual/tran_ngoc_huy.md` | 5 phần: phụ trách, quyết định kỹ thuật, lỗi xử lý, before/after, cải tiến; 400-650 từ |
| `reports/individual/nong_trung_kien.md` | 5 phần như trên |
| `reports/individual/bui_the_cong.md` | 5 phần như trên |

#### KHÔNG commit (trong .gitignore)
- `chroma_db/` — quá lớn (binaries)
- `.env` — chứa secrets
- `__pycache__/`, `*.pyc`, `.venv/`

---

## 4. TRẠNG THÁI HIỆN TẠI (2026-04-15)

### Tất cả file đã có ✅

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `etl_pipeline.py` | ✅ Hoàn chỉnh | cmd_run + cmd_embed_internal + cmd_freshness + 2 boundaries |
| `transform/cleaning_rules.py` | ✅ Hoàn chỉnh | 9 rules (R1-R6 baseline + R7-R9 mới), env vars cho R3/R8/R9 |
| `quality/expectations.py` | ✅ Hoàn chỉnh | 8 expectations (E1-E8) + pydantic real validation |
| `monitoring/freshness_check.py` | ✅ Hoàn chỉnh | 1-boundary + 2-boundary check |
| `contracts/data_contract.yaml` | ✅ Hoàn chỉnh | Owner, SLA, source map |
| `requirements.txt` | ✅ Fixed | pydantic>=2.0.0 đã thêm |
| `.gitignore` | ✅ Cập nhật | chroma_db, .env, __pycache__ |
| `docs/pipeline_architecture.md` | ✅ Hoàn chỉnh | Mermaid DAG + ASCII fallback + idempotency + env vars |
| `docs/data_contract.md` | ✅ Hoàn chỉnh | Source map, schema, owner |
| `docs/runbook.md` | ✅ Hoàn chỉnh | 5 mục đầy đủ |
| `docs/quality_report.md` | ✅ Hoàn chỉnh | Executive summary + expectation tables + metric_impact + before/after |
| `reports/group_report.md` | ✅ Hoàn chỉnh | 6 sections, metric_impact table, ~800 từ |
| `reports/individual/tran_ngoc_huy.md` | ✅ Hoàn chỉnh | ~520 từ, 5 phần |
| `reports/individual/nong_trung_kien.md` | ✅ Fixed | §5 đã sửa mâu thuẫn env var |
| `reports/individual/bui_the_cong.md` | ✅ Hoàn chỉnh | ~510 từ, 5 phần |
| `artifacts/eval/grading_run.jsonl` | ✅ Có sẵn | 3 dòng, gq_d10_01...03, contains_expected=true tất cả |
| `artifacts/manifests/manifest_sprint-final.json` | ✅ Có sẵn | Đủ fields + ingest_boundary_at + publish_boundary_at |
| `artifacts/logs/run_sprint-final.log` | ✅ Có sẵn | Đủ metrics |
| `artifacts/eval/before_after_eval.csv` | ✅ Có sẵn | before/after comparison |

### Các run hiện có
| run_id | Mục đích | Kết quả |
|--------|---------|---------|
| `sprint1` | Clean run đầu tiên | exit 0, cleaned=6, quarantine=4 |
| `sprint2` | Clean run tiếp theo | exit 0 |
| `inject-bad` | Sprint 3 — demo corruption | no-refund-fix + skip-validate |
| `inject-bad2` | Sprint 3 v2 — before state | no-refund-fix + skip-validate |
| `sprint-final` | Clean run cuối cùng | exit 0, cleaned=6, quarantine=4, embed=6 |
| `verify-final` | Verify idempotency | embed_prune_removed=0 (idempotent confirmed) |

---

## 5. CHI TIẾT KỸ THUẬT TỪNG COMPONENT

### 5.1 `transform/cleaning_rules.py`

**9 Cleaning Rules:**

| Rule | Tên | Severity | Tác động đo được |
|------|-----|---------|-----------------|
| R1 | `unknown_doc_id` | Quarantine | +1 quarantine khi inject doc_id lạ |
| R2 | `invalid_effective_date_format` / `missing_effective_date` | Quarantine | +1 khi date rỗng/sai format |
| R3 | `stale_hr_policy_effective_date` | Quarantine | +1 khi HR date < `HR_LEAVE_MIN_EFFECTIVE_DATE` |
| R4 | `missing_chunk_text` | Quarantine | +1 khi text rỗng |
| R5 | `duplicate_chunk_text` | Quarantine | +1 khi trùng nội dung |
| R6 | Fix stale refund | Fix text | Thay "14 ngày làm việc" → "7 ngày làm việc" + tag |
| **R7** | `encoding_corruption_in_chunk_text` | Quarantine | +1 khi inject `\ufeff` hoặc `\ufffd` |
| **R8** | `chunk_text_too_short` | Quarantine | +1 khi inject chunk < 20 chars |
| **R9** | `future_effective_date_exceeds_threshold` | Quarantine | +1 khi inject date 2099-01-01 |

**Env vars (Distinction criterion d — rule versioning):**
```
HR_LEAVE_MIN_EFFECTIVE_DATE=2026-01-01  # cutoff bản HR
MIN_CHUNK_CHARS=20                       # độ dài tối thiểu (Rule 8)
MAX_FUTURE_DAYS=365                      # threshold tương lai (Rule 9)
```

### 5.2 `quality/expectations.py`

**8 Expectations (E1-E8) + Pydantic:**

| Expectation | Severity | Logic |
|-------------|---------|-------|
| E1: `min_one_row` | halt | cleaned >= 1 row |
| E2: `no_empty_doc_id` | halt | không row nào doc_id rỗng |
| E3: `refund_no_stale_14d_window` | halt | không "14 ngày làm việc" trong policy_refund |
| E4: `chunk_min_length_8` | warn | chunk >= 8 chars |
| E5: `effective_date_iso_yyyy_mm_dd` | halt | date match YYYY-MM-DD |
| E6: `hr_leave_no_stale_10d_annual` | halt | không "10 ngày phép năm" trong hr |
| **E7**: `no_stale_leave_policy_any_doc` | **halt** | cross-doc check "10 ngày phép" mọi doc |
| **E8**: `min_chunks_per_expected_doc` | **warn** | mỗi doc có ít nhất 1 chunk |
| **Pydantic**: `pydantic_schema_validation` | **halt** | BaseModel + 4 field validators |

**`run_pydantic_expectations()`**: Import pydantic thật, validate 5 fields (chunk_id, doc_id, chunk_text, effective_date, exported_at), fallback về `run_expectations()` nếu ImportError.

### 5.3 `monitoring/freshness_check.py`

**2 functions:**
- `check_manifest_freshness()`: 1-boundary, đọc `publish_boundary_at` → PASS/WARN/FAIL
- `check_two_boundary_freshness()`: 2-boundary, đọc `ingest_boundary_at` + `publish_boundary_at` → per-boundary status + overall

**Bonus +1**: manifest phải có cả 2 trường + log `freshness_two_boundary=...`

### 5.4 `etl_pipeline.py`

**cmd_run() flow:**
```
1. ingest_boundary_at = now()          <- TIMESTAMP 1
2. rows = load_raw_csv(raw_path)
3. log run_id, raw_records, ingest_boundary_at
4. cleaned, quarantine = clean_rows(rows)
5. write cleaned_csv + quarantine_csv
6. log cleaned_records, quarantine_records
7. results, halt = run_pydantic_expectations(cleaned)
8. log expectation[...] OK/FAIL
9. if halt and not skip_validate -> exit 2
10. cmd_embed_internal(cleaned_csv)    <- upsert + prune
11. publish_boundary_at = now()        <- TIMESTAMP 2
12. log publish_boundary_at
13. write manifest JSON (cả 2 boundaries)
14. check_manifest_freshness(manifest)
15. check_two_boundary_freshness(manifest)
16. log PIPELINE_OK -> exit 0
```

**Idempotency (Bùi Thế Công — prune trước, upsert sau):**
```python
prev_ids = col.get(include=[])["ids"]
drop = sorted(set(prev_ids) - set(new_ids))
col.delete(ids=drop)           # prune stale
col.upsert(ids=new_ids, ...)   # upsert current
log(f"embed_prune_removed={len(drop)}")
```

### 5.5 `artifacts/eval/grading_run.jsonl`

**Format mỗi dòng (JSON object, 1 dòng/câu):**
```json
{
  "id": "gq_d10_01",
  "question": "...",
  "top1_doc_id": "policy_refund_v4",
  "contains_expected": true,
  "hits_forbidden": false,
  "top1_doc_matches": null,
  "top_k_used": 5,
  "grading_criteria": ["..."]
}
```

**3 câu hiện tại (trước khi có bộ câu hỏi grading chính thức lúc 17:00):**
- `gq_d10_01`: Refund window → contains "7 ngày", không có "14 ngày" ✅
- `gq_d10_02`: SLA P1 → contains "15 phút" ✅
- `gq_d10_03`: HR phép năm 2026 → contains "12 ngày", không có "10 ngày", top1 = hr_leave_policy ✅

> **QUAN TRỌNG:** Sau 17:00 khi GV public bộ câu hỏi grading, cần chạy lại:
> ```bash
> python grading_run.py --out artifacts/eval/grading_run.jsonl
> ```

---

## 6. LỆNH CHẠY ĐẦY ĐỦ

### Setup (lần đầu)
```bash
cd E:\LabAIThucChien\Lecture-Day-08-09-10-Nhom5-E402\day10\lab
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Clean run (Sprint 1-2)
```bash
python etl_pipeline.py run
# Hoặc với run-id cụ thể:
python etl_pipeline.py run --run-id sprint-final
```

### Inject corruption (Sprint 3 — "before" state)
```bash
python etl_pipeline.py run --run-id inject-bad2 --no-refund-fix --skip-validate
```

### Before/after eval
```bash
python eval_retrieval.py --out artifacts/eval/before_after_eval.csv
```

### Grading (chạy sau 17:00 khi có bộ câu hỏi)
```bash
python grading_run.py --out artifacts/eval/grading_run.jsonl
```

### Freshness check
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint-final.json
```

### Verify idempotency
```bash
python etl_pipeline.py run --run-id verify-final
# Xem log: embed_prune_removed=0 -> idempotent confirmed
```

### Kiểm tra GV (sanity check)
```bash
python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl
python instructor_quick_check.py --manifest artifacts/manifests/manifest_sprint-final.json
```

---

## 7. ĐIỀU KIỆN DISTINCTION (Tất cả đã đạt ✅)

| Criterion | Mô tả | Evidence |
|-----------|-------|---------|
| **(a) Pydantic/GE thật** | `run_pydantic_expectations()` dùng `pydantic.BaseModel` + `@field_validator`, validate 5 fields, fallback nếu ImportError | `quality/expectations.py` L196-252 |
| **(b) Freshness 2 boundary** | `ingest_boundary_at` + `publish_boundary_at` đo trong manifest; `check_two_boundary_freshness()` so sánh từng boundary vs SLA; log `freshness_two_boundary={"overall":"PASS"...}` | `monitoring/freshness_check.py`, `etl_pipeline.py` L65+L106 |
| **(d) Rule versioning env** | 3 env vars không hard-code: `HR_LEAVE_MIN_EFFECTIVE_DATE`, `MIN_CHUNK_CHARS`, `MAX_FUTURE_DAYS`; inject fake future date → quarantine confirms | `cleaning_rules.py` L39-46 |

---

## 8. CHECKLIST CUỐI (TRƯỚC KHI NỘP)

### Bắt buộc trước 18:00
- [x] `python etl_pipeline.py run` → exit 0
- [x] Log có run_id, raw_records, cleaned_records, quarantine_records
- [x] `artifacts/manifests/manifest_sprint-final.json` tồn tại + đủ fields
- [x] `artifacts/eval/grading_run.jsonl` đúng 3 dòng, tất cả contains_expected=true
- [x] `docs/pipeline_architecture.md` có sơ đồ
- [x] `docs/data_contract.md` có source map
- [x] `docs/runbook.md` 5 mục đủ
- [x] `docs/quality_report.md` có run_id + bảng expectation + metric_impact
- [x] `reports/group_report.md` có bảng metric_impact §2a
- [x] 3 rule mới (R7-R9) có tác động đo được (metric_impact table)
- [x] 2 expectation mới (E7-E8) + pydantic
- [x] Embed idempotent: `embed_prune_removed=0` lần 2
- [x] `requirements.txt` có pydantic>=2.0.0
- [x] `.gitignore` exclude chroma_db, .env, __pycache__

### Reports (có thể muộn)
- [x] `reports/individual/tran_ngoc_huy.md` — 5 phần, ~520 từ
- [x] `reports/individual/nong_trung_kien.md` — 5 phần, ~530 từ (§5 đã fix)
- [x] `reports/individual/bui_the_cong.md` — 5 phần, ~510 từ

### Việc cần làm sau 17:00
- [ ] Chạy lại `python grading_run.py --out artifacts/eval/grading_run.jsonl`
- [ ] Verify kết quả: `python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl`
- [ ] Commit tất cả artifacts + reports
- [ ] Push lên remote repo

---

## 9. FILES KHÔNG NỘP (trong .gitignore)

```
chroma_db/          # ChromaDB binaries — quá lớn, tái tạo được bằng etl_pipeline.py
.env                # Chứa API keys / env vars thật
__pycache__/        # Python bytecode
*.pyc               # Python compiled
.venv/              # Virtual environment
```

---

## 10. ĐIỂM YẾU / RISKS CÒN LẠI

| Risk | Xác suất | Ảnh hưởng điểm | Giải pháp |
|------|----------|----------------|----------|
| GV chấm khi `freshness_check=FAIL` | Trung bình | Không mất điểm (FAQ: FAIL trên lab data là hợp lý) | Ghi chú trong runbook §3 |
| `grading_run.jsonl` phải chạy lại sau 17:00 | Cao | Có thể cần update nếu bộ câu khác | Chạy `python grading_run.py` ngay sau 17:00 |
| E7 luôn PASS vì Rule 3 lọc trước | Thấp | Có thể bị đánh trivial | Đã ghi trong metric_impact: cần inject HR date 2026+ để test E7 riêng |
| pydantic ImportError trong môi trường GV | Thấp | Mất Bonus +2 | Đã thêm pydantic>=2.0.0 vào requirements.txt |
