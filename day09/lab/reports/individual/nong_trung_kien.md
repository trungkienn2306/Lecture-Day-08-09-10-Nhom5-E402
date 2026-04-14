# Báo Cáo Cá Nhân — Lab Day 09: Điều phối Đa Tác tử (Multi-Agent Orchestration)

**Họ và tên:** Nông Trung Kiên — MSSV: 2A202600414  
**Vai trò trong nhóm:** Người phụ trách Tác tử thực thi (Worker Owner) - Giai đoạn 2 (Sprint 2): Tác tử Truy xuất (Retrieval Worker), Tác tử Tổng hợp (Synthesis Worker), Tác tử Công cụ Chính sách (Policy Tool Worker)  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ  

---

## 1. Phần phụ trách (100–150 từ)

Giai đoạn 2 (Sprint 2) tập trung vào việc triển khai ba tác tử chuyên biệt (worker) phục vụ luồng xử lý đa tác tử (multi-agent pipeline). Đây là tầng thực thi cốt lõi — nơi mọi dữ liệu thực sự được xử lý sau khi Tác tử Điều phối (Supervisor) đã có quyết định định tuyến (routing).

**Mô-đun/tệp tin phụ trách:**
- Tệp tin chính: `workers/retrieval.py`, `workers/synthesis.py`, `workers/policy_tool.py`
- Các hàm triển khai (implemented functions): `_get_collection()`, `_build_index()`, `search()`, `run()` đối với Tác tử Truy xuất; `_call_llm()`, `_build_context()`, `_calculate_confidence()`, `_should_abstain()`, `synthesize()`, `run()` đối với Tác tử Tổng hợp; `_detect_exceptions()`, `_call_mcp()`, `analyze_policy()`, `run()` đối với Tác tử Công cụ Chính sách.

**Cách kết nối với phần của thành viên khác:**

Tác tử Truy xuất nhận yêu cầu tác vụ (task) từ trạng thái hệ thống (AgentState) do Tác tử Điều phối truyền xuống, sau đó ghi các đoạn văn bản (retrieved_chunks) và nguồn tài liệu (retrieved_sources) vào trạng thái. Tác tử Công cụ Chính sách nhận thêm các cờ báo hiệu như nhu cầu sử dụng công cụ (needs_tool) và mức độ rủi ro (risk_high), đồng thời gọi giao thức mạng (HTTP) sang Máy chủ Cung cấp Ngữ cảnh Máy (MCP Server - Sprint 3). Tác tử Tổng hợp luôn được tiến hành cuối cùng, đọc nội dung truy xuất và kết quả kiểm tra chính sách (policy_result) để sinh câu trả lời cuối cùng (final_answer), mức độ tin cậy (confidence), và danh sách tài liệu tham khảo (sources).

**Bằng chứng:**

Tôi đã thực hiện các nội dung này trong bản ghi thay đổi mã nguồn (commit) mang định danh `a3d4d331` (feat: add workers for sprint 2) và bản ghi mang mã `1be5557` (docs: add day 08 result for comparison - cung cấp dữ liệu đánh giá đối chiếu với mô hình hệ thống của ngày 08 theo thiết kế yêu cầu).

---

## 2. Quyết định kỹ thuật (150–200 từ)

**Quyết định:** Thiết kế hàm `_calculate_confidence()` trong `synthesis.py` theo cơ chế tính điểm đa tín hiệu (multi-signal scoring) thay vì dùng một ngưỡng cố định (hard-coded threshold).

**Lý do:**

Ban đầu, tồn tại hai phương án tiếp cận: (A) gán trực tiếp mức độ tin cậy bằng điểm số của đoạn văn bản tiếp nhận phù hợp nhất (top chunk score), hoặc (B) tổng hợp nhiều tín hiệu bao gồm điểm số cao nhất, trung bình, điểm thưởng tính trên đa nguồn dẫn (breadth bonus), điểm trừ do hệ thống từ chối trả lời (abstain penalty), và điểm trừ do gặp ngoại lệ quy trình (exception penalty). Phương án (A) vận hành tối giản nhưng không hàm chứa khả năng phản ánh tình huống hệ thống thông báo "không đủ thông tin" mặc cho điểm số truy xuất lại cao. Phương án (B) phức tạp hơn về mặt tính toán song phản ánh chuẩn xác chất lượng biểu thị thực tế của thông điệp được sinh ra.

**Sự đánh đổi (trade-off) đã chấp nhận:**

Phương án (B) nảy sinh đòi hỏi phải kiểm định nội dung đáp án thông qua thuật toán khớp chuỗi (string matching), vô tình tạo ra một sự phụ thuộc ngầm (implicit coupling) giữa phương thức hệ thống hóa độ tin cậy và cấu trúc ngữ nghĩa của văn bản xuất ra. Nếu Mô hình Kích thước Lớn (LLM) sử dụng cụm từ bất thường để từ chối trả lời, hàm trừu toán có thể bỏ lỡ việc áp dụng điểm phạt.

**Bằng chứng từ mã nguồn và dữ liệu dấu vết:**

```python
# workers/synthesis.py — hàm _calculate_confidence()
base_confidence = 0.65 * top_score + 0.35 * avg_score

abstain_phrases = [
    "không đủ thông tin", "không có trong tài liệu", "không tìm thấy",
    "not found", "tài liệu nội bộ không có", "synthesis error",
    "tổng hợp tự động",
]
is_abstain = any(phrase in answer.lower() for phrase in abstain_phrases)
abstain_penalty = 0.45 if is_abstain else 0.0

confidence = base_confidence + breadth_bonus - abstain_penalty - exception_penalty
return round(max(0.05, min(0.97, confidence)), 3)
```

Nhật ký truy vết (trace logs) mang tên `run_20260414_174107.json` cung cấp kết quả chứng minh: `top_chunk_score=0.7829`, `confidence=0.816` (đạt mức cao hơn so với thông số đơn vị nguyên bản nhờ lượng điểm thưởng kết hợp từ 2 phân vùng dữ liệu khác nhau), và hệ thống không từ chối vận hành (`abstained=false`) — hoạt động phản ánh triệt để khuôn mẫu mong tâm.

---

## 3. Lỗi đã sửa (150–200 từ)

**Vấn đề:** Xung đột cấu trúc số chiều không gian (dimension mismatch) khi khởi tạo Cơ sở dữ liệu Vectơ ChromaDB (Vector Database) với mô hình biểu diễn từ vựng `text-embedding-3-small`.

**Triệu chứng (symptom):**

Ngay tại thời điểm vận hành thuật toán `retrieval.py`, tiến trình vướng phải lỗi gián đoạn hệ thống (crash), biểu hiện qua phân vùng thông báo ngoại lệ (exception) "số chiều kích thước không hợp lệ" (invalid dimension). Toàn bộ luồng xử lý bị đình trệ; đồng thời phân hệ mất khả năng lập chỉ mục (index) văn bản cũng như tiến hành các bước phản hồi truy vấn tính toán (query).

**Nguyên nhân gốc rễ (root cause):**

Lý do phát lộ tại mã cấu hình khởi tạo danh mục dữ liệu (collection) của Tác tử Truy xuất. Không gian lưu trữ cục bộ `./chroma_db` mang những phân vùng bộ nhớ bền vững (persistent) định danh theo cấu hình cũ, vốn chứa đựng thông số định dạng cấu trúc vectơ phụ thuộc thuật toán mã hóa khác. Qua quá trình thay đổi đối trọng sang mô hình OpenAI `text-embedding-3-small`, hệ thống lâm vào tình trạng ngưng trệ bất đồng nhất do sai lệch số chiều tham chiếu (1536 so sánh với tham số lượng giá ban đầu).

**Giải pháp:**

Thay vì đòi hỏi người thao tác xóa bỏ thủ công tệp tin hệ thống thư mục cục bộ trích xuất, tôi định nghĩa lại biến `COLLECTION_NAME` tiếp nhận một danh xưng biệt lập được chỉ định chuẩn xác với biểu diễn thuật toán mới (`day09_docs_openai`). Công đoạn này cưỡng ép ChromaDB khởi lập một phân cực không gian lưu trữ hoàn toàn mới, xác lập nền móng thiết yếu thông qua hàm dựng `client.get_or_create_collection()`.

**Bằng chứng kiểm soát:**

Trước sửa đổi: Khởi tạo dùng `COLLECTION_NAME = "day09_docs"`, khởi nguyên việc gián đoạn tiến trình (crash).  
Sau sửa đổi: Điều chỉnh mã lệnh tại tệp `retrieval.py` (Dòng số 30):
```python
COLLECTION_NAME = "day09_docs_openai"  # Đổi tên để build lại index mới tránh xung đột size embedding
```
Nhật ký thực thi trả về thông điệp thiết lập hoàn thiện: `[RETRIEVAL] Indexed 12 chunks from data/docs/`.

---

## 4. Tự đánh giá đóng góp (100–150 từ)

**Thành tựu chuyên môn đạt mức tốt nhất:**

Năng lực thiết kế cho hàm xử lý trường hợp từ chối (`_should_abstain()`) đảm bảo khả năng kiểm soát tốt và vận hành chính xác qua các ngưỡng tình huống biên (edge cases). Cụ thể qua các yếu tố: (1) vô giá trị truy xuất văn bản, (2) điểm số hàm tương đồng không đạt ngưỡng phân giải `ABSTAIN_SCORE_THRESHOLD = 0.35`, và (3) sự thiếu sót về phạm vi thời gian hiệu lực (temporal scope mismatch). Mọi kịch bản thử nghiệm đã được xác nhận thực tiễn trên nhật ký truy vết hệ thống.

**Phương diện còn tồn đọng hạn chế:**

Giao thức gọi thủ tục ngữ cảnh (`_call_mcp()`) bên trong Tác tử Công cụ Chính sách vẫn vắng mặt cơ chế thử lại (retry). Do nguyên lý này, khi Máy chủ cấu hình vượt giới hạn thời gian chờ (timeout), đường dẫn liên lạc kết thúc tiến trình sau khi lưu giữ biểu định mã lỗi và tiếp tục khởi động phần tiếp theo — triệt tiêu phương án dự phòng (fallback) thiết yếu.

**Mức độ phụ thuộc của nhóm lập trình đối với khâu tổ chức:**

Hệ thống biểu thị chung bao trùm cổng kết quả (`final_answer`, `confidence`, `sources`) bắt buộc giao thoa quy trình thông qua Tác tử Tổng hợp. Ngưng trệ tại điểm nút này sẽ đưa toàn bộ chỉ số suy hao vô cùng trầm trọng cho đến khi dự phòng thủ công (rule-based synthesis) được vận hành.

**Sự phụ thuộc trên bình diện Tác tử chéo:**

Giai đoạn 2 đòi hỏi sự kiện toàn cấu hình tín hiệu định hướng từ Tác tử Điều phối (Giai đoạn 1). Sự tính toán sai sót chỉ thị sẽ cấu thành hệ lụy ngưng trệ không phù hợp hoặc hạ thấp điểm tin cậy nghiêm trọng ở phần khâu tổng hợp do cung cấp thông tin sai phạm.

---

## 5. Khuyến nghị cải tiến (50–100 từ)

Để tối ưu hóa khả năng chống chịu trạng thái gián đoạn, phương thức thử lại dựa theo hàm độ trễ lũy thừa (retry with exponential backoff) ở điểm nghẽn giao tiếp mạng `_call_mcp()` tại tập lệnh chính sách cần được bổ sung cụ thể. Quan sát cơ sở dữ liệu `run_20260414_174107.json` phơi bày độ trễ (delay) hiện tại tiếp cận `7242ms` phần lớn hao phí ở quá trình xử lý Máy chủ. Kịch bản đề nghị nên xây dựng quy tắc tăng bước từ 2 đến 3 nhịp lặp (trải dài độ trễ từ mức 0.5s đến 2s) nhằm thiết lập bức tường phòng thủ khắc phục các biến cố rớt gói dữ liệu (packet loss), duy trì trạng thái cho các thuộc tính mang cờ báo rủi ro cao (`risk_high=True`).
