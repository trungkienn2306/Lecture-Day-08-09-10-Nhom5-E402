# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nông Trung Kiên (Mã học viên: 2A202600414)  
**Vai trò:** Embed / Monitoring (Sprint 3 & 4)  
**Ngày nộp:** 15/04/2026  

---

## 1. Phụ trách chuyên môn (80–120 từ)

**File/Module thực hiện:**
- `day10/lab/monitoring/freshness_check.py`: Cập nhật logic đánh giá Data Freshness đa điểm hỗ trợ đo hai giới hạn ingest và publish.
- Viết kịch bản xử lý chấm điểm (`grading_run.py`) phục vụ tiến trình tự động đánh giá sau thực thi.
- Tham gia tích hợp cấu trúc Embedding và xử lý logic kết nối provider cho luồng Ingestion.

**Kết nối với thành viên khác:**
Quá trình hoàn thiện module `freshness_check.py` phụ thuộc vào nhật ký kết xuất do đầu mối Ingest đảm nhận. Nhờ tham chiếu dữ liệu từ `manifest_sprint-final.json`, module có năng lực phân giải thông số ngày giờ, làm cơ sở để đo lường giới hạn SLA, phối hợp đồng bộ để đưa ra cảnh báo về tính tươi mới của toàn hệ thống trước khi các module khác truy vấn.

**Bằng chứng (Commit thực tiễn):**
Các commit liên quan: `82b32b5` (feat: add custom monitoring/fresh_check) và `cdda5ed` (feat: add openAI provider logic).

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Trong công tác thiết lập module Freshness Check, định hướng kỹ thuật cốt lõi là kiểm soát giới hạn thời gian (SLA) dựa trên cơ chế hai ranh giới phân tách (2-boundary framework): `ingest_boundary_at` và `publish_boundary_at`. Quyết định này thay thế phương pháp tiếp cận mặc định vốn chỉ đánh giá thời lượng xử lý tại một điểm xuất duy nhất (latest exported).

Việc áp dụng song mô hình vừa nêu cho phép nền tảng Observability giám sát mạch lạc hơn. Cụ thể, nếu tiến trình xử lý mất cảnh báo ở cuối chu trình, người vận hành có thể tra soát ngay nguyên nhân tới từ khâu nén file ban đầu hay tại khâu đưa dữ liệu vào cấu trúc ChromaDB. Phương thức đánh giá kép cho luồng xuất kết quả (`check_two_boundary_freshness`) cung cấp cấu trúc trả về tường minh cho hệ thống Runbook, giảm trừ độ trễ trong quá trình khắc phục.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Quá trình đọc tham số SLA đối mặt với ngoại lệ khi hàm `datetime.fromisoformat()` phát sinh lỗi Parsing (ValueError). Triệu chứng biểu hiện ở việc cảnh báo Freshness ngừng thực hiện do đặc tả ISO 8601 chứa phụ tố "Z" (VD: `2026-04-10T08:00:00Z`). Lỗi bắt nguồn từ đặc thù giới hạn tương thích của thư viện Datetime tiêu chuẩn đối với Timezone theo định dạng.

Nhằm giải quyết triệt để rủi ro trên, kịch bản (Mitigation) được điều chỉnh thông qua việc bổ sung cơ chế kiểm duyệt và tinh chuẩn dữ liệu trực tiếp trong hàm `parse_iso(ts)`. Các tiền tố "Z" được thay thế chuẩn tắc thành định dạng tọa độ dịch chuẩn `+00:00` trước khi qua bước convert. Can thiệp này bảo đảm hệ thống kiểm định mốc thời gian không rơi vào Crash Status kể cả khi dữ liệu nguồn bị thay đổi định dạng.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Xác minh logic cách ly dữ liệu rác đối với hệ thống RAG trong quá trình truy xuất file `before_after_eval` và `after_inject_bad` (dựa trên run_id):
- **Trạng thái TRƯỚC (RunID: `after_inject_bad`):** Hệ thống còn xuất hiện tệp văn bản chính sách lỗi thời.
  `q_refund_window, "Khách hàng có bao nhiêu ngày để..." -> hits_forbidden: yes, top1_preview: Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc...`
- **Trạng thái SAU (RunID: `sprint-final`):** Dữ liệu kém chất lượng bị ngăn chặn tại module Expectation.
  `q_refund_window, "Khách hàng có bao nhiêu ngày để..." -> hits_forbidden: no, top1_preview: Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm...`

---

## 5. Cải tiến tiếp theo (40–80 từ)

Quỹ thời gian phụ trợ 2 giờ sẽ được phân bổ để xây dựng tiến trình nền tự động đồng bộ (Background job). Cụ thể, mô hình có thể trích xuất số liệu `quarantine_records` từ file Manifest chạy Batch xuất trực tiếp lên định dạng tương thích Metric Server, hỗ trợ xây dựng Dashboard giám sát SLA trực quan (như Grafana / Prometheus) nhằm tạo bộ đệm cho Runbook hiện tại.
