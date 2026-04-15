# Hướng dẫn chi tiết Bài tập Day 10 - Data Pipeline & Data Observability

Tài liệu này được viết nhằm giải thích mục đích của bài lab Day 10, hướng dẫn chi tiết các bước chạy, và làm rõ cấu trúc cũng như ý nghĩa của các file được sinh ra (CSV, JSON, JSONL), các file cần phải nộp, và các metrics được dùng để chấm điểm.

---

## 1. Bài tập Day 10 làm gì?

Bài tập Day 10 tập trung vào phần **Dữ liệu (Data)** (cụ thể là **Data Pipeline** và **Data Observability**) cho hệ thống RAG đã được xây dựng từ Day 08 và Day 09. Thay vì coi dữ liệu đầu vào là hoàn hảo, thực tế dữ liệu từ hệ thống nội bộ (như HR, Helpdesk, Policy) thường:
- Có file rác (encoding lỗi, dữ liệu trống).
- Lệch chuẩn thời gian (sai format).
- Quan trọng nhất: **Gây xung đột nghiệp vụ** (Ví dụ: policy cũ nói nhân viên được nghỉ 10 ngày, policy mới bảo 12 ngày; hoặc chính sách hoàn tiền cũ là 14 ngày thay vì 7 ngày mới).

**Mục tiêu của bài thực hành:**
- Xây dựng một luồng (ETL) tải dữ liệu `Ingest` -> làm sạch `Clean` -> kiểm định chất lượng `Validate (Expectations)` -> đẩy vào DB Vector `Embed`.
- Sử dụng mô hình **Data Observability**: Hệ thống phải phát hiện sự cố dữ liệu, tự động chặn lại (Halt pipeline) và lưu dữ liệu bẩn vào khu vực cách ly (Quarantine) thay vì đưa lên cho RAG Model đọc linh tinh.
- Nêu bật khái niệm **Before vs After**: Đánh giá câu trả lời của mô hình RAG sẽ tốt đến nào nếu ta có một Data Pipeline tốt.

---

## 2. Cách chạy bài tập lần lượt (Flow 4 Sprints)

Bạn mở terminal tại đường dẫn thư mục `day10/lab/`.

### Bước 0: Khởi tạo môi trường
```bash
python -m venv .venv
source .venv/bin/activate   # Với Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Bước 1 & 2: Chạy Data Pipeline Chuẩn (Ingest -> Clean -> Embed)
Mục tiêu là chạy pipeline để đọc file CSV raw (chứa dữ liệu chưa sạch), làm sạch chúng bằng các "Rules" và "Expectation", sau đó embed vào ChromaDB.

```bash
# Chạy toàn bộ pipeline ETL
python etl_pipeline.py run
```
Cái gì diễn ra bên trong:
- Đọc file `data/raw/policy_export_dirty.csv`.
- Đẩy qua các rule trong `transform/cleaning_rules.py` (loại bỏ record sai, fix cửa sổ hoàn tiền 14 ngày -> 7 ngày).
- Qua `quality/expectations.py` để kiểm định (pass/warn/halt).
- Đẩy dữ liệu sạch vào `chroma_db` (collection `day10_kb`), **upsert theo `chunk_id` và prune chunk cũ** — đảm bảo chạy 2 lần liên tiếp không phình collection.

### Bước 3: Inject dữ liệu hỏng & So sánh Trước/Sau
Bạn cần minh họa rằng: nếu thả cửa cho dữ liệu xấu đi vào db thì RAG sẽ trả lời sai. Do đó ta sẽ cố tình bỏ các bước sửa dữ liệu:

```bash
# Bỏ qua fix số ngày hoàn tiền và skip expectation (bỏ cơ chế chặn) để bắt Chroma nhai dữ liệu bẩn
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate

# Sinh file đánh giá lúc dữ liệu bị bẩn (trạng thái BEFORE fix — "before" trong before/after)
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
```

Sau đó, bạn lại làm sạch dữ liệu và chấm lại:
```bash
# Chạy pipeline sạch chuẩn (prune chunk bẩn ra khỏi ChromaDB, đưa về trạng thái đúng)
python etl_pipeline.py run

# Sinh file đánh giá lúc dữ liệu SẠCH (trạng thái AFTER fix — "after" trong before/after)
python eval_retrieval.py --out artifacts/eval/before_after_eval.csv
```

> **Lưu ý tên file:** `after_inject_bad.csv` là trạng thái **TRƯỚC khi fix** (sau khi inject rác), còn `before_after_eval.csv` là trạng thái **SAU khi fix** (pipeline sạch). Tên file đặt theo thời điểm chạy, không phải thứ tự tốt/xấu — đừng nhầm chiều.

Hãy mở 2 file CSV này và đưa chứng cứ so sánh vào báo cáo (Quality Report). Cột quan trọng cần so sánh: `hits_forbidden` (no = sạch, yes = còn rác lọt) và `contains_expected` (yes = trả lời đúng).

### Bước 4: Kiểm tra độ tươi của dữ liệu (Freshness) và Chấm điểm tự động
Khi dữ liệu đến quá ngày thiết lập, pipeline sẽ bắt đầu cảnh báo (tính theo file run manifest):
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json
```

Xuất file chấm điểm JSONL **(chỉ chạy sau 17:00 khi GV public bộ câu hỏi)**:
```bash
# Đảm bảo collection đang ở trạng thái SẠCH trước khi chạy (pipeline chuẩn, không --no-refund-fix)
python etl_pipeline.py run

# Chạy grading
python grading_run.py --out artifacts/eval/grading_run.jsonl
```

Tự kiểm tra artifact trước khi nộp (dùng script GV):
```bash
python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl
python instructor_quick_check.py --manifest artifacts/manifests/manifest_<run-id>.json
```

> **Deadline:** Code + artifact bắt buộc commit trước **18:00**. Sau 18:00 chỉ còn `reports/` được nộp muộn (tùy quy định lớp).

---

## 2b. Quy trình sau 17:00 — Nhận file Grading Questions và nộp bài

> Thực hiện **theo đúng thứ tự** bên dưới. Toàn bộ quy trình từ nhận file đến push xong khoảng **20–30 phút**.

### Bước 1 — Đảm bảo collection đang ở trạng thái SẠCH

Trước khi chạy grading, ChromaDB **phải** ở trạng thái sprint-final (không có chunk inject-bad).  
Kiểm tra nhanh — số chunk phải đúng 6:

```powershell
python -c "import chromadb; c = chromadb.PersistentClient('./chroma_db'); col = c.get_collection('day10_kb'); print('chunk count:', col.count())"
```

Nếu kết quả **≠ 6**, chạy lại pipeline sạch:

```bash
python etl_pipeline.py run --run-id sprint-final
# Chờ đến dòng: PIPELINE_OK
```

---

### Bước 2 — Nhận file `grading_questions.json` từ Giảng viên

Giảng viên sẽ gửi file `grading_questions.json` qua Teams / LMS / email.  
Copy file đó vào thư mục đúng vị trí:

```bash
# Windows (thay <đường-dẫn-GV-gửi> bằng vị trí file thật)
copy "<đường-dẫn-GV-gửi>\grading_questions.json" "data\grading_questions.json"

# Hoặc Linux/macOS
cp /path/to/grading_questions.json data/grading_questions.json
```

Kiểm tra file đã vào đúng chỗ:

```powershell
# Đếm số câu hỏi (Windows PowerShell)
python -c "import json; qs = json.load(open('data/grading_questions.json', encoding='utf-8')); print('So cau hoi:', len(qs)); [print(' -', q['id']) for q in qs]"
```

> **Hoặc xem thô nhanh hơn:**
> ```powershell
> type data\grading_questions.json
> ```

---

### Bước 3 — Chạy Grading

```bash
python grading_run.py \
  --questions data/grading_questions.json \
  --out artifacts/eval/grading_run.jsonl \
  --top-k 5
```

Lệnh này sẽ in ra: `Wrote artifacts/eval/grading_run.jsonl`

---

### Bước 4 — Kiểm tra kết quả JSONL

Đọc nhanh kết quả để tự đánh giá trước khi nộp:

```powershell
# Windows PowerShell — chạy script kiểm tra
python scripts/check_grading.py
```

Nếu chưa có script, dùng lệnh một dòng (PowerShell):

```powershell
python -c "import json; lines=open('artifacts/eval/grading_run.jsonl',encoding='utf-8').readlines(); [print('[OK]' if r['contains_expected'] and not r['hits_forbidden'] else '[FAIL]', r['id'], '| contains_expected=' + str(r['contains_expected']) + ', hits_forbidden=' + str(r['hits_forbidden'])) for r in [json.loads(l) for l in lines]]"
```

**Kết quả mong đợi (để đạt Merit/Distinction):**

```
Tổng số dòng: 3

  [OK] gq_d10_01
         contains_expected=True, hits_forbidden=False
  [OK] gq_d10_02
         contains_expected=True, hits_forbidden=False
  [OK] gq_d10_03
         contains_expected=True, hits_forbidden=False, top1_doc_matches=True
```

Nếu bất kỳ câu nào `hits_forbidden=True` → collection vẫn còn chunk bẩn → quay lại Bước 1, chạy lại `etl_pipeline.py run` (không có `--no-refund-fix`), rồi chạy lại grading.

---

### Bước 5 — Kiểm tra nhanh toàn bộ artifact (nếu GV có script)

```bash
python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl
python instructor_quick_check.py --manifest artifacts/manifests/manifest_sprint-final.json
```

---

### Bước 6 — Commit và Push trước 18:00

```bash
# Stage tất cả artifact và file grading
git add data/grading_questions.json
git add artifacts/eval/grading_run.jsonl
git add artifacts/eval/before_after_eval.csv
git add artifacts/eval/after_inject_bad.csv
git add artifacts/manifests/
git add artifacts/quarantine/
git add artifacts/logs/
git add artifacts/cleaned/

# Stage code và tài liệu (nếu còn chỉnh sửa)
git add transform/ quality/ monitoring/
git add etl_pipeline.py eval_retrieval.py grading_run.py
git add docs/ reports/ contracts/
git add requirements.txt

# Kiểm tra những gì sẽ commit
git status

# Commit
git commit -m "feat: sprint-final artifacts + grading run day10"

# Push
git push origin feat/day10-test-sprint
```

Sau khi push, verify trên GitHub/GitLab rằng file `artifacts/eval/grading_run.jsonl` đã có mặt trong repo.

---

### Checklist 5 phút trước khi nộp

```
✅ artifacts/manifests/manifest_sprint-final.json    (cleaned_records=6, quarantine_records=4)
✅ artifacts/quarantine/quarantine_sprint-final.csv  (4 dòng, 4 reason khác nhau)
✅ artifacts/eval/before_after_eval.csv              (4 câu, tất cả hits_forbidden=no)
✅ artifacts/eval/after_inject_bad.csv               (q_refund_window có hits_forbidden=yes)
✅ artifacts/eval/grading_run.jsonl                  (N dòng = N câu GV phát, mọi contains_expected=true)
✅ data/grading_questions.json                       (file GV phát — đã commit)
✅ docs/runbook.md, pipeline_architecture.md, data_contract.md, quality_report.md
✅ reports/group_report.md + reports/individual/*.md
✅ chroma_db/ KHÔNG xuất hiện trong git status (đã gitignore)
✅ .env KHÔNG xuất hiện trong git status (đã gitignore)
```

> **Deadline cứng: 18:00.** Nếu push muộn hơn, chỉ `reports/` được nộp bổ sung theo quy định lớp.

---

## 3. Các files sinh ra trong quá trình chạy (Artifacts)

Tất cả các output sẽ được tự động tống vào nhánh `day10/lab/artifacts/`.

### 1) Các Logs chạy (`artifacts/logs/`)
- Mẫu `run_<run-id>.log`: Ghi lại chi tiết logs (số lượng raw_records nạp vô, số lượng cleaned_records đã dọn, bao nhiêu bị cách ly (quarantine), tiến trình Validate (OK/FAIL), logs embed).

### 2) Dữ liệu Cách ly (`artifacts/quarantine/`)
- Trả về file `quarantine_<run-id>.csv`: File này chứa các data chunks BỊ LOẠI BỎ. Có chứa một trường quan trọng nhất phải nắm:
  - Trường `reason`: Lý do loại bỏ (vd: `encoding_corruption_in_chunk_text`, `stale_hr_policy_effective_date`, `future_effective_date_exceeds_threshold`,...).

### 3) Báo cáo Manifest sau khi nhồi (`artifacts/manifests/`)
- File `manifest_<run-id>.json`: Đây là bill/hóa đơn chạy của hệ thống pipeline. Trong đó có các trường quan trọng:
  - `run_id`: Tên ID lần nạp đó.
  - `raw_records` / `cleaned_records` / `quarantine_records`: Số lượng văn bản (chunks) ban đầu / sau sạch / bị rác.
  - `ingest_boundary_at` & `publish_boundary_at`: Mốc thời gian hệ thống nạp csv raw & mốc thời gian hệ thống lưu thành công vào ChromaDB (dùng cho Freshness 2-boundary).
  - `embed_prune_removed`: Số chunk cũ bị xóa khỏi collection khi re-run (= 0 nếu chạy 2 lần cùng input → idempotency xác nhận).

### 4) File kết quả (CSV) đánh giá Eval Retrieval (`artifacts/eval/`)
Gồm các file csv mà bạn chạy ra lúc nãy (`before_after_eval.csv` và `after_inject_bad.csv`). Gồm các trường quan trọng:
- `question_id`: ID câu hỏi test (vd: `q_refund_window`, `q_leave_version`).
- `question`: Nội dung câu hỏi.
- `top1_doc_id`: ID của tài liệu RAG lôi lên đầu tiên.
- `top1_preview`: Đoạn văn ngắn đầu tiên từ chunk được lấy ra (để đọc kiểm tra tay).
- `contains_expected`: *(Metric đo lường quan trọng)* Câu trả lời có đúng ý (VD: Có chữ "7 ngày", "12 ngày") không? Trả về `yes`/`no`.
- `hits_forbidden`: RAG có lôi lên chunk rác/hết hạn (vd: "14 ngày làm việc", "10 ngày phép năm") không? Trả về `yes`/`no`. **Phải là `no` trong run sạch.**
- `top1_doc_expected`: Chunk top-1 có từ đúng tài liệu kỳ vọng không? (`yes`/`no` hoặc bỏ trống nếu câu hỏi không yêu cầu).
- `top_k_used`: Số chunk tìm kiếm (thường là 3).

> **Lưu ý:** Pipeline dùng **keyword retrieval** (không gọi LLM), nên không có trường `llm_answer`. `hits_forbidden` quét toàn bộ top-k chunk ghép lại để phát hiện "câu trả lời trông đúng nhưng context vẫn còn chunk stale".

### 5) File nộp JSONL chấm tự động (`artifacts/eval/grading_run.jsonl`)
File có đuôi JSONL (viết tắt của JSON Lines, mỗi dòng trên text là một cấu trúc chuỗi JSON valid).
- Dùng phục vụ chấm code tự động cho 3 Câu Hỏi Vàng (`gq_d10_01` tới `gq_d10_03`).
- File phải có **đúng 3 dòng**, mỗi dòng JSON hợp lệ (không có dấu phẩy thừa, không bọc trong array `[]`).
- **Để đạt điểm cao**, file JSONL phải đảm bảo:
  - `contains_expected=true`: Trả lời đúng trọng tâm.
  - `hits_forbidden=false`: RAG không được phép thấy dòng luật cũ vì bạn được yêu cầu làm ETL phải "xóa/rút rác" khỏi db.
  - Dòng 3 (`gq_d10_03`) yêu cầu thêm `top1_doc_matches=true`: Trả về đúng tài liệu top-1 liên quan.

---

## 4. Danh sách các file PHẢI NỘP

Bạn cần chuẩn chỉnh các code và report sau để nộp theo như barem điểm `SCORING.md`.

> **Deadline cứng 18:00:** Các mục A, B, C bắt buộc commit trước 18:00. Mục D (reports) theo quy định lớp (thường cho phép muộn hơn).

### A. Source code (Sự đóng góp của nhóm)
1. `transform/cleaning_rules.py`: Chứa các quy tắc làm sạch dữ liệu. Lưu ý phải phát triển ít nhất ≥ 3 Rules mới so với code được giảng viên cho.
2. `quality/expectations.py`: Chứa các kỳ vọng chất lượng, kiểm thử testcase (Vượt qua hay Halt / Dừng pipeline). Phải thêm ≥ 2 Expectation mới phục vụ bắt dính rác.
3. `contracts/data_contract.yaml`: Điền thông tin Data Owner (thành viên quản lý kho data), SLA...

### B. Artifact run minh chứng
1. Tất cả file trong folder `artifacts/` — cụ thể là: `artifacts/manifests/`, `artifacts/quarantine/`, `artifacts/cleaned/`, `artifacts/eval/` (log, jsonl, csv evaluation before/after).
2. **Không commit** thư mục `chroma_db/` ở root (vector database tự regenerate được, đã có trong `.gitignore`).

### C. Tài liệu hệ thống và vận hành (Docs Folder)
1. `docs/pipeline_architecture.md`: Bạn tự vẽ và giải thích luồng thiết kế Data pipeline sơ đồ Ingest -> Clean -> Embed.
2. `docs/data_contract.md`: Document mô tả metadata, schema luồng dữ liệu (có source map).
3. `docs/quality_report.md`: Báo cáo chất lượng — phải có bảng `metric_impact` chứng minh từng rule/expectation mới có tác động đo được, bảng expectation pass/fail, và bằng chứng before/after retrieval.
4. `docs/runbook.md`: Quy trình gỡ rối (Troubleshooting guide / Runbook) khi Pipeline bị HALT, Data Freshness bị dính cảnh báo. Đủ 5 mục: Triệu chứng (Symptom) -> Detection -> Diagnosis -> Mitigation -> Prevention.

### D. File báo cáo (Report)
1. `reports/group_report.md`: Báo cáo quá trình làm chung cả nhóm. Phải có bảng `metric_impact` liệt kê tác động của từng Cleaning rules mà nhóm đã thêm (vd: thêm rule 7 thì bị loại thêm bao nhiêu record).
2. `reports/individual/[ten_thanh_vien].md`: Báo cáo từ từng thành viên trong nhóm (Dài 400 - 650 chữ).
   - Nội dung yêu cầu: Vai trò (Ingestion Owner / Cleaning Quality / Embed / Monitor), Quyết định kỹ thuật thiết kế, một Lỗi gặp phải và evidence fix lỗi, một dòng before/after tự chọn, và đề xuất cải tiến 2h.

### Giải thích lại Metrics Chấm thi (Dựa trên `SCORING.md`)
- **Pass (Trung bình):** System Run mượt (Exit 0), code đủ rule mới (≥3 Cleaning, ≥2 Expectation), file JSONL qua được 2 câu đầu (`gq_d10_01` `contains_expected=true` + `hits_forbidden=false`, `gq_d10_02` `contains_expected=true`).
- **Merit (Khá Giỏi):** Pass + câu 3 (`gq_d10_03`) đạt đủ `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true`; có chứng cứ eval cho `q_leave_version` (HR bản 2025 đã bị quarantine, bản 2026 trả lời đúng "12 ngày phép năm").
- **Distinction (Xuất Sắc):** Merit + ít nhất một trong: (a) cài và import package `pydantic` thật để validate schema cleaned; (b) log freshness ở **2 boundary** (ingest + publish) có minh chứng trong manifest; (c) rule versioning không hardcode cutoff date, đọc từ env var hoặc contract.

**=> Lời khuyên cuối:** Bạn hãy đọc thật kĩ file báo cáo nhóm để đồng bộ "Bảng vai trò cá nhân", không mâu thuẫn report ↔ repo. Các code đóng góp bắt buộc thể hiện tác dụng vật lý (giảm record, tạo lỗi halt) chứ không chỉ viết quy tắc vô thưởng vô phạt.
