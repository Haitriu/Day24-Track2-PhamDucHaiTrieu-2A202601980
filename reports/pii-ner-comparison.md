# Stretch #2 — So sánh Presidio/spaCy NER vs regex (`agent/pii.py`) cho PII tiếng Việt

## Cách chạy

```bash
python -m spacy download en_core_web_sm   # 1 lần, model nho (~13MB)
python -m scripts.compare_pii_ner
```

## Kết quả chạy thật (trên `tests/vn_pii_testset.jsonl`, 120 mẫu / 118 entity)

```
=== agent/pii.py (regex, co ngu canh tieng Viet) ===
gold=118 pred=118 tp=118 precision=1.000 recall=1.000

=== Presidio AnalyzerEngine (tieng Anh, khong co model VN) ===
gold=118 pred=60 tp=53 precision=0.883 recall=0.449

=== Ket luan ===
regex (agent/pii.py):        recall=1.000  precision=1.000
Presidio (en, khong co VN):  recall=0.449  precision=0.883
```

(`presidio-analyzer` 2.2.364 + `spacy` 3.8.15 + model `en_core_web_sm`, ép
dùng qua `NlpEngineProvider` để tránh Presidio tự tải model lớn mặc định
`en_core_web_lg` ~400MB — xem `scripts/compare_pii_ner.py`.)

## Vì sao Presidio kém hơn hẳn ở đây

- Presidio mặc định **không có recognizer nào cho VN_CCCD/VN_PHONE/
  VN_BANK_ACCOUNT** — các recognizer built-in chỉ nhắm tới định dạng
  Mỹ/Anh (`US_SSN`, `UK_NHS`...), nên 118 entity gold trong test set gần
  như không khớp type nào Presidio biết sẵn.
- NLP engine dùng ở đây là `en_core_web_sm` (tiếng Anh) — không hiểu ngữ
  cảnh tiếng Việt xung quanh con số (vd "CCCD của X:", "STK ...") để suy
  luận entity type, nên **56/118** entity gold hoàn toàn không được match
  (`recall=0.449`, tức chỉ bắt được số PHONE_NUMBER khớp coincidentally +
  EMAIL_ADDRESS — 2 pattern global không phụ thuộc ngôn ngữ).
- `precision=0.883` (không quá tệ) vì Presidio ít "đoán bừa" — chủ yếu chỉ
  trả về EMAIL_ADDRESS (pattern chuẩn, ngôn ngữ nào cũng đúng) và một số
  PHONE_NUMBER khớp coincidentally với gold nhờ pattern số điện thoại quốc
  tế, nên false positive thấp — nhưng false NEGATIVE (bỏ sót) rất cao.
- `agent/pii.py` đạt `precision=1.000 recall=1.000` vì được thiết kế CÓ NGỮ
  CẢNH tiếng Việt tường minh (từ khoá "CCCD"/"STK"/"SĐT" — xem
  `agent/pii.py` dòng 33-46) đúng với format thực tế của dữ liệu lab,
  trong khi Presidio là 1 công cụ tổng quát không có kiến thức miền
  (domain knowledge) này sẵn.

## Kết luận (khớp cảnh báo trong Guide.md §3a và docstring `agent/pii.py`)

Presidio không có tiếng Việt sẵn (`AnalyzerEngine()` mặc định chỉ hỗ trợ
`en`) — số liệu thật ở trên xác nhận: dùng thẳng Presidio cho PII tiếng
Việt trong 2h của lab này SẼ THẤT BẠI RÕ RỆT (`recall=0.449` < ngưỡng fail
`50%` của `test_pii.py`). Hướng đúng cho bài lab — regex có ngữ cảnh — đã
đạt 100%/100% và là lựa chọn hợp lý về thời gian lẫn kết quả. Presidio chỉ
trở nên đáng dùng nếu có custom recognizer viết riêng cho từng loại PII
tiếng Việt (ngoài phạm vi 2h của lab), lúc đó lợi thế của Presidio là
framework quản lý nhiều recognizer/language có sẵn, không phải khả năng
"hiểu" tiếng Việt tự nhiên.
