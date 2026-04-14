"""
graph.py — Supervisor Orchestrator
Sprint 1: Implement AgentState, supervisor_node, route_decision và kết nối graph.

Kiến trúc:
    Input → Supervisor → [retrieval_worker | policy_tool_worker | human_review] → synthesis → Output

Chạy thử:
    python graph.py
"""

import json
import os
from datetime import datetime
from typing import TypedDict, Literal, Optional

# Uncomment nếu dùng LangGraph:
# from langgraph.graph import StateGraph, END

# ─────────────────────────────────────────────
# 1. Shared State — dữ liệu đi xuyên toàn graph
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    task: str                           # Câu hỏi đầu vào từ user

    # Supervisor decisions
    route_reason: str                   # Lý do route sang worker nào
    risk_high: bool                     # True → cần HITL hoặc human_review
    needs_tool: bool                    # True → cần gọi external tool qua MCP
    hitl_triggered: bool                # True → đã pause cho human review

    # Worker outputs
    retrieved_chunks: list              # Output từ retrieval_worker
    retrieved_sources: list             # Danh sách nguồn tài liệu
    policy_result: dict                 # Output từ policy_tool_worker
    mcp_tools_used: list                # Danh sách MCP tools đã gọi

    # Final output
    final_answer: str                   # Câu trả lời tổng hợp
    sources: list                       # Sources được cite
    confidence: float                   # Mức độ tin cậy (0.0 - 1.0)

    # Trace & history
    history: list                       # Lịch sử các bước đã qua
    workers_called: list                # Danh sách workers đã được gọi
    supervisor_route: str               # Worker được chọn bởi supervisor
    latency_ms: Optional[int]           # Thời gian xử lý (ms)
    run_id: str                         # ID của run này


def make_initial_state(task: str) -> AgentState:
    """Khởi tạo state cho một run mới."""
    return {
        "task": task,
        "route_reason": "",
        "risk_high": False,
        "needs_tool": False,
        "hitl_triggered": False,
        "retrieved_chunks": [],
        "retrieved_sources": [],
        "policy_result": {},
        "mcp_tools_used": [],
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "history": [],
        "workers_called": [],
        "supervisor_route": "",
        "latency_ms": None,
        "run_id": f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    }


# ─────────────────────────────────────────────
# 2. Supervisor Node — quyết định route
# ─────────────────────────────────────────────

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào
    2. Có cần MCP tool không
    3. Có risk cao cần HITL không

    Routing logic (theo thứ tự ưu tiên):
    - Mã lỗi không rõ (ERR-xxx) + không đủ context → human_review
    - "hoàn tiền", "refund", "flash sale", "license", "digital" → policy_tool_worker
    - "cấp quyền", "access", "level 3", "emergency", "contractor" → policy_tool_worker
    - "P1", "escalation", "sla", "ticket", "sự cố", "2am" → retrieval_worker (ưu tiên)
    - còn lại → retrieval_worker (default)
    """
    task = state["task"].lower()
    state["history"].append(f"[supervisor] received task: {state['task'][:80]}")

    # ─── Bước 1: Phát hiện mã lỗi không rõ ───
    import re
    unknown_error_pattern = re.search(r"err-[a-z0-9]+", task)

    # ─── Bước 2: Keyword sets ───────────────
    policy_keywords = [
        "hoàn tiền", "refund", "flash sale", "flashsale",
        "license", "bản quyền", "digital", "kỹ thuật số",
        "policy", "chính sách", "quy định",
        "hủy đơn", "cancel", "đổi trả",
    ]

    access_keywords = [
        "cấp quyền", "access", "level 3", "admin access",
        "emergency", "khẩn cấp", "contractor", "nhà thầu",
        "tạm thời", "temporary access", "quyền truy cập",
        "phân quyền",
    ]

    retrieval_priority_keywords = [
        "p1", "escalation", "leo thang", "sla",
        "ticket", "sự cố", "incident", "2am",
        "thông báo", "ai nhận", "notify",
        "helpdesk", "on-call",
    ]

    risk_keywords = [
        "emergency", "khẩn cấp", "2am",
        "không có người", "ngoài giờ", "off-hours",
        "err-", "lỗi không rõ", "unknown error",
    ]

    # ─── Bước 3: Tính điểm ưu tiên ─────────
    has_policy   = any(kw in task for kw in policy_keywords)
    has_access   = any(kw in task for kw in access_keywords)
    has_retrieval = any(kw in task for kw in retrieval_priority_keywords)
    risk_high    = any(kw in task for kw in risk_keywords)

    # ─── Bước 4: Routing logic (theo ưu tiên) ──
    route = "retrieval_worker"
    route_reason = "default: không khớp keyword đặc biệt → retrieval_worker"
    needs_tool = False

    # Priority 1: Mã lỗi không rõ + risk cao → human_review
    if unknown_error_pattern and not has_retrieval:
        route = "human_review"
        route_reason = (
            f"phát hiện mã lỗi không rõ '{unknown_error_pattern.group()}' "
            "và không đủ context → chuyển human review"
        )
        risk_high = True

    # Priority 2: Policy/refund/license keywords → policy_tool_worker
    elif has_policy:
        route = "policy_tool_worker"
        needs_tool = True
        matched = [kw for kw in policy_keywords if kw in task]
        route_reason = f"task chứa policy keyword {matched} → policy_tool_worker"

    # Priority 3: Access/emergency keywords → policy_tool_worker
    elif has_access:
        route = "policy_tool_worker"
        needs_tool = True
        matched = [kw for kw in access_keywords if kw in task]
        route_reason = f"task chứa access/emergency keyword {matched} → policy_tool_worker"

    # Priority 4: P1/SLA/escalation → retrieval_worker (ưu tiên)
    elif has_retrieval:
        route = "retrieval_worker"
        matched = [kw for kw in retrieval_priority_keywords if kw in task]
        route_reason = f"task chứa SLA/ticket/escalation keyword {matched} → retrieval_worker"

    # Gắn thêm risk flag vào route_reason nếu có
    if risk_high and "risk_high" not in route_reason:
        risk_matched = [kw for kw in risk_keywords if kw in task]
        route_reason += f" | risk_high=True (matched: {risk_matched})"

    # ─── Bước 5: Ghi vào state ──────────────
    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(
        f"[supervisor] route={route} | reason={route_reason} | "
        f"risk_high={risk_high} | needs_tool={needs_tool}"
    )

    print(f"  [supervisor] → {route}")
    print(f"  [supervisor] reason: {route_reason}")

    return state


# ─────────────────────────────────────────────
# 3. Route Decision — conditional edge
# ─────────────────────────────────────────────

def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    """
    Trả về tên worker tiếp theo dựa vào supervisor_route trong state.
    Đây là conditional edge của graph.
    """
    route = state.get("supervisor_route", "retrieval_worker")
    return route  # type: ignore


# ─────────────────────────────────────────────
# 4. Human Review Node — HITL placeholder
# ─────────────────────────────────────────────

def human_review_node(state: AgentState) -> AgentState:
    """
    HITL node: pause và chờ human approval.
    Trong lab này, implement dưới dạng placeholder (in ra warning).

    TODO Sprint 3 (optional): Implement actual HITL với interrupt_before hoặc
    breakpoint nếu dùng LangGraph.
    """
    state["hitl_triggered"] = True
    state["history"].append("[human_review] HITL triggered — awaiting human input")
    state["workers_called"].append("human_review")

    # Placeholder: tự động approve để pipeline tiếp tục
    print(f"\n⚠️  HITL TRIGGERED")
    print(f"   Task: {state['task']}")
    print(f"   Reason: {state['route_reason']}")
    print(f"   Action: Auto-approving in lab mode (set hitl_triggered=True)\n")

    # Sau khi human approve, route về retrieval để lấy evidence
    state["supervisor_route"] = "retrieval_worker"
    state["route_reason"] += " | human approved → retrieval"

    return state


# ─────────────────────────────────────────────
# 5. Import Workers
# ─────────────────────────────────────────────

# TODO Sprint 2: Uncomment sau khi implement workers
# from workers.retrieval import run as retrieval_run
# from workers.policy_tool import run as policy_tool_run
# from workers.synthesis import run as synthesis_run


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker."""
    # TODO Sprint 2: Thay bằng retrieval_run(state)
    state["workers_called"].append("retrieval_worker")
    state["history"].append("[retrieval_worker] called")

    # Placeholder output để test graph chạy được
    state["retrieved_chunks"] = [
        {"text": "SLA P1: phản hồi 15 phút, xử lý 4 giờ.", "source": "sla_p1_2026.txt", "score": 0.92}
    ]
    state["retrieved_sources"] = ["sla_p1_2026.txt"]
    state["history"].append(f"[retrieval_worker] retrieved {len(state['retrieved_chunks'])} chunks")
    return state


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    # TODO Sprint 2: Thay bằng policy_tool_run(state)
    state["workers_called"].append("policy_tool_worker")
    state["history"].append("[policy_tool_worker] called")

    # Placeholder output
    state["policy_result"] = {
        "policy_applies": True,
        "policy_name": "refund_policy_v4",
        "exceptions_found": [],
        "source": "policy_refund_v4.txt",
    }
    state["history"].append("[policy_tool_worker] policy check complete")
    return state


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    # TODO Sprint 2: Thay bằng synthesis_run(state)
    state["workers_called"].append("synthesis_worker")
    state["history"].append("[synthesis_worker] called")

    # Placeholder output
    chunks = state.get("retrieved_chunks", [])
    sources = state.get("retrieved_sources", [])
    state["final_answer"] = f"[PLACEHOLDER] Câu trả lời được tổng hợp từ {len(chunks)} chunks."
    state["sources"] = sources
    state["confidence"] = 0.75
    state["history"].append(f"[synthesis_worker] answer generated, confidence={state['confidence']}")
    return state


# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với supervisor-worker pattern.

    Option A (đơn giản — Python thuần): Dùng if/else, không cần LangGraph.
    Option B (nâng cao): Dùng LangGraph StateGraph với conditional edges.

    Lab này implement Option A theo mặc định.
    TODO Sprint 1: Có thể chuyển sang LangGraph nếu muốn.
    """
    # Option A: Simple Python orchestrator
    def run(state: AgentState) -> AgentState:
        import time
        start = time.time()

        # Step 1: Supervisor decides route
        state = supervisor_node(state)

        # Step 2: Route to appropriate worker
        route = route_decision(state)

        if route == "human_review":
            state = human_review_node(state)
            # After human approval, continue with retrieval
            state = retrieval_worker_node(state)
        elif route == "policy_tool_worker":
            state = policy_tool_worker_node(state)
            # Policy worker may need retrieval context first
            if not state["retrieved_chunks"]:
                state = retrieval_worker_node(state)
        else:
            # Default: retrieval_worker
            state = retrieval_worker_node(state)

        # Step 3: Always synthesize
        state = synthesis_worker_node(state)

        state["latency_ms"] = int((time.time() - start) * 1000)
        state["history"].append(f"[graph] completed in {state['latency_ms']}ms")
        return state

    return run


# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

_graph = build_graph()


def run_graph(task: str) -> AgentState:
    """
    Entry point: nhận câu hỏi, trả về AgentState với full trace.

    Args:
        task: Câu hỏi từ user

    Returns:
        AgentState với final_answer, trace, routing info, v.v.
    """
    state = make_initial_state(task)
    result = _graph(state)
    return result


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    """Lưu trace ra file JSON."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{state['run_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return filename


# ─────────────────────────────────────────────
# 8. Manual Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph (Sprint 1)")
    print("=" * 60)

    # ─── Sprint 1 Test: 5 queries bao phủ mọi routing path ───
    test_queries = [
        # 1. SLA/ticket → retrieval_worker
        "Ticket P1 lúc 2am — escalation xảy ra thế nào và ai nhận thông báo?",

        # 2. Policy/refund → policy_tool_worker
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — policy nào áp dụng?",

        # 3. Access/emergency → policy_tool_worker
        "Contractor cần Admin Access để sửa P1 khẩn cấp — quy trình tạm thời là gì?",

        # 4. Unknown error code → human_review
        "Server bị lỗi ERR-5X2 và hệ thống không phản hồi.",

        # 5. General SLA question → retrieval_worker (default)
        "SLA xử lý ticket P1 là bao lâu?",
    ]

    passed = 0
    failed = 0

    expected_routes = [
        "retrieval_worker",   # query 1: P1 escalation
        "policy_tool_worker", # query 2: flash sale refund
        "policy_tool_worker", # query 3: admin access emergency
        "human_review",       # query 4: unknown error ERR-xxx
        "retrieval_worker",   # query 5: SLA question
    ]

    for i, (query, expected) in enumerate(zip(test_queries, expected_routes), 1):
        print(f"\n{'─'*60}")
        print(f"▶ Query #{i}: {query}")
        result = run_graph(query)

        # Trích xuất initial route dựa trên worker đầu tiên được gọi
        actual_route = result['workers_called'][0] if result['workers_called'] else result['supervisor_route']
        ok = "✅" if actual_route == expected else "❌"
        if actual_route == expected:
            passed += 1
        else:
            failed += 1

        print(f"  Route   : {actual_route} {ok} (expected: {expected})")
        print(f"  Reason  : {result['route_reason']}")
        print(f"  Risk    : {result['risk_high']}")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  : {result['final_answer'][:80]}...")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Latency : {result['latency_ms']}ms")

        # Lưu trace
        trace_file = save_trace(result)
        print(f"  Trace   : {trace_file}")

    print(f"\n{'='*60}")
    print(f"Sprint 1 Results: {passed}/{len(test_queries)} passed, {failed} failed")
    if failed == 0:
        print("✅ All routing tests PASSED — Sprint 1 Definition of Done met!")
    else:
        print("⚠️  Some routing tests failed — check route_reason logs above.")
    print(f"{'='*60}")
