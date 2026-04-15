# Kế hoạch phân chia Sprint cho Day 10 - Data Pipeline & Data Observability

Tài liệu này phân rã bài lab Day 10 thành 4 giai đoạn (Sprints), chỉ định rõ file nào cần làm trong giai đoạn nào và vai trò tương ứng của các thành viên.

---

## 📅 Tổng quan các Sprints

| Sprint | Trọng tâm | File chính | Mục tiêu hoàn thành (DoD) |
| :--- | :--- | :--- | :--- |
| **Sprint 1** | **Ingestion & Schema** | `contracts/` & `docs/` | Setup môi trường, chạy được pipeline mộc, hiểu schema. |
| **Sprint 2** | **Cleaning & Quality** | `transform/` & `quality/` | Thêm code xử lý rác (Rule) và bộ lọc (Expectation). |
| **Sprint 3** | **Eval & Evidence** | `eval_retrieval.py` | Có bằng chứng CSV so sánh RAG trả lời Đúng vs Sai. |
| **Sprint 4** | **Monitoring & Reports** | `reports/` & `docs/runbook.md`| Hoàn thiện tài liệu vận hành và báo cáo cá nhân/nhóm. |

---

##  dettaglio nội dung từng Sprint

### 🏃 Sprint 1: Thiết lập & Ingestion (60 phút)
*   **Mục tiêu:** Đảm bảo hệ thống đọc được dữ liệu thô và có "hợp đồng" dữ liệu rõ ràng.
*   **Các file cần xử lý:**
    *   `contracts/data_contract.yaml`: Khai báo chủ sở hữu (Owner), kỳ vọng thời gian (SLA 24h).
    *   `docs/data_contract.md`: Mô tả các trường dữ liệu (`doc_id`, `exported_at`, `chunk_text`).
    *   `etl_pipeline.py`: Chạy lệnh `python etl_pipeline.py run` để kiểm tra logs ghi nhận số lượng record ban đầu.
*   **Vai trò:** *Ingestion Owner*.

### 🧼 Sprint 2: Làm sạch & Kiểm định (60 phút)
*   **Mục tiêu:** Viết logic để loại bỏ hoặc sửa chữa dữ liệu sai/cũ.
*   **Các file cần xử lý:**
    *   `transform/cleaning_rules.py`: Code logic làm sạch. **Cần thêm ít nhất 3 Rule mới** (VD: Xóa ký tự lạ, chuẩn hóa ngày tháng, logic lương thưởng/nghỉ phép).
    *   `quality/expectations.py`: Code logic kiểm thử. **Cần thêm ít nhất 2 Expectation mới** (VD: Cột ngày không được trống, không được chứa từ khóa cấm).
*   **Vai trò:** *Cleaning / Quality Owner*.

### 📊 Sprint 3: Đánh giá & Bằng chứng (60 phút)
*   **Mục tiêu:** Chứng minh việc dọn rác có tác dụng thực tế lên chất lượng câu trả lời của RAG.
*   **Các file cần xử lý/chạy:**
    *   `eval_retrieval.py`: Chạy để xuất ra file kết quả `before_after_eval.csv` (dữ liệu sạch) và `after_inject_bad.csv` (dữ liệu rác).
    *   `docs/quality_report.md`: Tổng hợp bảng so sánh từ 2 file CSV trên. Chỉ ra rõ: "Khi chưa dọn rác RAG trả lời câu hỏi X sai, sau khi dọn đã trả lời đúng".
*   **Vai trò:** *Embed Owner*.

### 📑 Sprint 4: Vận hành & Báo cáo (60 phút)
*   **Mục tiêu:** Dự báo rủi ro và nộp bài đúng hạn.
*   **Các file cần xử lý:**
    *   `docs/runbook.md`: Viết hướng dẫn xử lý khi Pipeline bị dừng (Halt) hoặc dữ liệu bị cũ.
    *   `docs/pipeline_architecture.md`: Vẽ mô hình luồng dữ liệu của nhóm (Ingest -> Clean -> Validate -> Embed).
    *   `reports/group_report.md`: Tổng hợp điểm và vai trò nhóm.
    *   `reports/individual/[ten].md`: Báo cáo cá nhân mỗi thành viên (400-650 chữ).
    *   `grading_run.py`: Chạy lệnh lấy file `grading_run.jsonl` cuối cùng để nộp.
*   **Vai trò:** *Monitoring / Docs Owner*.

---

## 🛠️ Trình tự chạy lệnh (Gợi ý)
1. `python etl_pipeline.py run` (Sprint 1-2)
2. `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate` (Sprint 3 - Test rác)
3. `python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv` (Sprint 3)
4. `python grading_run.py --out artifacts/eval/grading_run.jsonl` (Sprint 4)

---
> [!IMPORTANT]
> Hãy đảm bảo các **Run ID** trong báo cáo khớp với các file thực tế trong thư mục `artifacts/`. Khuyết điểm lớn nhất thường gặp là báo cáo nói làm sạch rồi nhưng trong file JSONL nộp bài vẫn còn dính bằng chứng rác (hits_forbidden=true).
