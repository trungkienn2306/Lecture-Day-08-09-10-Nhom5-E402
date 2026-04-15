# Runbook — Lab Day 10: Data Pipeline & Data Observability

**Nhóm:** 05-E402 | **Pipeline:** `etl_pipeline.py` → ChromaDB `day10_kb`  
**Cập nhật:** 2026-04-15

---

## 1. Symptom (Triệu chứng)

### Symptom A — Agent trả lời sai policy refund

**Mô tả:** Agent hoặc retrieval trả về "khách hàng có **14 ngày** làm việc để hoàn tiền" thay vì "**7 ngày** làm việc".

**Biểu hiện cụ thể:**
- `eval_retrieval.py` xuất ra: `hits_forbidden=yes` cho câu `q_refund_window`
- Agent trích dẫn chunk từ `policy_refund_v4` nhưng nội dung stale

**Kịch bản gây ra:** Pipeline chạy với flag `--no-refund-fix` (bỏ qua Rule 6) hoặc Rule 6 bị disable trong `cleaning_rules.py`.

---

### Symptom B — Agent trả lời sai chính sách nghỉ phép HR

**Mô tả:** Agent trả về "nhân viên được **10 ngày phép năm**" thay vì "**12 ngày phép năm** theo chính sách 2026".

**Biểu hiện cụ thể:**
- `eval_retrieval.py` xuất ra: `hits_forbidden=yes` cho câu `q_leave_version`
- `top1_doc_expected=no` — top-1 chunk không từ `hr_leave_policy` (bản 2026)

**Kịch bản gây ra:** HR bản 2025 (`effective_date=2025-01-01`) không bị quarantine, lọt vào embed. Xảy ra khi `HR_LEAVE_MIN_EFFECTIVE_DATE` env var sai hoặc Rule 3 bị disable.

---

### Symptom C — Pipeline halt đột ngột (exit 2)

**Mô tả:** `python etl_pipeline.py run` kết thúc với exit code 2 và log `PIPELINE_HALT`.

**Biểu hiện cụ thể:**
```
expectation[refund_no_stale_14d_window] FAIL (halt) violations=1
PIPELINE_HALT
```

**Kịch bản gây ra:** Expectation halt phát hiện violation trong cleaned data — ví dụ refund window stale chưa được Rule 6 sửa, hoặc doc_id rỗng, hoặc ngày không hợp lệ.

---

### Symptom D — Freshness WARN hoặc FAIL

**Mô tả:** `python etl_pipeline.py freshness` hoặc log sau run báo `freshness_two_boundary=WARN/FAIL`.

**Biểu hiện cụ thể:**
```
freshness_two_boundary={"overall":"FAIL","ingest":{"status":"FAIL","age_hours":26.3}}
```

**Kịch bản gây ra:** Pipeline không chạy trong 24h (mặc định SLA), hoặc `ingest_boundary_at` / `publish_boundary_at` không được ghi vào manifest.

---

## 2. Detection (Phát hiện)

| Signal | Lệnh kiểm tra | Giá trị bình thường | Giá trị cảnh báo |
|--------|--------------|--------------------|--------------------|
| Pipeline exit code | `echo $?` sau `python etl_pipeline.py run` | `0` | `1` (error), `2` (halt) |
| Expectation result | Grep log: `expectation[...] FAIL` | Không có dòng FAIL | Có `FAIL (halt)` → dừng ngay |
| Freshness 2-boundary | Log: `freshness_two_boundary=...` | `"overall":"PASS"` | `"overall":"WARN"` hoặc `"FAIL"` |
| Retrieval eval | `python eval_retrieval.py` → `artifacts/eval/before_after_eval.csv` | `hits_forbidden=no` tất cả câu | `hits_forbidden=yes` bất kỳ câu |
| Quarantine count | Xem `manifest_*.json` → `quarantine_records` | 4 (sprint-final baseline) | Đột biến tăng/giảm bất thường |
| Collection count | `python -c "import chromadb; c=chromadb.PersistentClient('./chroma_db'); print(c.get_collection('day10_kb').count())"` | 6 (sprint-final) | Tăng liên tục qua mỗi run → prune bị lỗi |

---

## 3. Diagnosis (Chẩn đoán)

### Bước 1 — Đọc manifest JSON của run gần nhất

```bash
# Tìm manifest mới nhất
ls -lt artifacts/manifests/manifest_*.json | head -3

# Đọc số liệu tổng quan
python -c "
import json, sys
with open('artifacts/manifests/manifest_sprint-final.json') as f:
    m = json.load(f)
for k,v in m.items(): print(f'{k}: {v}')
"
```

**Kết quả mong đợi (clean run):**
```
run_id: sprint-final
raw_records: 10
cleaned_records: 6
quarantine_records: 4
ingest_boundary_at: 2026-04-15T...
publish_boundary_at: 2026-04-15T...
```

**Dấu hiệu bất thường:** `cleaned_records < 6` đột ngột (rule mới quá strict), `quarantine_records = 0` (rule không hoạt động), thiếu `ingest_boundary_at` / `publish_boundary_at` (pipeline cũ chưa có 2-boundary).

---

### Bước 2 — Kiểm tra quarantine CSV

```bash
# Xem quarantine của run cần debug
cat artifacts/quarantine/quarantine_sprint-final.csv

# Đếm theo reason
python -c "
import csv
from collections import Counter
with open('artifacts/quarantine/quarantine_sprint-final.csv') as f:
    rows = list(csv.DictReader(f))
counts = Counter(r['reason'] for r in rows)
for reason, n in counts.most_common(): print(f'{n:3d}  {reason}')
"
```

**Kết quả mong đợi:**
```
  1  unknown_doc_id
  1  missing_effective_date (hoặc invalid_effective_date_format)
  1  stale_hr_policy_effective_date
  1  duplicate_chunk_text
```

**Dấu hiệu bất thường:** `stale_hr_policy_effective_date = 0` → HR bản cũ có thể đã lọt vào embed. `encoding_corruption_in_chunk_text > 0` → có chunk BOM từ nguồn mới.

---

### Bước 3 — Chạy retrieval eval để xác nhận ảnh hưởng

```bash
python eval_retrieval.py --out artifacts/eval/diagnosis_run.csv
cat artifacts/eval/diagnosis_run.csv
```

**Kết quả mong đợi (clean state):**
```
q_refund_window  → contains_expected=yes, hits_forbidden=no
q_p1_sla         → contains_expected=yes, hits_forbidden=no
q_lockout        → contains_expected=yes, hits_forbidden=no
q_leave_version  → contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes
```

**Câu nào `hits_forbidden=yes` → biết chính xác loại data stale nào đang lọt vào collection.**

---

### Bảng chẩn đoán nhanh

| Triệu chứng | Nguyên nhân phổ biến | File cần kiểm tra |
|-------------|---------------------|-------------------|
| `hits_forbidden=yes` cho refund | Rule 6 disabled / `--no-refund-fix` | `transform/cleaning_rules.py` Rule 6 + manifest flag |
| `hits_forbidden=yes` cho HR | Rule 3 không quarantine bản 2025 | `HR_LEAVE_MIN_EFFECTIVE_DATE` env var, `.env` |
| `cleaned_records=0` | Allowlist quá strict, tất cả bị quarantine | `cleaning_rules.py` `ALLOWED_DOC_IDS` |
| `expectation[pydantic_schema_validation] FAIL` | Row có `doc_id=""` hoặc `chunk_text` < 8 chars | Xem log dòng `pydantic_errors=N` |
| `embed_prune_removed` tăng mãi | chunk_id thay đổi giữa các run (input không stable) | Kiểm tra `sha256(doc_id\|chunk_text\|seq)` |
| `freshness_two_boundary=WARN` | Manifest thiếu boundary timestamp | Phiên bản `etl_pipeline.py` cũ |

---

## 4. Mitigation (Xử lý)

### Tình huống 1 — Retrieval sai do data stale trong collection

```bash
# Bước 1: Chạy lại pipeline clean (không inject flag)
python etl_pipeline.py run --run-id hotfix-$(date +%Y%m%dT%H%M)

# Bước 2: Xác nhận prune đã xóa chunk cũ
# Log phải có: embed_prune_removed > 0 (nếu trước đó có inject)

# Bước 3: Verify retrieval
python eval_retrieval.py --out artifacts/eval/after_hotfix.csv
# Kiểm tra: tất cả hits_forbidden=no
```

---

### Tình huống 2 — Pipeline halt (exit 2) do expectation fail

```bash
# Bước 1: Xem expectation nào fail
grep "FAIL (halt)" artifacts/logs/pipeline_*.log | tail -5

# Bước 2a: Nếu là refund_no_stale_14d_window → Rule 6 không chạy
# Kiểm tra cleaning_rules.py có Rule 6 không bị comment
grep -n "refund" transform/cleaning_rules.py

# Bước 2b: Nếu là hr_leave_no_stale_10d_annual → kiểm tra env var
echo $HR_LEAVE_MIN_EFFECTIVE_DATE  # phải là 2026-01-01 hoặc mới hơn

# Bước 3: Fix nguồn rồi rerun
python etl_pipeline.py run
```

---

### Tình huống 3 — Freshness FAIL (data quá cũ)

```bash
# Kiểm tra SLA hiện tại
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint-final.json

# Nếu data source thật sự cũ → trigger re-ingest từ nguồn
# (Lab mock: cập nhật exported_at trong raw CSV hoặc tăng SLA)
FRESHNESS_SLA_HOURS=48 python etl_pipeline.py freshness \
  --manifest artifacts/manifests/manifest_sprint-final.json

# Nếu cần override SLA vĩnh viễn → sửa .env
echo "FRESHNESS_SLA_HOURS=48" >> .env
```

> **Lưu ý lab:** `latest_exported_at` trong raw CSV là `2026-04-10T08:00:00` (mock export 5 ngày trước). `ingest_boundary_at` và `publish_boundary_at` là timestamp thực của pipeline run — freshness đo từ boundary thực tế nên vẫn PASS.

---

### Tình huống 4 — Collection phình to (idempotency broken)

```bash
# Kiểm tra count hiện tại
python -c "
import chromadb
c = chromadb.PersistentClient('./chroma_db')
col = c.get_collection('day10_kb')
print('count:', col.count())
"

# Nếu count > 6 (sprint-final baseline) → xóa collection và rebuild
python -c "
import chromadb
c = chromadb.PersistentClient('./chroma_db')
c.delete_collection('day10_kb')
print('Collection deleted')
"
python etl_pipeline.py run --run-id rebuild-$(date +%Y%m%dT%H%M)
# count phải = 6 sau rebuild
```

---

## 5. Prevention (Phòng ngừa)

### P1 — Expectation suite là tuyến phòng thủ đầu tiên

Pipeline có 9 expectation (6 baseline + E7, E8, pydantic) chia 2 mức:
- **halt**: dừng pipeline ngay, không embed data xấu vào collection
- **warn**: log cảnh báo nhưng tiếp tục (để không block hoàn toàn khi thiếu coverage)

Mỗi khi thêm failure mode mới từ data source → **bắt buộc thêm expectation tương ứng** vào `quality/expectations.py`.

### P2 — Freshness 2-boundary monitoring

Hai timestamp `ingest_boundary_at` + `publish_boundary_at` được ghi vào mỗi manifest. Chạy `freshness_check` sau mỗi pipeline run để phát hiện sớm data lag:

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json
```

Nếu `overall=WARN` → kiểm tra xem pipeline có chạy định kỳ không (cron/scheduler).

### P3 — Rule versioning từ env var (không hardcode)

Cutoff dates được đọc từ biến môi trường, không hardcode:
```
HR_LEAVE_MIN_EFFECTIVE_DATE=2026-01-01   # trong .env
MIN_CHUNK_CHARS=20
MAX_FUTURE_DAYS=365
```

Khi policy thay đổi → chỉ update `.env` hoặc `contracts/data_contract.yaml`, không sửa code → tránh lỗi regression.

### P4 — Before/after eval sau mỗi thay đổi data

Mỗi khi raw CSV hoặc cleaning rule thay đổi:
1. Chạy `python etl_pipeline.py run` với run_id mới
2. Chạy `python eval_retrieval.py` → so sánh với baseline `before_after_eval.csv`
3. Nếu bất kỳ câu nào `hits_forbidden` thay đổi từ `no` → `yes` → rollback

### P5 — Commit artifact sau mỗi sprint

Commit `artifacts/manifests/`, `artifacts/quarantine/`, `artifacts/eval/` vào git sau mỗi sprint (không commit `chroma_db/` — regenerable). Điều này tạo audit trail cho mỗi run_id và cho phép so sánh số liệu giữa các sprint.
