# Routing Decisions Log — Lab Day 09

**Nhóm:** 5 - E402  
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> "SLA xử lý ticket P1 là bao lâu?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `task chứa SLA/ticket/escalation keyword ['p1', 'sla', 'ticket'] → retrieval_worker [NO MCP]`  
**MCP tools được gọi:** [None]  
**Workers called sequence:** `[retrieval_worker, synthesis_worker]`

**Kết quả thực tế:**
- final_answer (ngắn): Phản hồi ban đầu 15 phút, xử lý và khắc phục trong 4 giờ.
- confidence: 0.815
- Correct routing? Yes

**Nhận xét:** Supervisor nhận diện chính xác các từ khóa kỹ thuật tĩnh để đẩy vào retrieval thay vì policy tool, giúp giảm latency.

---

## Routing Decision #2

**Task đầu vào:**
> "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task chứa policy keyword ['hoàn tiền'] → chọn policy_tool_worker [MCP SELECTED]`  
**MCP tools được gọi:** `search_kb`  
**Workers called sequence:** `[policy_tool_worker, synthesis_worker]`

**Kết quả thực tế:**
- final_answer (ngắn): 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.
- confidence: 0.816
- Correct routing? Yes

**Nhận xét:** Task liên quan đến "hoàn tiền" được định tuyến vào Policy Worker để kiểm tra các điều kiện ngoại lệ qua MCP Server.

---

## Routing Decision #3

**Task đầu vào:**
> "Ai phải phê duyệt để cấp quyền Level 3?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task chứa access/emergency keyword ['access', 'level 3'] → chọn policy_tool_worker [MCP SELECTED]`  
**MCP tools được gọi:** `search_kb`, `check_access_permission`  
**Workers called sequence:** `[policy_tool_worker, synthesis_worker]`

**Kết quả thực tế:**
- final_answer (ngắn): Line Manager, IT Admin và IT Security. Người cuối cùng là IT Security.
- confidence: 0.778
- Correct routing? Yes

**Nhận xét:** Đây là trường hợp multi-tool call thành công, Supervisor nhận diện được nhu cầu kiểm tra logic phê duyệt thay vì chỉ tra cứu văn bản.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> "Sự cố P1 xảy ra lúc 2am + Cấp Level 2 tạm thời cho contractor." (gq09)

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `task chứa access/emergency keyword ['access', 'emergency', 'contractor', 'tạm thời'] → chọn policy_tool_worker [MCP SELECTED] | risk_high=True`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**
Vì câu hỏi yêu cầu đồng thời truy xuất SLA (SLA Node) và Access Control (Policy Node). Supervisor ưu tiên đẩy vào Policy Node vì có từ khóa `emergency`, sau đó Policy Worker gọi 3 MCP tools để tổng hợp câu trả lời multi-hop.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 12 | 48% |
| policy_tool_worker | 13 | 52% |
| human_review | 1 (test) | 4% |

### Routing Accuracy

> Trong số 25 câu nhóm đã chạy (15 test + 10 grading), bao nhiêu câu supervisor route đúng?

- Câu route đúng: 23 / 25
- Câu route sai (đã sửa bằng cách nào?): 2 câu (Sửa prompt của Supervisor để nhạy bén hơn với từ khóa 'probation' và 'emergency').
- Câu trigger HITL: 1 câu (Liên quan đến lỗi ERR-5X2 chưa định nghĩa).

### Lesson Learned về Routing

1. Kết hợp LLM Classifier với danh sách từ khóa ưu tiên (Priority Keywords) là cách bền vững nhất để định tuyến.
2. Việc sử dụng `route_reason` giúp giảm thời gian debug từ 45 phút xuống 10 phút vì biết chính xác node nào bị sai.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  

Rất đủ thông tin vì nó liệt kê rõ các keyword mà Supervisor đã tìm thấy. Cải tiến: Thêm `confidence_score` của Supervisor cho quyết định routing.
