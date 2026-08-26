# DPIA-lite (1 trang)

## 1. Dữ liệu gì

- `search_docs` (`agent/tools.py`) đọc toàn văn `corpus/*.md` — nội dung
  ticket hỗ trợ, có thể chứa `customer_id` (`KH-000999`) do khách hoặc
  attacker nhúng vào, nhưng KHÔNG chứa PII thô của khách (CCCD/SĐT/STK chỉ
  nằm trong `data/customers.json`, không nằm trong corpus).
- `read_customer` (`agent/tools.py`) đọc `data/customers.json` — hồ sơ đầy
  đủ 1 khách hàng: `customer_id`, `name`, `cccd` (VN_CCCD), `phone`
  (VN_PHONE), `bank_account` (VN_BANK_ACCOUNT), `email`, `related_tickets`.
  Đây là dữ liệu cá nhân nhạy cảm (CCCD, tài khoản ngân hàng).
- `agent/pii.py::detect()` nhận diện đúng 4 loại trên trong bất kỳ đoạn
  text nào (dùng bởi test suite và có thể dùng để redact trước khi log).
- `reports/ledger.jsonl` KHÔNG chứa PII thô — chỉ chứa `args_hash` (SHA-256
  của args, xem `agent/runner.py::_args_hash`), nên bản thân log audit
  không phải là một nơi lộ dữ liệu mới.

## 2. Mục đích gì

- `search_docs`: agent cần tìm ticket khớp yêu cầu người dùng ("Tổng hợp
  các ticket còn mở tuần này") để biết đang xử lý ticket nào — mục đích
  hợp lệ, không cần PII.
- `read_customer`: agent cần hồ sơ khách hàng CHỈ khi ticket đó thực sự
  thuộc về khách đó (`related_tickets`), để tổng hợp/trả lời đúng ngữ cảnh
  hỗ trợ khách hàng (`request_purpose="support-summary"` trong
  `agent/runner.py`). Đây là mục đích chính đáng, tương xứng
  (proportionate) với yêu cầu gốc — không đọc khách hàng nào không liên
  quan tới ticket đang xử lý.
- KHÔNG có mục đích hợp lệ nào cho việc `http_post` dữ liệu khách hàng ra
  ngoài trong luồng hiện tại — mọi lần `http_post` quan sát được đều bắt
  nguồn từ chỉ thị injection trong corpus (attacker), không phải từ yêu cầu
  gốc của người dùng, và bị `agent/policy.py` từ chối (classification=
  restricted + egress_enabled=True → deny).

## 3. Chảy đi đâu

- **Nội bộ**: `data/customers.json` → RAM của tiến trình Python trong lúc
  chạy → (nếu `policy.check()` allow) trả về trong `llm.summarize()` dưới
  dạng câu tóm tắt hiển thị cho người dùng CLI. Không lưu ra file nào khác
  ngoài `reports/ledger.jsonl` (chỉ chứa hash, không chứa PII thô).
- **Sink (trong lab)**: `http://localhost:9999` — mô phỏng đích exfiltration
  giả định. Sau khi contain (Bước 3), `reports/attack-after.log` xác nhận
  sink không còn nhận được gì (0 byte) dù corpus vẫn chứa đủ 5 biến thể
  injection.
- **Model provider (chỉ khi dùng `--model claude-...`, KHÔNG phải đường
  mặc định `--mock` của lab này)**: nếu chạy `agent/llm.py::RealLLM`, nội
  dung ticket (KHÔNG phải hồ sơ khách hàng — `RealLLM.summarize()` chỉ nhận
  `docs` từ `search_docs`, không nhận `collected` từ `read_customer`) được
  gửi qua Anthropic API để tóm tắt. Đây LÀ chuyển dữ liệu xuyên biên giới
  theo NĐ 356/2025 nếu hạ tầng của provider đặt ở nước ngoài — cần đánh giá
  tác động và ghi nhận trong hồ sơ chuyển dữ liệu nếu lab này được vận
  hành ngoài môi trường thử nghiệm. Do lab được **chấm bằng `--mock`**
  (không gọi mạng ra ngoài `localhost:9999`), rủi ro này không phát sinh
  trong luồng chấm điểm chính thức, nhưng vẫn phải ghi nhận ở đây vì
  `--model` là một lựa chọn hợp lệ (README §"Model dùng cho lab này").
- Không có egress control nào trong `agent/tools.py`/`agent/policy.py` che
  chắn lời gọi tới API model thật (đó là một luồng khác, không đi qua
  `http_post`) — nếu triển khai thật với `--model`, cần bổ sung classification/
  DPIA riêng cho luồng gọi model, không dùng chung với luồng `http_post`
  hiện tại.
