# Stretch #3 — Delete cascade (right-to-delete demo)

Yêu cầu: Luật 91/2025 cho phép chủ thể dữ liệu yêu cầu xoá dữ liệu cá nhân
của họ. `scripts/delete_customer.py` triển khai control này và chứng minh
việc xoá subject KHÔNG phá tính toàn vẹn của audit ledger đã ghi trước đó.

## Cách chạy (KHÔNG chạy trên `data/customers.json` thật khi demo/test — sẽ
phá fixture `KH-000777` decoy mà `tests/test_split.py` cần)

```bash
python -m scripts.delete_customer KH-000777 \
  --reason "khach yeu cau xoa du lieu (demo stretch #3)" \
  --customers-file <ban-sao-customers.json> \
  --ledger-path <ban-sao-ledger.jsonl>
```

Chạy thật (production) không truyền `--customers-file`/`--ledger-path` sẽ
tác động lên `data/customers.json` và `reports/ledger.jsonl` thật.

## Kết quả demo (chạy trên bản sao, seed sẵn 1 dòng ledger `read_customer`
cho KH-000777 trước khi xoá, để mô phỏng: subject đã từng có hoạt động
được ghi log, sau đó bị xoá)

**Trước khi xoá** — ledger có 1 dòng `read_customer` cho KH-000777 (giả lập
hoạt động lịch sử), `ledger.verify() == True`.

**Lệnh xoá:**
```
Da xoa KH-000777 khoi <...customers.json>.
Da ghi ledger: {'ts': '2026-08-26T14:13:14...', 'agent_id': 'lab24-agent',
'run_id': 'delete-cascade', 'tool': 'delete_customer',
'args_hash': '9f4db027...', 'classification': 'restricted',
'decision': 'allow', 'reason': 'right-to-delete request: khach yeu cau
xoa du lieu (demo stretch #3)', ...}
ledger.verify() sau khi xoa subject: True
```

**Sau khi xoá:**
- `customers.json`: KH-000777 không còn trong danh sách (25/26 record còn
  lại — xác nhận bằng `any(c["customer_id"]=="KH-000777" for c in customers)
  == False`).
- `ledger.jsonl`: cả dòng cũ (`read_customer` cho KH-000777) VÀ dòng mới
  (`delete_customer`) đều còn nguyên, hash-chain vẫn liên tục
  (`prev_hash` dòng 2 == `hash` dòng 1), `ledger.verify() == True`.

## Vì sao xoá subject không phá tính toàn vẹn ledger

`agent/ledger.py` không bao giờ lưu PII thô — mỗi dòng chỉ có `args_hash`
(SHA-256 của args, xem `agent/runner.py::_args_hash`), không có `name`,
`cccd`, `phone`, `bank_account` nào trong log. Vì vậy xoá 1 subject khỏi
`data/customers.json` (nguồn dữ liệu sống) không cần và không được phép
xoá ngược lại các dòng ledger đã ghi về họ — ledger là **bằng chứng lịch sử
bất biến** (ai đã truy cập, khi nào, được phép hay không, vì sao), tách
biệt hoàn toàn khỏi kho dữ liệu sống. Đây chính là lý do tại sao
`right-to-delete` (xoá dữ liệu sống) và `audit trail` (giữ nguyên lịch sử
truy cập) không mâu thuẫn nhau trong kiến trúc này.
