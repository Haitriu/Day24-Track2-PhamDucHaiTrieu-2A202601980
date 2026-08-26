"""Stretch #2 — So sánh Presidio/spaCy NER (tiếng Anh) vs agent/pii.py (regex)
trên tests/vn_pii_testset.jsonl.

    python -m scripts.compare_pii_ner

KHÔNG động vào agent/pii.py (đã chấm điểm ở Bước 3a) — script này độc lập,
chỉ đọc chung 1 test set để so sánh 2 cách tiếp cận.

Presidio AnalyzerEngine() mặc định chỉ có NLP engine tiếng Anh
(en_core_web_sm) — không có model tiếng Việt sẵn (đúng cảnh báo trong
Guide.md §3a và docstring agent/pii.py). Kỳ vọng: Presidio nhận diện được
EMAIL (pattern-based, không phụ thuộc ngôn ngữ) khá tốt, nhưng gần như bỏ
lỡ hoàn toàn VN_CCCD/VN_PHONE/VN_BANK_ACCOUNT vì các entity đó không nằm
trong recognizer mặc định của Presidio (chỉ có US/UK theo default), và
NLP engine tiếng Anh không "hiểu" ngữ cảnh tiếng Việt xung quanh các con số
để phân loại đúng.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent import pii as regex_pii

TESTSET_PATH = Path(__file__).resolve().parent.parent / "tests" / "vn_pii_testset.jsonl"


def _load_testset() -> list[dict]:
    with TESTSET_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def _score(testset: list[dict], detect_fn, type_match: bool = True) -> tuple[float, float, int, int, int]:
    total_gold = 0
    total_pred = 0
    true_positive = 0
    for row in testset:
        gold = row["entities"]
        pred = detect_fn(row["text"])
        total_gold += len(gold)
        total_pred += len(pred)
        matched_gold = set()
        for p in pred:
            for i, g in enumerate(gold):
                if i in matched_gold:
                    continue
                same_type = (p["type"] == g["type"]) if type_match else True
                if same_type and p["start"] < g["end"] and g["start"] < p["end"]:
                    matched_gold.add(i)
                    true_positive += 1
                    break
    precision = true_positive / total_pred if total_pred else 0.0
    recall = true_positive / total_gold if total_gold else 0.0
    return precision, recall, total_gold, total_pred, true_positive


def _presidio_detect(analyzer, text: str) -> list[dict]:
    # Presidio khong co type VN_CCCD/VN_PHONE/VN_BANK_ACCOUNT - chi map
    # PHONE_NUMBER/EMAIL_ADDRESS ve dung "type" gan nhat de so sanh cong
    # bang; moi thu khac (PERSON, LOCATION, ...) bo qua vi khong co trong
    # gold labels cua vn_pii_testset.jsonl.
    type_map = {
        "EMAIL_ADDRESS": "EMAIL",
        "PHONE_NUMBER": "VN_PHONE",
    }
    results = analyzer.analyze(text=text, language="en")
    out = []
    for r in results:
        mapped = type_map.get(r.entity_type)
        if mapped:
            out.append({"type": mapped, "start": r.start, "end": r.end})
    return out


def main() -> None:
    testset = _load_testset()

    print("=== agent/pii.py (regex, co ngu canh tieng Viet) ===")
    p, r, gold, pred, tp = _score(testset, regex_pii.detect)
    print(f"gold={gold} pred={pred} tp={tp} precision={p:.3f} recall={r:.3f}")

    print()
    print("=== Presidio AnalyzerEngine (tieng Anh, khong co model VN) ===")
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
    except ImportError:
        print("presidio-analyzer chua duoc cai (pip install presidio-analyzer).")
        print("Ket luan: khong danh gia duoc - dung agent/pii.py (regex-first) theo Guide.md.")
        return

    try:
        # Ep dung dung model nho da tai san (en_core_web_sm) - KHONG de
        # presidio tu dong tai model lon mac dinh (en_core_web_lg, ~400MB).
        nlp_config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
        provider = NlpEngineProvider(nlp_configuration=nlp_config)
        analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
    except Exception as exc:  # model spaCy chua tai / loi khoi tao NLP engine
        print(f"Khong khoi tao duoc AnalyzerEngine: {exc!r}")
        print("Chay: python -m spacy download en_core_web_sm  roi thu lai.")
        print("Ket luan: khong danh gia duoc trong moi truong nay - dung agent/pii.py.")
        return

    p2, r2, gold2, pred2, tp2 = _score(testset, lambda t: _presidio_detect(analyzer, t))
    print(f"gold={gold2} pred={pred2} tp={tp2} precision={p2:.3f} recall={r2:.3f}")

    print()
    print("=== Ket luan ===")
    print(f"regex (agent/pii.py):        recall={r:.3f}  precision={p:.3f}")
    print(f"Presidio (en, khong co VN):  recall={r2:.3f}  precision={p2:.3f}")


if __name__ == "__main__":
    main()
