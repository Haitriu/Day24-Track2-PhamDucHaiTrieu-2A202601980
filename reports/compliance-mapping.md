# Compliance mapping

Điền evidence là **đường dẫn file/dòng thật** trong repo của bạn — không
phải mô tả chung. Xem `Guide.md` Bước 4 và `Rubric.md`.

| Requirement | Control | Evidence |
|---|---|---|
| Luật 91/2025 — quyền yêu cầu xoá | `scripts/delete_customer.py` (stretch #3) xoá subject khỏi `data/customers.json`, ghi 1 dòng ledger `tool="delete_customer"` qua `agent.ledger.append()` mà không phá tính toàn vẹn hash-chain | `reports/delete-cascade-demo.md` |
| NĐ 356/2025 — hồ sơ xuyên biên giới 60 ngày | data-flow inventory cho trường hợp dùng `--model` (Claude API) | `reports/dpia-lite.md` §3 |
| ASI03 — privilege abuse | per-run identity (`agent_owner="run-a"`/`"run-b"`/`"run-b-egress"`) truyền qua `PolicyContext`, ghi vào field `agent_owner` của mọi dòng ledger | `agent/policy.py` (dataclass `PolicyContext`, dòng 30-36), `agent/runner.py` (dòng 113-121, 145-153, 178-186), `reports/ledger.jsonl` field `agent_owner` |
| ASI01 — goal hijack | trifecta split: Run A (`search_docs` only) không bao giờ đọc `customer_id`/URL từ free text; Run B tra `customer_id` qua `related_tickets` (nguồn tin cậy), không qua `injected.customer_ids` | `agent/runner.py` dòng 128-152 (`_extract_ticket_ids`, `_customers_for_tickets`); bằng chứng chạy: `reports/attack-after.log` (rỗng) + `pytest tests/test_split.py` pass (KH-000777 không bao giờ bị `read_customer` gọi tới) |
| ISO 42001 Clause 5-6 | policy-as-code (`agent/policy.py`) có review qua git history, mỗi thay đổi rule là 1 commit riêng biệt, có thể audit | `git log --oneline -- agent/policy.py` (commit `e48b6d7` "BUOC 3b: implement agent/policy.py - PEP + minimum deny rule") |
