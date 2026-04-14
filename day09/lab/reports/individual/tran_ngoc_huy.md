# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Ngọc Huy
**Vai trò trong nhóm:** Supervisor Owner
**Ngày nộp:** 2026-04-14

---

## 1. Tôi phụ trách phần nào?

Trong Sprint 1 của Lab Day 09, tôi đảm nhận vai trò **Supervisor Owner** — chịu trách nhiệm thiết kế và implement toàn bộ orchestration layer của hệ thống multi-agent.

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py`
- Functions tôi implement:
  - `AgentState` — TypedDict định nghĩa shared state đi xuyên suốt toàn graph
  - `make_initial_state()` — khởi tạo state mặc định cho mỗi run
  - `supervisor_node()` — **hàm trung tâm**: phân tích keyword trong task, kết hợp risk detection để quyết định route
  - `route_decision()` — conditional edge đọc `supervisor_route` từ state và trả về tên worker tiếp theo
  - `build_graph()` — lắp ghép toàn bộ flow: supervisor → route → [workers] → synthesis
  - `run_graph()` — public entry point nhận câu hỏi và trả về AgentState với full trace
  - `save_trace()` — lưu kết quả mỗi run ra file JSON trong `artifacts/traces/`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Supervisor node là "cổng vào" cho toàn bộ hệ thống. Mọi request đều phải đi qua `supervisor_node()` trước, sau đó mới tỏa ra các worker tương ứng. Các thành viên owner của Sprint 2 (Worker Owner) sẽ implement `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py` — các file này sẽ được gọi thay thế các placeholder trong `graph.py` khi Sprint 2 hoàn thành.

**Bằng chứng:** Toàn bộ routing logic nằm trong `graph.py`. Trace file `artifacts/traces/run_20260414_135404.json` ghi nhận đầy đủ các run test với `supervisor_route` và `route_reason` cụ thể.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Dùng **keyword-based priority routing với 4 tầng ưu tiên rõ ràng** thay vì gọi LLM để classify task.

Ban đầu, tôi cân nhắc hai hướng:
- **Option A (đã chọn):** Phân tích keyword trực tiếp bằng Python (`any(kw in task for kw in keywords)`), với 4 tầng ưu tiên được sắp xếp theo mức độ quan trọng — từ `human_review` (nguy hiểm nhất) xuống đến `retrieval_worker` (mặc định).
- **Option B (bị loại):** Gọi LLM để phân loại intent của task, sau đó map sang worker.

Tôi chọn Option A vì ba lý do: **(1) Tốc độ** — keyword check xử lý dưới 1ms trong khi LLM call sẽ tốn 500–1000ms, làm tăng latency toàn pipeline đáng kể. **(2) Predictability** — behavior của keyword routing có thể đọc và debug trực tiếp từ `route_reason` log, còn LLM classification có thể thay đổi kết quả nếu prompt thay đổi. **(3) Đủ chính xác cho bài toán** — 5 loại task trong lab đều có keyword đặc trưng rõ ràng (refund, access, SLA, ERR-xxx) nên không cần semantic understanding.

**Trade-off đã chấp nhận:** Keyword matching không hiểu ngữ cảnh, nên edge case như "không có vấn đề về refund" vẫn bị bắt nhầm sang `policy_tool_worker`. Trade-off này chấp nhận được vì lab ưu tiên traceable routing hơn semantic accuracy.

**Bằng chứng từ trace/code:**

```
▶ Query #2: Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — policy nào áp dụng?
  [supervisor] → policy_tool_worker
  [supervisor] reason: task chứa policy keyword ['hoàn tiền', 'flash sale', 'policy'] → policy_tool_worker
  Route   : policy_tool_worker ✅ (expected: policy_tool_worker)
  Latency : 0ms

▶ Query #3: Contractor cần Admin Access để sửa P1 khẩn cấp — quy trình tạm thời là gì?
  [supervisor] → policy_tool_worker
  [supervisor] reason: task chứa access/emergency keyword ['access', 'admin access', 'khẩn cấp', 'contractor', 'tạm thời'] → policy_tool_worker | risk_high=True
```

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Test assertion đọc sai giá trị `supervisor_route` sau khi `human_review` node tự-override route.

**Symptom:** Khi chạy test với query chứa mã lỗi `ERR-5X2`, pipeline định tuyến đúng sang `human_review_node` — nhưng kết quả cuối lại báo `Route: retrieval_worker ❌` thay vì `human_review ✅`.

**Root cause:** Trong `human_review_node()`, sau khi HITL được kích hoạt (lab mode auto-approve), node tự ghi đè giá trị `state["supervisor_route"] = "retrieval_worker"` để pipeline tiếp tục với retrieval. Code assertion trong test block lại đọc `result['supervisor_route']` — đây là giá trị **sau khi bị override**, không phải giá trị routing ban đầu của supervisor.

**Cách sửa:** Thay vì đọc `result['supervisor_route']` để kiểm tra, tôi chuyển sang đọc `result['workers_called'][0]` — tức là **worker đầu tiên được gọi** trong pipeline. Worker đầu tiên luôn phản ánh đúng quyết định routing ban đầu của supervisor, không bị ảnh hưởng bởi các override về sau.

**Bằng chứng trước/sau:**

```python
# TRƯỚC (sai — đọc giá trị bị override):
actual_route = result['supervisor_route']
# → Kết quả: Route: retrieval_worker ❌ (expected: human_review)

# SAU (đúng — đọc worker đầu tiên được gọi):
actual_route = result['workers_called'][0] if result['workers_called'] else result['supervisor_route']
# → Kết quả: Route: human_review ✅ (expected: human_review)
```

Sau khi sửa: **Sprint 1 Results: 5/5 passed, 0 failed ✅**

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế routing với 4 tầng ưu tiên rõ ràng và có hệ thống — mỗi nhánh đều log đầy đủ `route_reason`, `risk_high`, `needs_tool` vào state. Khi nhìn vào trace file, bất kỳ thành viên nào trong nhóm cũng có thể đọc và hiểu ngay tại sao một câu hỏi được route sang worker cụ thể mà không cần debug thêm.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Keyword list hiện tại được viết cứng (hard-coded) trong `supervisor_node()`. Nếu bài toán mở rộng thêm domain mới, phải vào code để thêm keyword thủ công — không có cơ chế configure từ bên ngoài (VD: load từ file YAML). Đây là điểm cần cải thiện cho scale thực tế.

**Nhóm phụ thuộc vào tôi ở đâu?**

Tất cả các Sprint sau (2, 3, 4) đều phụ thuộc vào `graph.py`. Worker Owner cần `AgentState` đã được define đúng để implement workers. Trace Owner cần `save_trace()` trả về đủ fields để `eval_trace.py` đọc được.

**Phần tôi phụ thuộc vào thành viên khác:**

Hiện tại `retrieval_worker_node()`, `policy_tool_worker_node()`, `synthesis_worker_node()` trong `graph.py` đang dùng placeholder output. Worker Owner (Sprint 2) cần implement các file `workers/*.py` thực sự để pipeline cho kết quả có nghĩa thay vì `[PLACEHOLDER]`.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thêm **confidence-based HITL escalation** vào `supervisor_node()`. Hiện tại, `human_review` chỉ được trigger khi phát hiện mã lỗi ERR-xxx. Nhưng từ trace test query #1 (Ticket P1 lúc 2am), kết quả trả về `confidence=0.75` với câu hỏi có `risk_high=True`. Theo contract trong `worker_contracts.yaml`, `confidence < 0.4` nên trigger HITL — nhưng supervisor hiện tại không kiểm tra confidence sau synthesis để quyết định có cần escalate lại không. Nếu có thêm 2 giờ, tôi sẽ implement một vòng lặp feedback: sau khi synthesis xong, nếu `confidence < 0.6` và `risk_high=True`, supervisor sẽ tự động flag lại `hitl_triggered=True` và append lý do vào `route_reason` để trace ghi nhận đầy đủ.

---

*File lưu tại: `reports/individual/tran_ngoc_huy.md`*
