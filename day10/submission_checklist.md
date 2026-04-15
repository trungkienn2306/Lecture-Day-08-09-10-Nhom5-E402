# Submission Checklist — Lab Day 10: Những file cần commit

**Nhóm:** 05-E402 | **Deadline nộp:** 18:00 ngày 2026-04-15  
**Grading questions phát:** 17:00 | **Thời gian chạy grading:** ~30 phút

---

## 1. Tổng quan hai luồng sinh artifact

```
Pipeline flow:
  python etl_pipeline.py run          →  artifacts/manifests/manifest_<run-id>.json
                                       artifacts/logs/run_<run-id>.log
                                       artifacts/cleaned/cleaned_<run-id>.csv
                                       artifacts/quarantine/quarantine_<run-id>.csv
                                       chroma_db/  (KHÔNG commit)

Luồng A — Test questions (eval_retrieval.py):
  python eval_retrieval.py            →  artifacts/eval/before_after_eval.csv
  python eval_retrieval.py (inject)  →  artifacts/eval/after_inject_bad.csv

Luồng B — Grading questions (grading_run.py):
  python grading_run.py               →  artifacts/eval/grading_run.jsonl
```

---

## 2. Luồng A — Test questions (`eval_retrieval.py`)

### 2.1 Lệnh chạy

```bash
# Sprint-final (clean state — AFTER fix):
python eval_retrieval.py \
  --questions data/test_questions.json \
  --out artifacts/eval/before_after_eval.csv

# Inject-bad state (BEFORE fix — để tạo evidence "trước khi sửa"):
python etl_pipeline.py run --no-refund-fix --skip-validate --run-id inject-bad2
python eval_retrieval.py \
  --questions data/test_questions.json \
  --out artifacts/eval/after_inject_bad.csv
```

### 2.2 File output và vị trí

| File | Đường dẫn | Mô tả |
|------|-----------|-------|
| `before_after_eval.csv` | `artifacts/eval/before_after_eval.csv` | State **AFTER fix** (sprint-final) |
| `after_inject_bad.csv` | `artifacts/eval/after_inject_bad.csv` | State **BEFORE fix** (inject-bad2) |

> **Chú ý tên file:** Tên `before_after_eval` là tên mặc định (default `--out`) của script.  
> File này đại diện trạng thái **sau khi sửa** (clean). Ngược lại, `after_inject_bad.csv` mới là state "trước khi sửa".

### 2.3 Schema CSV output

```
question_id, question, top1_doc_id, top1_preview, contains_expected, hits_forbidden, top1_doc_expected, top_k_used
```

| Cột | Giá trị mẫu | Ý nghĩa |
|-----|-------------|---------|
| `question_id` | `q_refund_window` | ID câu hỏi trong `test_questions.json` |
| `question` | `"Khách hàng có bao nhiêu ngày để hoàn tiền?"` | Nội dung câu hỏi |
| `top1_doc_id` | `policy_refund_v4` | doc_id của chunk top-1 |
| `top1_preview` | `"Khách hàng có 7 ngày làm việc..."` | 180 ký tự đầu chunk top-1 |
| `contains_expected` | `yes` / `no` | Có tìm thấy keyword must_contain_any không |
| `hits_forbidden` | `yes` / `no` | Có chunk nào chứa từ bị cấm không |
| `top1_doc_expected` | `yes` / `no` / `""` | Top-1 có đúng doc_id mong đợi không |
| `top_k_used` | `3` | Số chunk truy vấn |

### 2.4 Kết quả mong đợi (clean state — `before_after_eval.csv`)

```
q_refund_window  → contains_expected=yes, hits_forbidden=no
q_p1_sla         → contains_expected=yes, hits_forbidden=no
q_lockout        → contains_expected=yes, hits_forbidden=no
q_leave_version  → contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes
```

### 2.5 File cần commit (Luồng A)

```
artifacts/eval/before_after_eval.csv      ← AFTER fix (sprint-final)
artifacts/eval/after_inject_bad.csv       ← BEFORE fix (inject-bad2) — evidence Sprint 3
```

---

## 3. Luồng B — Grading questions (`grading_run.py`)

### 3.1 Lệnh chạy (sau 17:00 khi có file)

```bash
# Bước 1: Đảm bảo collection đang ở trạng thái clean (sprint-final)
python etl_pipeline.py run --run-id sprint-final
# (Nếu collection đã đúng, bỏ qua bước này — idempotent)

# Bước 2: Copy file grading_questions.json từ giảng viên vào
cp <đường-dẫn-GV-gửi> data/grading_questions.json

# Bước 3: Chạy grading
python grading_run.py \
  --questions data/grading_questions.json \
  --out artifacts/eval/grading_run.jsonl \
  --top-k 5
```

### 3.2 File output và vị trí

| File | Đường dẫn | Mô tả |
|------|-----------|-------|
| `grading_run.jsonl` | `artifacts/eval/grading_run.jsonl` | Kết quả grading — 1 dòng JSON/câu |

### 3.3 Schema JSONL output

Mỗi dòng là một JSON object (không dùng `"` ngoài field):

```json
{
  "id": "gq_d10_01",
  "question": "Nội dung câu hỏi từ grading_questions.json",
  "top1_doc_id": "policy_refund_v4",
  "contains_expected": true,
  "hits_forbidden": false,
  "top1_doc_matches": true,
  "top_k_used": 5,
  "grading_criteria": ["refund", "7 ngày"]
}
```

| Field | Kiểu | Ý nghĩa |
|-------|------|---------|
| `id` | string | ID câu từ `grading_questions.json` |
| `question` | string | Nội dung câu hỏi |
| `top1_doc_id` | string | doc_id metadata chunk top-1 |
| `contains_expected` | bool | Keyword must_contain_any có xuất hiện trong top-k không |
| `hits_forbidden` | bool | Keyword bị cấm có xuất hiện không |
| `top1_doc_matches` | bool / null | Top-1 đúng doc_id không; `null` nếu không có `expect_top1_doc_id` |
| `top_k_used` | int | Số chunk truy vấn (mặc định 5) |
| `grading_criteria` | list[str] | Tiêu chí chấm điểm |

> **Lưu ý JSONL vs JSON:** File là **JSONL** (JSON Lines) — mỗi dòng là một JSON riêng biệt, **KHÔNG** có dấu phẩy giữa các dòng, **KHÔNG** bọc mảng `[...]`.

### 3.4 Kiểm tra nhanh sau khi chạy

```bash
# Đếm số dòng (phải = số câu trong grading_questions.json)
python -c "
lines = open('artifacts/eval/grading_run.jsonl', encoding='utf-8').readlines()
print(f'Total lines: {len(lines)}')
import json
for i, l in enumerate(lines):
    r = json.loads(l)
    status = 'OK' if r['contains_expected'] and not r['hits_forbidden'] else 'FAIL'
    print(f'  [{status}] {r[\"id\"]}: contains_expected={r[\"contains_expected\"]}, hits_forbidden={r[\"hits_forbidden\"]}')
"
```

### 3.5 File cần commit (Luồng B)

```
data/grading_questions.json              ← File GV phát (copy vào đây trước khi chạy)
artifacts/eval/grading_run.jsonl         ← Output của grading_run.py
```

---

## 4. Sprint artifacts — File cần commit sau mỗi sprint

### 4.1 Sprint artifacts (đã có sẵn từ pipeline chạy)

```
artifacts/manifests/manifest_sprint-final.json    ← PHẢI có
artifacts/manifests/manifest_inject-bad2.json     ← Evidence Sprint 3
artifacts/quarantine/quarantine_sprint-final.csv  ← PHẢI có (4 records)
artifacts/quarantine/quarantine_inject-bad2.csv   ← Evidence Sprint 3
artifacts/logs/run_sprint-final.log               ← PHẢI có (PIPELINE_OK)
artifacts/cleaned/cleaned_sprint-final.csv        ← PHẢI có (6 records)
```

### 4.2 Eval artifacts (từ hai luồng trên)

```
artifacts/eval/before_after_eval.csv    ← Luồng A — AFTER fix
artifacts/eval/after_inject_bad.csv     ← Luồng A — BEFORE fix
artifacts/eval/grading_run.jsonl        ← Luồng B — Grading (sau 17:00)
```

---

## 5. Naming convention — Quy tắc đặt tên file

### 5.1 Run ID format

```
sprint-final          ← Run sạch cuối cùng (canonical)
inject-bad2           ← Run inject lỗi (Sprint 3 demo)
hotfix-20260415T1730  ← Hotfix (nếu cần sửa gấp sau 17:00)
```

Run ID mặc định (nếu không truyền `--run-id`) = `YYYY-MM-DDTHH-MMZ` (UTC).

### 5.2 File naming pattern

| Loại file | Pattern | Ví dụ |
|-----------|---------|-------|
| Manifest | `manifest_<run-id>.json` | `manifest_sprint-final.json` |
| Log | `run_<run-id>.log` | `run_sprint-final.log` |
| Cleaned CSV | `cleaned_<run-id>.csv` | `cleaned_sprint-final.csv` |
| Quarantine CSV | `quarantine_<run-id>.csv` | `quarantine_sprint-final.csv` |
| Eval (test qs) | `before_after_eval.csv` (default) | `before_after_eval.csv` |
| Eval (inject) | `after_inject_bad.csv` | `after_inject_bad.csv` |
| Grading JSONL | `grading_run.jsonl` (default) | `grading_run.jsonl` |

> **Quan trọng:** Các file trong `artifacts/eval/` có tên **cố định** (không có run-id trong tên) — dùng tên mô tả trạng thái (`before_after_eval`, `after_inject_bad`, `grading_run`).

---

## 6. Những file KHÔNG commit

```
chroma_db/            ← Regenerable (có trong .gitignore)
.env                  ← Chứa API key bí mật (có trong .gitignore)
__pycache__/          ← Python bytecode
*.pyc
```

---

## 7. Danh sách commit cuối (18:00 deadline)

### 7.1 Commit cuối — đầy đủ tất cả artifact

```bash
# Kiểm tra danh sách file sẽ commit
git status

# Stage các file artifact và code
git add artifacts/manifests/
git add artifacts/quarantine/
git add artifacts/logs/
git add artifacts/cleaned/
git add artifacts/eval/

# Stage code nếu có thay đổi
git add transform/ quality/ monitoring/
git add etl_pipeline.py eval_retrieval.py grading_run.py
git add requirements.txt
git add docs/
git add reports/
git add contracts/
git add data/grading_questions.json   # chỉ sau 17:00

# Commit
git commit -m "feat: sprint-final artifacts + grading run day10 lab"

git push origin feat/day10-test-sprint
```

### 7.2 Quick checklist trước khi submit

```
✅ artifacts/manifests/manifest_sprint-final.json  (cleaned=6, quarantine=4)
✅ artifacts/quarantine/quarantine_sprint-final.csv (4 dòng, 4 reason khác nhau)
✅ artifacts/eval/before_after_eval.csv             (4 câu, all hits_forbidden=no)
✅ artifacts/eval/after_inject_bad.csv              (q_refund_window hits_forbidden=yes)
✅ artifacts/eval/grading_run.jsonl                 (N dòng = N câu GV phát)
✅ docs/runbook.md, docs/pipeline_architecture.md, docs/data_contract.md
✅ reports/group_report.md, reports/individual/*.md
✅ .env.example (KHÔNG commit .env thật)
```

---

## 8. Timeline ngày nộp bài

| Thời điểm | Việc cần làm |
|-----------|-------------|
| Trước 17:00 | Hoàn thiện code, chạy `sprint-final`, có đủ `before/after_inject_bad.csv` |
| 17:00 | GV phát `grading_questions.json` |
| 17:00–17:30 | Copy file vào `data/`, chạy `python grading_run.py`, kiểm tra output |
| 17:30 | `git add artifacts/eval/grading_run.jsonl data/grading_questions.json` |
| 17:30–17:45 | Final commit + push |
| **18:00** | **Deadline — không push thêm sau giờ này** |

---

*Cập nhật: 2026-04-15 | Nhóm 05-E402*
