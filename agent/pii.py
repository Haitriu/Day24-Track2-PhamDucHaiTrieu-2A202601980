"""BƯỚC 3a — PII gate TRƯỚC KHI vào context/store (12').

Đọc Guide.md (§3a) trước khi bắt đầu: Presidio không có tiếng Việt
sẵn (AnalyzerEngine() mặc định chỉ hỗ trợ "en"). Đường an toàn cho 2h là
regex recognizer + deny-list cho PERSON — coi spaCy/transformers NER là
stretch goal, KHÔNG bắt buộc.

Interface bắt buộc (tests/test_pii.py gọi trực tiếp 2 hàm này):

    detect(text: str) -> list[dict]
        Mỗi entity: {"type": str, "start": int, "end": int}
        `type` là một trong: "VN_CCCD", "VN_PHONE", "VN_BANK_ACCOUNT", "EMAIL"
        `start`/`end` là offset ký tự trong `text` (offset đầu bao gồm,
        offset cuối KHÔNG bao gồm — giống slice Python text[start:end]).
        Format này khớp với tests/vn_pii_testset.jsonl.

    redact(text: str) -> str
        Trả về `text` sau khi mọi entity từ detect() bị thay bằng
        "[REDACTED_<TYPE>]". Phải xử lý overlap/thứ tự đúng khi có nhiều
        entity (gợi ý: thay từ cuối văn bản về đầu để offset không bị lệch).

Gợi ý định dạng (không bắt buộc đúng regex này, miễn đạt ngưỡng trên test
set ở tests/vn_pii_testset.jsonl):
    VN_CCCD          12 chữ số liên tiếp
    VN_PHONE         0 + 9-10 chữ số, có thể có dấu cách/gạch ngang
    VN_BANK_ACCOUNT  8-16 chữ số liên tiếp, thường đi kèm "STK"/"số tài khoản"
    EMAIL            dạng chuẩn local@domain.tld

Đo bằng: pytest tests/test_pii.py -v -s   (in ra precision/recall)
"""
from __future__ import annotations

import re

# Ngữ cảnh đứng trước một chuỗi số dùng để phân loại đúng loại PII khi độ
# dài chữ số một mình không đủ phân biệt (vd 12 số vừa có thể là CCCD vừa
# có thể là STK dài). Match trực tiếp trên text gốc (không normalize) để
# offset trả về luôn khớp 1-1 với text đầu vào — IGNORECASE đã đủ xử lý biến
# thể hoa/thường của các từ khoá này trong tiếng Việt có dấu.
_BANK_CONTEXT_RE = re.compile(
    r"(?:STK|số\s*tài\s*khoản|so\s*tai\s*khoan)\D{0,15}?(\d{8,16})",
    re.IGNORECASE,
)
_CCCD_CONTEXT_RE = re.compile(
    r"(?:CCCD|CMND|căn\s*cước|can\s*cuoc)\D{0,15}?(\d{12})",
    re.IGNORECASE,
)
_PHONE_CONTEXT_RE = re.compile(
    r"(?:SĐT|SDT|số\s*điện\s*thoại|so\s*dien\s*thoai|phone)\D{0,20}?(0\d{9,10})",
    re.IGNORECASE,
)

# Fallback không ngữ cảnh: áp dụng lên chuỗi số CHƯA khớp entity nào ở trên,
# cho trường hợp câu không có từ khoá tường minh.
_CCCD_FALLBACK_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_PHONE_FALLBACK_RE = re.compile(r"(?<!\d)0\d{9,10}(?!\d)")
_BANK_FALLBACK_RE = re.compile(r"(?<!\d)\d{8,16}(?!\d)")

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _find_contextual(text: str, pattern: re.Pattern, entity_type: str) -> list[dict]:
    return [
        {"type": entity_type, "start": m.start(1), "end": m.end(1)}
        for m in pattern.finditer(text)
    ]


def _overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def detect(text: str) -> list[dict]:
    entities: list[dict] = []

    # 1) Ngữ cảnh trước (ưu tiên cao nhất — nếu có "STK"/"CCCD"/"SĐT" đứng
    #    gần thì tin theo ngữ cảnh, không đoán theo độ dài số).
    entities.extend(_find_contextual(text, _BANK_CONTEXT_RE, "VN_BANK_ACCOUNT"))
    entities.extend(_find_contextual(text, _CCCD_CONTEXT_RE, "VN_CCCD"))
    entities.extend(_find_contextual(text, _PHONE_CONTEXT_RE, "VN_PHONE"))

    # 2) Email — không đụng chuỗi số nên tách riêng.
    for m in _EMAIL_RE.finditer(text):
        entities.append({"type": "EMAIL", "start": m.start(), "end": m.end()})

    # 3) Fallback không ngữ cảnh cho chuỗi số CHƯA được entity nào ở trên
    #    phủ tới — ưu tiên CCCD (đúng 12 số) trước, rồi PHONE (0 + 9-10 số),
    #    cuối cùng BANK_ACCOUNT (8-16 số, "bắt" phần còn lại).
    def _covered(span_start: int, span_end: int) -> bool:
        return any(_overlaps({"start": span_start, "end": span_end}, e) for e in entities)

    for m in _CCCD_FALLBACK_RE.finditer(text):
        if not _covered(m.start(), m.end()):
            entities.append({"type": "VN_CCCD", "start": m.start(), "end": m.end()})

    for m in _PHONE_FALLBACK_RE.finditer(text):
        if not _covered(m.start(), m.end()):
            entities.append({"type": "VN_PHONE", "start": m.start(), "end": m.end()})

    for m in _BANK_FALLBACK_RE.finditer(text):
        if not _covered(m.start(), m.end()):
            entities.append({"type": "VN_BANK_ACCOUNT", "start": m.start(), "end": m.end()})

    entities.sort(key=lambda e: e["start"])
    return entities


def redact(text: str) -> str:
    entities = sorted(detect(text), key=lambda e: e["start"], reverse=True)
    result = text
    for entity in entities:
        placeholder = f"[REDACTED_{entity['type']}]"
        result = result[: entity["start"]] + placeholder + result[entity["end"] :]
    return result
