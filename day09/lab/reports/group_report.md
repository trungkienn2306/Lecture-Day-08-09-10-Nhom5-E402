# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Nhóm 05-E402
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Trần Ngọc Huy | Supervisor Owner | 26ai.huytn@vinuni.edu.vn |
|  Nông Trung Kiên | Worker Owner | ___ |
| Bùi Thế Công | MCP Owner | 26ai.congbt@vinuni.edu.vn |
| Bùi Thế Công | Trace & Docs Owner | 26ai.congbt@vinuni.edu.vn |

**Ngày nộp:** 14/04/2026 

**Repo:** https://github.com/trungkienn2306/Lecture-Day-08-09-10-Nhom5-E402.git 

**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

Hệ thống của chúng tôi được xây dựng theo mô hình **Supervisor-Worker**, tập trung vào tính chuyên môn hóa và khả năng giải thích (Explainability). Hệ thống bao gồm một bộ não trung tâm (Supervisor) và ba Worker thực thi chuyên biệt.

**Hệ thống tổng quan:**
- **Supervisor (`graph.py`):** Điều phối luồng làm việc, phân tích ý định người dùng để chọn worker phù hợp.
- **Workers (`workers/`):** 
    - `retrieval_worker`: Tra cứu tài liệu tĩnh từ ChromaDB.
    - `policy_tool_worker`: Xử lý logic nghiệp vụ phức tạp thông qua MCP Server.
    - `synthesis_worker`: Tổng hợp câu trả lời cuối cùng có trích dẫn nguồn.

**Routing logic cốt lõi:**
Nhóm sử dụng cơ chế **Hybrid Routing** (kết hợp Keyword Matching và LLM Classifier). Supervisor sẽ ưu tiên kiểm tra các bộ từ khóa (Keyword Sets) đặc thù như `sla`, `access`, `refund` để định tuyến nhanh. Nếu không khớp cao, hệ thống sẽ dùng LLM để phân tích ngữ cảnh sâu hơn.

**MCP tools đã tích hợp:**
Chúng tôi triển khai **Advanced MCP Server** bằng FastAPI với 3 công cụ chính:
- `search_kb`: Tìm kiếm ngữ nghĩa trong Knowledge Base.
- `get_ticket_info`: Tra cứu thông tin Ticket thực tế từ hệ thống mô phỏng.
- `check_access_permission`: Kiểm tra các điều kiện cấp quyền theo SOP.

*Ví dụ trace:* Trong quyết định `gq03`, hệ thống gọi đồng thời `search_kb` và `check_access_permission` để xác định quy trình phê duyệt 3 bước.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Triển khai **Advanced MCP Server** qua HTTP (FastAPI) thay vì Mock Class.

**Bối cảnh vấn đề:**
Trong Sprint 3, nhóm đối mặt với lựa chọn triển khai MCP đơn giản (Python functions) hay xây dựng một service độc lập. Việc dùng Mock Class tuy nhanh nhưng không mô phỏng được độ trễ mạng thực tế và gây khó khăn cho việc quản lý trạng thái tập trung khi hệ thống mở rộng.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Mock Class (Standard) | Dễ code, chạy nhanh trong 1 process. | Khó mở rộng, không mô phỏng được Microservices. |
| FastAPI HTTP (Advanced) | Tính module hóa cao, dễ debug qua logs server, sát thực tế. | Tốn tài nguyên (2 process), độ trễ cao hơn. |

**Phương án đã chọn và lý do:**
Nhóm chọn **FastAPI (Advanced)** vì mục tiêu của Lab Day 09 là Trace & Observability. Việc tách riêng MCP Server giúp chúng tôi theo dõi được Access Logs độc lập, đồng thời cho phép bất kỳ agent nào (không chỉ graph hiện tại) cũng có thể gọi tool qua REST API.

**Bằng chứng từ trace/code:**
Trong `mcp_server.py`, chúng tôi định nghĩa endpoint linh hoạt:
```python
@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: Dict[str, Any]):
    args = request.get("arguments", request)
    result = dispatch_tool(tool_name, args)
    return result
```
Bằng chứng thực tế từ `single_vs_multi_comparison.md` cho thấy việc gọi qua HTTP đóng góp một phần vào latency nhưng mang lại khả năng quản lý tool schema cực kỳ rõ ràng.

---

## 3. Kết quả grading questions (150–200 từ)

**Tổng điểm raw ước tính:** 92 / 96

**Câu pipeline xử lý tốt nhất:**
- ID: `gq10` — Lý do tốt: Pipeline nhận diện đúng ngoại lệ "Flash Sale" override quy định "lỗi nhà sản xuất" nhờ việc định tuyến chính xác vào Policy Worker và kiểm tra điều kiện qua MCP `search_kb`.

**Câu pipeline fail hoặc partial:**
- ID: `gq09` — Fail ở đâu: Kết quả trả về rất đầy đủ nhưng latency lên tới 10.3 giây.
  Root cause: Do câu hỏi multi-hop này yêu cầu Supervisor gọi tuần tự cả 2 workers và Policy Worker gọi thêm 3 MCP tools, tạo ra overhead cộng dồn đáng kể.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?
Hệ thống xử lý rất tốt nhờ logic `synthesis_worker` được cấu hình để không tự bịa thông tin. Kết quả trả về rõ ràng: *"Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này"*, đạt điểm tối đa cho tiêu chí anti-hallucination.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?
Trace ghi nhận đúng `workers_called: ["policy_tool_worker", "synthesis_worker"]` (Lưu ý: Policy tool gọi chéo sang retrieval thông qua MCP `search_kb`). Kết quả tổng hợp đủ cả quy trình SLA và điều kiện cấp quyền Level 2, đạt Full Marks.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**
**Routing Visibility:** Từ ✗ (Day 08 - Blackbox) sang ✓ (Day 09 - Transparency). Nhóm có thể giải trình chính xác lý do chọn hướng xử lý thông qua trường `route_reason` trong trace JSON.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**
Sự chênh lệch về **độ trễ (Latency)**. Day 08 chỉ tốn ~1.2s, trong khi Day 09 trung bình lên tới ~5.2s. Tuy nhiên, thời gian **Debug** lại giảm từ 45 phút xuống còn 10 phút nhờ biết chính xác lỗi nằm ở Worker nào hay bước định tuyến nào.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Với các câu hỏi tra cứu thông tin tĩnh đơn giản (như "Store credit là bao nhiêu %?"), kiến trúc Multi-Agent tỏ ra "overkill". Việc phải đi qua Supervisor -> Retrieval -> Synthesis làm chậm tốc độ phản hồi gấp 3 lần mà không mang lại thêm giá trị về mặt logic so với Single Agent.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Trần Ngọc Huy | thiết kế và implement toàn bộ orchestration layer của hệ thống multi-agent. | 1 |
| Nông Trung Kiên | Tác tử Truy xuất (Retrieval Worker), Tác tử Tổng hợp (Synthesis Worker), Tác tử Công cụ Chính sách (Policy Tool Worker) | 2 |
| Bùi Thế Công | MCP Server (FastAPI), Eval Script, Docs | 3, 4 |

**Điều nhóm làm tốt:**
Phối hợp nhịp nhàng ở khâu khớp nối Interface (Contract). Việc thống nhất `AgentState` từ sớm giúp MCP Owner có thể giả lập API mà không cần chờ Graph hoàn thiện.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Khâu kiểm thử Grading Questions hơi gấp gáp (gần giờ deadline 18:00) nên chưa triển khai được chấm điểm tự động cho grading questions cũng như thời gian làm tài liệu ít nên có thể tài liệu chưa được đầy đủ.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**
Nhóm sẽ thực hiện "Parallel Sprinting" sớm hơn. Có thể tự mock data để làm đồng thời cả 3 sprint, qua đó đẩy nhanh tiến độ và có nhiều thời gian hơn cho việc chạy test, đánh giá kết quả và làm tài liệu.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ triển khai cơ chế **Parallel Node Execution** trong LangGraph. Hiện tại Supervisor gọi worker tuần tự; nếu có thêm 1 ngày, chúng tôi sẽ cho phép gọi đồng thời các worker cho các câu hỏi multi-hop như `gq09` để giảm latency từ 10s xuống còn khoảng 4-5s, đồng thời tích hợp thêm một lớp Human-in-the-loop (HITL) thực tế qua giao diện UI.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
