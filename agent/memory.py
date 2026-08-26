"""Stretch #4 — Agent memory tối giản (KHÔNG phải interface bắt buộc của
lab, không được import bởi agent/runner.py mặc định — production path đã
chấm điểm ở Bước 3 giữ nguyên, không phụ thuộc module này).

Ý tưởng: agent "nhớ" vài ghi chú (note) giữa các lần chạy, lưu ở 1 file
JSON tại `data/agent_memory.json`. Đây là nơi minh hoạ "memory poisoning" —
xem `scripts/memory_poisoning_demo.py` và `reports/memory-poisoning-demo.md`.
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_MEMORY_PATH = Path(__file__).resolve().parent.parent / "data" / "agent_memory.json"


def recall(path: Path | None = None) -> list[dict]:
    path = path or DEFAULT_MEMORY_PATH
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def remember(note: dict, path: Path | None = None) -> None:
    path = path or DEFAULT_MEMORY_PATH
    notes = recall(path)
    notes.append(note)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reset(path: Path | None = None) -> None:
    path = path or DEFAULT_MEMORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]\n", encoding="utf-8")
