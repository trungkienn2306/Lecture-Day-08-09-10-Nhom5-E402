# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Bùi Thế Công  
**Vai trò:** Ingestion Owner — Thiết lập Data Contract & Manifest (Sprint 1)  
**Ngày nộp:** 15/04/2026  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
- `contracts/data_contract.yaml`: Tôi đã mở rộng và chuẩn hóa toàn bộ file này từ phiên bản 1.0 lên 1.1, thiết lập các bộ quy tắc (Quality rules, Cleaning rules summary) và mở rộng cấu hình (Freshness tính bằng 2 biên, Schema cleaned ràng buộc chặt - thêm rule min_chars_env, max_days_env).
- `docs/data_contract.md`: Đồng bộ tài liệu markdown với file YAML.
- `etl_pipeline.py` (giám sát log): Hỗ trợ chạy Sprint 1 bằng terminal, sinh và kiểm tra các log/manifest.

**Kết nối với thành viên khác:**
Tôi tạo ra "hợp đồng" cấu trúc dữ liệu chặt chẽ ở giai đoạn Ingest. Các tham số như cấm BOM, min characters, và freshness boundaries (ingest/publish) mà tôi xác lập là yêu cầu khắt khe để Data Pipeline team thiết kế các quy tắc Cleaning & Expectation hợp lệ trong Sprint 2 và 3.

**Bằng chứng (commit / comment trong code):**
Đóng góp rõ nhất ở file `data_contract.yaml` dòng khai báo `version: "1.1"` và thiết kế mảng cấu hình đa dạng (`freshness` boundaries, `policy_versioning` bằng tham số không hard-code). Song song là việc chạy pipeline ghi nhận `run_id=sprint1`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định đáng kể nhất của tôi khi lên kế hoạch contract là thiết lập tham số **`freshness` đa ranh giới (2 boundaries)** thay vì chỉ một điểm duy nhất (Mục Freshness SLA). Bằng cách thiết lập kiểm tra SLA ở thời điểm `ingest` (sau `load_raw_csv`) và thời điểm `publish` (sau khi embed thành công vào ChromaDB collection `day10_kb`), tôi giúp cho hệ thống phân định được SLA bottleneck. Nếu dữ liệu Fresh nhưng ở VectorDB quá cũ, lỗi nằm ở logic Pipeline; nếu bản thân dữ liệu raw đã cũ (như dữ liệu log export bị ngâm 1 tuần), lỗi do quy trình Source của đội Policy/HR. Đây cũng là một tiêu chí đáp ứng mục tiêu **Distinction** (bonus point) trong chấm điểm. Việc quản lý bằng hệ biến môi trường (như `HR_LEAVE_MIN_EFFECTIVE_DATE`) cũng hạn chế hard-code.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Trong lúc rà soát manifest sinh ra từ Sprint 1, hệ thống giám sát cảnh báo: _"Freshness check FAIL: age_hours=121.1"_. Ban đầu đây có vẻ là một lỗi, vì dữ liệu mới đưa vào mà đã bị báo cũ (stale data alert). Lỗi này xuất phát từ việc trường `exported_at` của bộ dữ liệu CSV thô `policy_export_dirty.csv` rơi vào ngày 2026-04-10, vượt qua cấu hình chuẩn `FRESHNESS_SLA_HOURS=24`.
Thay vì hạ tiêu chuẩn bằng cách nới lỏng cấu hình SLA thành vô hạn, tôi quyết định vẫn ghi nhận đây là `FAIL` trong file log chạy hiện tại để minh chứng quy tắc Data Observability đang kiểm soát đúng mạch (broken pipe simulation). Đối với kịch bản tích hợp thực tế, chúng tôi sẽ xử lý dữ liệu với ngày xuất export hiện tại thay vì ghi đè config.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Tôi cung cấp bằng chứng cho quá trình Ingestion và cách lý dữ liệu thành công trong chạy `run-id=sprint1`:
- **Trước**: Tập dữ liệu raw `policy_export_dirty.csv` chứa 10 bản ghi gồm nhiều nhiễu sóng (trùng lắp text, sai ngày tháng, tài liệu vô danh).
- **Sau (Trích xuất log run_sprint1.log):**
```text
run_id=sprint1
raw_records=10
cleaned_records=6
quarantine_records=4
manifest_written=artifacts\manifests\manifest_sprint1.json
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 121.113, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```
Dữ liệu sạch (6 records) được nạp vào ChromaDB `day10_kb`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm thời gian, tôi sẽ trực tiếp hiện thực hoá rule kiểm tra **Pydantic Model Validation** theo đúng expectation `pydantic_schema_validation` mà tôi đã thêm vào Data Contract. Bằng cách định nghĩa bảng mô phỏng `CleanedChunk(BaseModel)`, pipeline sẽ tự động bắt các lỗi định dạng ISO-8601 mà không cần viết các khối RegExp cồng kềnh.