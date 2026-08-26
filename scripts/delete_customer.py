"""Stretch #3 — Delete cascade (quyền yêu cầu xoá, Luật 91/2025).

    python -m scripts.delete_customer KH-000777 --reason "khach yeu cau xoa du lieu"

Xoá 1 customer khỏi data/customers.json và ghi lại thao tác này vào
reports/ledger.jsonl qua agent.ledger.append() — CHỨNG MINH ledger cũ vẫn
verify()==True sau khi xoá subject: ledger không lưu PII thô (chỉ
args_hash), nên xoá 1 subject khỏi customers.json không phá tính toàn vẹn
hash-chain của các dòng ledger đã ghi trước đó nói về subject này.

Không động vào corpus/*.md (ticket vẫn còn, chỉ related_tickets của customer
biến mất cùng record) — nếu cần xoá cả nhắc tới trong ticket, đó là việc
khác (redact nội dung ticket), ngoài phạm vi stretch goal này.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent import ledger

BASE_DIR = Path(__file__).resolve().parent.parent
CUSTOMERS_FILE = BASE_DIR / "data" / "customers.json"
DEFAULT_LEDGER_PATH = BASE_DIR / "reports" / "ledger.jsonl"


def delete_customer(
    customer_id: str,
    reason: str,
    ledger_path: Path | None = None,
    customers_file: Path | None = None,
) -> dict:
    ledger_path = ledger_path or DEFAULT_LEDGER_PATH
    customers_file = customers_file or CUSTOMERS_FILE
    customers = json.loads(customers_file.read_text(encoding="utf-8"))

    remaining = [c for c in customers if c["customer_id"] != customer_id]
    if len(remaining) == len(customers):
        raise ValueError(f"customer_id khong ton tai: {customer_id}")

    customers_file.write_text(
        json.dumps(remaining, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    import datetime
    import hashlib

    entry = ledger.append(
        {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "agent_id": "lab24-agent",
            "run_id": "delete-cascade",
            "tool": "delete_customer",
            "args_hash": hashlib.sha256(
                json.dumps({"customer_id": customer_id}, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "classification": "restricted",
            "decision": "allow",
            "reason": f"right-to-delete request: {reason}",
        },
        ledger_path,
    )
    return entry


def main() -> None:
    ap = argparse.ArgumentParser(description="Xoa 1 customer (right-to-delete)")
    ap.add_argument("customer_id", help="vd KH-000777")
    ap.add_argument("--reason", default="khach hang yeu cau xoa du lieu (Luat 91/2025)")
    ap.add_argument(
        "--customers-file",
        type=Path,
        default=None,
        help="Mac dinh data/customers.json THAT. Dung --customers-file de demo tren ban "
        "sao, tranh pha fixture cua test suite (vd KH-000777 la decoy test_split.py can).",
    )
    ap.add_argument("--ledger-path", type=Path, default=None)
    args = ap.parse_args()

    entry = delete_customer(
        args.customer_id,
        args.reason,
        ledger_path=args.ledger_path,
        customers_file=args.customers_file,
    )
    print(f"Da xoa {args.customer_id} khoi {args.customers_file or CUSTOMERS_FILE}.")
    print(f"Da ghi ledger: {entry}")

    ok = ledger.verify(args.ledger_path or DEFAULT_LEDGER_PATH)
    print(f"ledger.verify() sau khi xoa subject: {ok}")


if __name__ == "__main__":
    main()
