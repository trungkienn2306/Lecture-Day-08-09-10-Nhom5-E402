# Sprint 1 (60') — Refactor Graph

**Tệp tin làm việc chính:** `graph.py`

## Bối cảnh
RAG pipeline từ Day 08 là một khối "monolith" (thực hiện tất cả chức năng retrieve → generate trong cùng một hàm). Nhiệm vụ của Sprint 1 là "đập đi xây lại" (refactor) quá trình này thành một cấu trúc đồ thị đa tác nhân (Multi-Agent Graph), được điều phối linh hoạt thông qua một Agent (Supervisor).

## Các công việc cần làm

### 1. Định nghĩa `AgentState`
- Cần định nghĩa kiến trúc cho `AgentState` để làm *shared state* (trạng thái dùng chung) lưu chuyển qua xuyên suốt quá trình thực thi graph.
- Yêu cầu bắt buộc object thuộc state này phải có các biến lưu trữ sau:
  - `task`: Yêu cầu thực tế lưu từ input
  - `route_reason`: Ghi chú lại lý do điều hướng tới agent tiếp theo
  - `history`: Lược sử (nếu có)
  - `risk_high`: Đánh dấu trạng thái rủi ro.

### 2. Cài đặt `supervisor_node()`
- Chịu trách nhiệm khởi tạo hàm `supervisor_node()` để đọc giá trị đầu vào (task) và quyết định luồng rẽ (route) đến node nào để thực hiện.

### 3. Cài đặt hệ thống `route_decision()`
- Hàm `route_decision()` chứa các cài đặt phân tích câu lệnh truy vấn từ user cộng hưởng với cờ rủi ro (risk flag) nếu có.
- **Gợi ý tham khảo logic định tuyến:**
  - Nếu task chứa "hoàn tiền", "refund", "policy" $\rightarrow$ điều hướng tới tới `policy_tool_worker`
  - Nếu task chứa "cấp quyền", "access", "emergency" $\rightarrow$ điều hướng tới `policy_tool_worker`
  - Nếu task chứa "P1", "escalation", "ticket" $\rightarrow$ điều hướng tới `retrieval_worker` (nhằm độ ưu tiên cao)
  - Nếu task chứa mã lỗi không rõ $\rightarrow$ điều hướng `human_review`
  - Các trường hợp cơ bản khác $\rightarrow$ điệu hướng tới `retrieval_worker`

### 4. Kết nối Graph
- Thực hiện nối các Nodes và Edges theo đúng luồng dự kiến: `supervisor → route → [retrieval | policy_tool | human_review] → synthesis → END`

### 5. Khởi chạy thử nghiệm (Testing)
- Gọi thực thi hàm `graph.invoke()` với tối thiểu 2 test queries mang đặc thù khác nhau để kiểm chứng khả năng phân định luồng đi.

## Tiêu chí hoàn thành (Definition of Done)
- [x] Chạy file main bằng lệnh `python graph.py` và không gặp lỗi (crash / error).
- [x] Supervisor chọn đúng đường đi theo đúng luồng định tuyến (với ít nhất 2 loại câu hỏi khác nhau, VD logic retrieval và policy).
- [x] Có thực hiện log thông tin định tuyến (lưu log `route_reason`) cho mỗi bước chuyển.
- [x] Đảm bảo State object đi xuyên suốt graph và luôn duy trì chứa đầy đủ các trường: `task`, `route_reason`, `history`, `risk_high`.
