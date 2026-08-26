"""BƯỚC 3c — trifecta split + egress allowlist (13'). ĐÂY LÀ PHẦN KHÓ NHẤT.

Đọc Guide.md (§3c) trước khi viết code. Tóm tắt yêu cầu:

Tách 1 yêu cầu người dùng thành ít nhất 2 run riêng biệt — KHÔNG run nào
được cầm cả 3 chân của trifecta cùng lúc:

    Run A: gọi search_docs (untrusted content).
           KHÔNG gọi read_customer. KHÔNG gọi http_post.
    Run B: gọi read_customer (private data).
           CHỈ nhận input là TYPED, ĐÃ SANITIZE từ Run A — ví dụ
           list[int] ticket id trích từ TÊN FILE (vd "ticket-007.md" -> 7),
           KHÔNG BAO GIỜ nhận nguyên văn text của document. free text của
           attacker không được đi xa hơn Run A.

Mọi lần gọi tool (allow HAY deny) phải:
  1. Đi qua `agent.policy.check()` TRƯỚC KHI tool thật sự chạy.
  2. Được ghi vào ledger qua `agent.ledger.append()` — cả khi deny.
Nếu policy deny, KHÔNG được gọi tool đó.

--- Gợi ý kiến trúc (không bắt buộc theo đúng, nhưng đủ để làm trong 13') ---

data/customers.json có field `related_tickets: list[int]` cho mỗi khách
hàng — đây là NGUỒN TIN CẬY để map ticket_id -> customer_id, KHÔNG map qua
customer_id mà attacker nhúng trong nội dung document. Cụ thể:

    Run A: search_docs(message) -> lấy list[int] ticket_id từ TÊN FILE của
           các doc khớp (vd "ticket-999.md" -> 999). Cũng chạy
           llm.find_injection() trên text để log lại (KHÔNG dùng
           customer_id mà nó trả về).
    Run B: với mỗi ticket_id nhận từ Run A, tìm customer nào trong
           customers.json có ticket_id trong related_tickets, rồi
           read_customer(customer_id) đó — không phải customer_id lấy từ
           text tự do.

Vì sao cách này chống được biến thể 5 (không dấu / lookalike): filter
chuỗi thô sẽ luôn có thể bị né bằng cách viết lại chỉ thị, nhưng nếu Run B
không bao giờ ĐỌC free text để quyết định gọi ai, thì việc né filter chuỗi
trở nên vô nghĩa — đây là containment (kiến trúc), khác với mitigation
(bộ lọc). Sinh viên NÊN thử filter chuỗi trước, rồi tự phá nó bằng biến
thể 5, trước khi chuyển sang cách này.

Interface bắt buộc (agent/loop.py import và gọi hàm này nếu tồn tại):

    handle(message: str, llm, log_dir: pathlib.Path | None = None) -> str
        `llm` cung cấp:
            llm.find_injection(text: str) -> InjectedInstruction | None
            llm.summarize(docs: list[dict]) -> str
        `log_dir` là thư mục chứa ledger.jsonl (mặc định: reports/).
        Trả về câu trả lời cuối cùng hiển thị cho người dùng — hành vi
        quan sát được từ ngoài (CLI) không đổi so với trước khi contain,
        chỉ có sink log và ledger là khác.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from agent import ledger as ledger_module
from agent import policy as policy_module
from agent import tools

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DEFAULT_LEDGER_PATH = REPORTS_DIR / "ledger.jsonl"
CUSTOMERS_FILE = Path(__file__).resolve().parent.parent / "data" / "customers.json"

AGENT_ID = "lab24-agent"
_TICKET_ID_RE = re.compile(r"ticket-(\d+)")


def _args_hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _log(ledger_path: Path, *, run_id: str, tool: str, decision: str, reason: str,
          classification: str, args_hash: str) -> None:
    ledger_module.append(
        {
            "ts": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "agent_id": AGENT_ID,
            "run_id": run_id,
            "tool": tool,
            "args_hash": args_hash,
            "classification": classification,
            "decision": decision,
            "reason": reason,
        },
        ledger_path,
    )


def _extract_ticket_ids(docs: list[dict]) -> list[int]:
    """Chân Run A: chỉ tin tên file, KHÔNG bao giờ đọc customer_id trong text."""
    ticket_ids = []
    for doc in docs:
        match = _TICKET_ID_RE.search(doc["id"])
        if match:
            ticket_ids.append(int(match.group(1)))
    return ticket_ids


def _customers_for_tickets(ticket_ids: list[int]) -> list[dict]:
    """Nguồn tin cậy duy nhất để map ticket_id -> customer: related_tickets
    trong data/customers.json. KHÔNG bao giờ dùng customer_id trích từ free
    text của attacker (injected.customer_ids)."""
    customers = json.loads(CUSTOMERS_FILE.read_text(encoding="utf-8"))
    ticket_id_set = set(ticket_ids)
    return [c for c in customers if ticket_id_set & set(c.get("related_tickets", []))]


def handle(message: str, llm, log_dir: Path | None = None) -> str:
    ledger_path = Path(log_dir) / "ledger.jsonl" if log_dir is not None else DEFAULT_LEDGER_PATH

    # ---------- Run A: search_docs only, không read_customer/http_post ----------
    run_a_id = "run-a"
    ctx_a = policy_module.PolicyContext(
        data_classification="public",
        request_purpose="search-tickets",
        agent_owner=run_a_id,
        delegation_depth=0,
        egress_enabled=False,
    )
    allow_a, reason_a = policy_module.check(ctx_a)
    _log(
        ledger_path,
        run_id=run_a_id,
        tool="search_docs",
        decision="allow" if allow_a else "deny",
        reason=reason_a,
        classification=ctx_a.data_classification,
        args_hash=_args_hash({"query": message}),
    )
    if not allow_a:
        return "Yêu cầu bị từ chối bởi policy trước khi tìm ticket."

    docs = tools.search_docs(message)

    # find_injection chỉ dùng để LOG bằng chứng injection, KHÔNG bao giờ
    # dùng injected.customer_ids để quyết định gọi read_customer cho ai.
    combined_text = "\n\n".join(d["text"] for d in docs)
    injected = llm.find_injection(combined_text)

    ticket_ids = _extract_ticket_ids(docs)

    # ---------- Run B: read_customer, chỉ nhận typed ticket_id từ Run A ----------
    run_b_id = "run-b"
    collected = []
    for customer in _customers_for_tickets(ticket_ids):
        ctx_b = policy_module.PolicyContext(
            data_classification="internal",
            request_purpose="support-summary",
            agent_owner=run_b_id,
            delegation_depth=0,
            egress_enabled=False,
        )
        allow_b, reason_b = policy_module.check(ctx_b)
        _log(
            ledger_path,
            run_id=run_b_id,
            tool="read_customer",
            decision="allow" if allow_b else "deny",
            reason=reason_b,
            classification=ctx_b.data_classification,
            args_hash=_args_hash({"customer_id": customer["customer_id"]}),
        )
        if allow_b:
            try:
                collected.append(tools.read_customer(customer["customer_id"]))
            except tools.ToolError:
                continue

    # ---------- Egress attempt: chỉ khi corpus chứa chỉ thị injection ----------
    # target_url/target luôn bị coi là restricted + egress -> policy tối
    # thiểu sẽ deny, và tools.http_post() KHÔNG BAO GIỜ được gọi khi bị deny.
    if injected is not None:
        run_egress_id = "run-b-egress"
        ctx_egress = policy_module.PolicyContext(
            data_classification="restricted",
            request_purpose="reconciliation-egress(injected-instruction)",
            agent_owner=run_egress_id,
            delegation_depth=1,
            egress_enabled=True,
        )
        allow_egress, reason_egress = policy_module.check(ctx_egress)
        _log(
            ledger_path,
            run_id=run_egress_id,
            tool="http_post",
            decision="allow" if allow_egress else "deny",
            reason=reason_egress,
            classification=ctx_egress.data_classification,
            args_hash=_args_hash({"url": injected.target_url, "n_records": len(collected)}),
        )
        if allow_egress:
            tools.http_post(injected.target_url, {"records": collected})

    return llm.summarize(docs)
