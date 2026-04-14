# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** 5 - E402  
**Ngày:** 14/04/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.650 | 0.700 | +0.050 | Tăng độ chắc chắn của câu trả lời. |
| Avg latency (ms) | 1250 | 5184 | +3934ms | Chậm hơn do overhead Graph & MCP. |
| Abstain rate (%) | 20% | 20% | 0% | Duy trì sự trung thực, không bịa thông tin. |
| Multi-hop accuracy | 30% | 75% | +45% | Nhờ Policy Worker & MCP Tools. |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Minh bạch hóa quá trình suy luận. |
| Debug time (estimate) | 45 phút | 10 phút | -35 phút | Biết chính xác lỗi ở Worker nào. |

> **Lưu ý:** Chỉ số Day 08 lấy từ scorecard 2.9 (Faithfulness) và 4.2 (Relevance).

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Cao | Cao |
| Latency | Thấp (1.2s) | Trung bình (3.5s) |
| Observation | Nhanh nhưng không có trace. | Chậm nhưng giải trình tốt. |

**Kết luận:** Với câu hỏi đơn giản, Single Agent có lợi thế về tốc độ nhưng kém về tính minh bạch.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Thấp | Rất Cao |
| Routing visible? | ✗ | ✓ |
| Observation | Thường bỏ lỡ 1-2 tài liệu quan trọng. | Phối hợp tốt giữa Retrieval và Policy. |

**Kết luận:** Multi-agent vượt trội hoàn toàn về chất lượng câu trả lời phức tạp (xem gq09).

### 2.3 Câu hỏi cần từ chối (Abstain)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | 20% | 20% |
| Hallucination cases | Có (do bias prompt) | Rất ít (do Policy Filter) |
| Observation | Cố gắng trả lời sai context. | Nhận diện đúng chính sách cũ (v3). |

**Kết luận:** Multi-agent an toàn hơn cho các hệ thống doanh nghiệp (Enterprise).

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 45 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 10 phút
```

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó | Dễ (swap worker) |

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 2 LLM calls |
| Complex query | 1 LLM call | 3-4 LLM calls |
| MCP tool call | N/A | FastAPI Call |

**Nhận xét về cost-benefit:** Đánh đổi chi phí lấy sự an tâm. Multi-agent tốn kém hơn nhưng đảm bảo tính đúng đắn cho các trường hợp đặc biệt.

---

## 6. Kết luận

**Multi-agent tốt hơn single agent ở điểm:**
1. Khả năng giải trình (Route reason).
2. Xử lý logic chính sách qua MCP Server.
3. Chuyên môn hóa (Specialization) của các Worker.

**Multi-agent kém hơn hoặc không khác biệt ở điểm:**
1. Độ trễ (Latency) tăng cao do nhiều node liên quan.
2. Chi phí API cao hơn.

**Khi nào KHÔNG nên dùng multi-agent?**
Khi hệ thống chỉ cần tra cứu thông tin tĩnh đơn giản và yêu cầu thời gian phản hồi dưới 1 giây.

**Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**
Thêm Worker chuyên về SQL để truy vấn dữ liệu giao dịch thực tế từ Database.
