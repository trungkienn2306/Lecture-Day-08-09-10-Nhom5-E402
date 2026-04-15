#!/usr/bin/env python3
"""
Kiểm tra nhanh file grading_run.jsonl trước khi nộp bài.
Chạy từ thư mục day10/lab/:
  python scripts/check_grading.py
"""
import json
from pathlib import Path

GRADING_FILE = Path("artifacts/eval/grading_run.jsonl")

if not GRADING_FILE.is_file():
    print(f"ERROR: Chua co file {GRADING_FILE}")
    print("  -> Chay: python grading_run.py --out artifacts/eval/grading_run.jsonl")
    raise SystemExit(1)

lines = [l.strip() for l in GRADING_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
print(f"=== Ket qua grading_run.jsonl ({len(lines)} cau) ===\n")

all_ok = True
for line in lines:
    r = json.loads(line)
    ok = r["contains_expected"] and not r["hits_forbidden"]
    top1 = r.get("top1_doc_matches")
    if top1 is not None:
        ok = ok and (top1 is True)

    status = "OK  " if ok else "FAIL"
    all_ok = all_ok and ok

    top1_str = f", top1_doc_matches={top1}" if top1 is not None else ""
    print(f"  [{status}] {r['id']}")
    print(f"          contains_expected={r['contains_expected']}, hits_forbidden={r['hits_forbidden']}{top1_str}")
    print()

if all_ok:
    print("=> TAT CA CAC CAU: OK - San sang nop bai!")
else:
    print("=> CO CAU FAIL - Kiem tra lai collection ChromaDB (chay etl_pipeline.py run truoc).")

raise SystemExit(0 if all_ok else 1)
