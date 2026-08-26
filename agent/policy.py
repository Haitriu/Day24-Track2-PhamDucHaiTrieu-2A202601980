"""BƯỚC 3b — PEP (Policy Enforcement Point) tại tool call (15').

Cổng chặn TRƯỚC KHI tool thật sự execute. Đọc Guide.md (§3b).

Interface bắt buộc (tests/test_policy.py và agent/runner.py gọi trực tiếp):

    check(context: PolicyContext) -> tuple[bool, str]
        Trả về (allow, reason).
        `reason` KHÔNG BAO GIỜ được để trống — cả khi allow=True và
        allow=False. Đây là evidence audit ở Bước 4 (rubric: "Audit
        completeness = 100%" — điều kiện trượt nếu có dòng thiếu reason).

PolicyContext — 5 input đúng slide §3.3 (đã định nghĩa sẵn, đừng đổi field):

    data_classification: str   "public" | "internal" | "restricted"
    request_purpose: str       tự do, ví dụ "reconciliation", "support-reply"
    agent_owner: str            định danh agent/run gọi tool này
    delegation_depth: int       0 = gọi trực tiếp bởi user, >0 = agent gọi agent
    egress_enabled: bool        run hiện tại có được phép gọi network không

Rule TỐI THIỂU bắt buộc (không được viết yếu hơn rule này):

    classification == "restricted" and egress_enabled is True  ->  DENY
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyContext:
    data_classification: str
    request_purpose: str
    agent_owner: str
    delegation_depth: int
    egress_enabled: bool


def check(context: PolicyContext) -> tuple[bool, str]:
    # Rule tối thiểu bắt buộc: dữ liệu restricted không bao giờ được đi kèm
    # egress trong CÙNG một run — đây chính là cái chặn attacker POST PII ra
    # sink dù read_customer có được gọi hay không.
    if context.data_classification == "restricted" and context.egress_enabled:
        return False, (
            "deny: restricted data khong duoc phep egress trong cung 1 run "
            f"(agent_owner={context.agent_owner}, purpose={context.request_purpose})"
        )

    # Delegation sâu (agent gọi agent, do injected instruction tạo ra) không
    # được phép request dữ liệu restricted — chặn sớm trước khi tool chạy,
    # kể cả khi run đó chưa bật egress.
    if context.delegation_depth > 0 and context.data_classification == "restricted":
        return False, (
            "deny: delegation_depth > 0 khong duoc doc du lieu restricted "
            f"(agent_owner={context.agent_owner}, depth={context.delegation_depth})"
        )

    # Public data luôn được phép, kể cả có egress (không phải bí mật).
    if context.data_classification == "public":
        return True, (
            f"allow: data_classification=public, khong co rui ro ro ri "
            f"(agent_owner={context.agent_owner}, purpose={context.request_purpose})"
        )

    # Internal data: cho phép đọc nếu KHÔNG egress trong cùng run (đúng luồng
    # Run B của runner.py — đọc customer để tổng hợp, không gửi đi đâu).
    if context.data_classification == "internal" and not context.egress_enabled:
        return True, (
            "allow: internal data, egress_enabled=False trong run nay "
            f"(agent_owner={context.agent_owner}, purpose={context.request_purpose})"
        )

    # Mọi trường hợp còn lại (vd internal + egress_enabled=True) mặc định
    # deny — không có rule minh thị nào cho phép nó.
    return False, (
        f"deny: khong co rule nao cho phep classification={context.data_classification} "
        f"voi egress_enabled={context.egress_enabled} "
        f"(agent_owner={context.agent_owner}, purpose={context.request_purpose})"
    )
