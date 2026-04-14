# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Bùi Thế Công  
**Vai trò trong nhóm:** MCP Owner / Trace & Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án Lab Day 09, tôi đảm nhận sự kết hợp giữa hai vai trò **MCP Owner** và **Trace & Docs Owner**. Trọng tâm công việc của tôi là xây dựng cầu nối giữa Agent và các hệ thống dữ liệu bên ngoài, đồng thời thiết kế bộ khung đánh giá hiệu năng hệ thống.

**Module/file tôi chịu trách nhiệm:**
- **File chính:** `mcp_server.py`, `eval_trace.py`, `docs/*`, `artifacts/*`.
- **Sprint 3 (Advanced):** Tôi đã triển khai **Advanced MCP Server** sử dụng framework **FastAPI**. Thay vì chỉ dùng Mock Class đơn giản, tôi đã xây dựng một REST API thực sự chạy trên cổng 8765, mô phỏng các dịch vụ Jira (ticket tra cứu) và Access Control System (kiểm tra quyền hạn).
- **Sprint 4:** Hoàn thiện `eval_trace.py` với các logic tính toán metrics và so sánh Delta hiệu năng giữa Single-Agent (Day 08) và Multi-Agent (Day 09). Tôi cũng phụ trách cùng team tổng hợp dữ liệu thực tế từ 25 traces (15 test questions và 10 grading questions) để điền vào các tài liệu kiến trúc hệ thống.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi cung cấp các API công cụ (tools) để `policy_tool_worker` của bạn Worker Owner gọi tới. Cuối cùng, tôi sử dụng file `graph.py` của bạn Supervisor Owner để chạy bộ câu hỏi test và grading, trích xuất dữ liệu cho cả nhóm.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
File `mcp_server.py` với kiến trúc FastAPI (app, endpoints `/tools`, `/tools/{tool_name}`) là minh chứng cho phần Advanced mà tôi đã thực hiện.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Sử dụng **FastAPI để triển khai MCP Server (HTTP Layer)** thay vì Mock Function truyền thống.

**Lý do:**
Việc sử dụng Multi-Agent Orchestration đòi hỏi tính module hóa cao. Nếu chỉ dùng Mock Class trong cùng một process, chúng ta sẽ không thấy được các vấn đề về độ trễ mạng (network latency) hoặc serialization dữ liệu. Tôi chọn FastAPI vì:
1. **Tính chân thực:** Giả lập sát nhất môi trường production nơi các Agent giao tiếp với CRM/ERP qua API.
2. **Khả năng mở rộng:** Dễ dàng bổ sung thêm các tool mới (như `create_ticket`) và kiểm tra tính hợp lệ của Input Schema bằng Pydantic.
3. **Observability:** Dễ dàng theo dõi Access Logs của server để biết Worker nào đang gọi tool gì, vào lúc nào.

**Trade-off đã chấp nhận:**
Hệ thống phức tạp hơn vì phải quản lý thêm một process server riêng biệt. Điều này đôi khi gây lỗi "Connection Refused" nếu người dùng quên khởi động server trước khi chạy graph, nhưng tôi đã bổ sung hướng dẫn rõ ràng trong README.md để khắc phục.

**Bằng chứng từ trace/code:**
Đoạn code định nghĩa endpoint thực thi tool linh hoạt trong `mcp_server.py`:
```python
@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: Dict[str, Any]):
    print(f"  [MCP Server] Received request for tool: {tool_name}")
    args = request.get("arguments", request) # Xử lý linh hoạt payload
    result = dispatch_tool(tool_name, args)
    return result
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Phần tôi làm không gặp lỗi.

**Symptom (pipeline làm gì sai?):**


**Root cause (lỗi nằm ở đâu?):**


**Cách sửa:**

**Bằng chứng trước/sau:**
- **Trước:** 
- **Sau:** 

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã triển khai thành công MCP Server theo hướng **Advanced** sử dụng **FastAPI**, giúp hệ thống có khả năng mở rộng như một service độc lập. Đồng thời, tôi đã tối ưu hóa `eval_trace.py` để tách biệt hoàn toàn luồng chạy của 15 câu **test questions** (lưu vào `traces/test`) và 10 câu **grading questions** (lưu vào `traces/grading` và `grading_run.jsonl`). Việc tự động sinh ra các file `eval_report` riêng cho từng bộ câu hỏi giúp nhóm dễ dàng đối soát kết quả.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa triển khai được cơ chế **đánh giá điểm raw tự động**. Hiện tại việc chấm điểm vẫn phải làm thủ công bằng cách đối chiếu kết quả trong `grading_run.jsonl` với danh sách `grading_criteria` từ file `grading_questions.json`, dẫn đến việc nhóm không biết ngay được scorecard cuối cùng theo `SCORING.md`.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm phụ thuộc vào tôi ở tầng hạ tầng tools (MCP Server) và hệ thống đo lường hiệu năng. Nếu script eval của tôi gặp lỗi, nhóm sẽ không có bằng chứng (traces/log) để nộp bài đúng kết quả.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần Supervisor và các Worker (như `policy_tool`) hoàn thiện logic gọi tool để có dữ liệu thực tế cho báo cáo đánh giá.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm 2 giờ, tôi sẽ triển khai module **LLM-Auto-Grader**. Tôi sẽ dùng một con LLM (như GPT-4o) để tự động đọc `grading_run.jsonl` và đối chiếu với `grading_criteria` của từng câu hỏi trong `grading_questions.json`. Việc tự động hóa này đặc biệt quan trọng cho các câu khó như `gq09` (multi-hop) vì nó giúp nhóm biết ngay mình có đạt đủ 16 điểm raw hay không để kịp thời điều chỉnh prompt thay vì phải chấm thủ công rất mất thời gian.

---

