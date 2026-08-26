# Stretch #1 — So sánh `agent/policy.py` (Python) vs `policy/policy.rego` (OPA/Rego)

`policy/policy.rego` port lại đúng logic của `agent/policy.py::check()` —
đã xác minh output khớp 1-1 bằng `opa eval` trên cả 3 case
`tests/test_policy.py` dùng:

```
opa eval -i input.json -d policy/policy.rego "data.lab24.policy.allow"
opa eval -i input.json -d policy/policy.rego "data.lab24.policy.reason"
```

| Case | Python `check()` | Rego `allow`/`reason` |
|---|---|---|
| `restricted` + `egress_enabled=True` | `(False, "deny: restricted data khong duoc phep egress...")` | `false` / `"deny: restricted data khong duoc phep egress..."` |
| `internal` + `egress_enabled=False` | `(True, "allow: internal data, egress_enabled=False...")` | `true` / `"allow: internal data, egress_enabled=False..."` |
| `public` + `egress_enabled=True` | `(True, "allow: data_classification=public...")` | `true` / `"allow: data_classification=public..."` |

Kết quả `opa eval` khớp chính xác từng ký tự với `agent/policy.py::check()`
(đã chạy thật, không phải suy diễn — xem log trong phần "Kết quả chạy thật"
bên dưới).

## Kết quả chạy thật

```
=== restricted_egress ===
false
"deny: restricted data khong duoc phep egress trong cung 1 run (agent_owner=run-b, purpose=reconciliation)"
=== internal_no_egress ===
true
"allow: internal data, egress_enabled=False trong run nay (agent_owner=run-a, purpose=summarize-tickets)"
=== public ===
true
"allow: data_classification=public, khong co rui ro ro ri (agent_owner=run-a, purpose=faq)"
```
(môi trường thực thi: `opa version` → `Version: 1.19.1`, tải từ
`https://openpolicyagent.org/downloads/latest/opa_windows_amd64.exe`)

## So sánh biểu cảm / khả năng test / khả năng review

| Tiêu chí | `agent/policy.py` (Python) | `policy/policy.rego` (OPA/Rego) |
|---|---|---|
| **Biểu cảm** | Code mệnh lệnh (if/else tuần tự), dễ đọc với người quen Python, nhưng thứ tự các `if` ẩn implicit priority — dễ vô tình đổi kết quả khi thêm rule mới vào giữa | Khai báo (declarative): mỗi `deny`/`allow` là 1 rule độc lập, engine tự OR các rule cùng tên lại — thêm rule mới không phá rule cũ nếu không cố tình `not deny` sai chỗ. Rõ ràng hơn khi luật nghiệp vụ nhiều và tăng dần theo thời gian |
| **Khả năng test** | `pytest tests/test_policy.py` — test đơn vị bình thường, chạy trong process, dễ debug bằng breakpoint | `opa eval` chạy độc lập binary ngoài — cần cài `opa` CLI (không có sẵn trong `requirements.txt`), nhưng `opa test` hỗ trợ viết test case ngay trong `.rego` (không làm ở đây do phạm vi stretch), và test hoàn toàn tách khỏi runtime Python — hữu ích nếu muốn 1 policy dùng chung cho nhiều service không phải Python |
| **Khả năng review** | Review qua git diff của file `.py` bình thường — người review cần đọc hiểu logic if/else | Rego buộc tác giả tách rõ từng điều kiện thành rule có tên (`deny_restricted_egress`, `deny_delegated_restricted`) — review dễ hơn vì mỗi rule trả lời đúng 1 câu hỏi nghiệp vụ, tên rule tự làm tài liệu. Đây là ưu điểm chính của "policy-as-code" tách khỏi code nghiệp vụ (khớp `ISO 42001 Clause 5-6` trong `compliance-mapping.md`) |
| **Vận hành thực tế trong lab này** | Đã tích hợp trực tiếp vào `agent/runner.py`, chấm điểm bằng `pytest --mock`, không cần cài thêm gì | Chỉ dùng để CHỨNG MINH tính tương đương — KHÔNG được dùng thay `agent/policy.py` trong luồng chấm điểm chính thức (rubric yêu cầu `pytest tests/test_policy.py` chạy trên Python), cần cài `opa` CLI riêng (đã tải thành công trong môi trường này, không có sẵn mặc định) |

## Kết luận

Rule tối thiểu bắt buộc (`classification == "restricted" and egress_enabled`
→ deny) được giữ **nguyên nghĩa** ở cả 2 bản port — không bị làm yếu đi khi
chuyển sang Rego. Với quy mô policy nhỏ như bài lab này, Python đã đủ dùng
và không cần thêm dependency `opa`; Rego trở nên đáng giá hơn khi số lượng
rule tăng lên và cần nhiều team/service không phải Python cùng dùng chung
1 nguồn policy.
