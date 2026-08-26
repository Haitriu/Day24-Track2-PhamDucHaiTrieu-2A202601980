# Stretch #1 — Port agent/policy.py sang OPA/Rego.
#
# Mo phong dung logic cua agent/policy.py::check() (Buoc 3b). Input tuong
# ung 1-1 voi PolicyContext (agent/policy.py dong 30-36):
#
#   input.data_classification  "public" | "internal" | "restricted"
#   input.request_purpose      string
#   input.agent_owner          string
#   input.delegation_depth     int
#   input.egress_enabled       bool
#
# Cach dung:
#   opa eval -i input.json -d policy/policy.rego "data.lab24.policy.allow"
#   opa eval -i input.json -d policy/policy.rego "data.lab24.policy.reason"
#
# Rule toi thieu bat buoc cua bai lab (Guide.md / agent/policy.py dong
# 21-23): classification == "restricted" and egress_enabled -> DENY. Rule
# nay duoc giu nguyen nghia trong `deny_restricted_egress` duoi day - day la
# rule KHONG duoc lam yeu di khi port sang Rego.

package lab24.policy

import future.keywords.if

default allow := false

# ---- Rule toi thieu bat buoc: restricted + egress luon bi tu choi ----
deny_restricted_egress if {
	input.data_classification == "restricted"
	input.egress_enabled == true
}

# ---- Delegation sau khong duoc doc du lieu restricted ----
deny_delegated_restricted if {
	input.delegation_depth > 0
	input.data_classification == "restricted"
}

deny if deny_restricted_egress
deny if deny_delegated_restricted

# ---- Allow: public luon duoc phep ----
allow if {
	not deny
	input.data_classification == "public"
}

# ---- Allow: internal duoc phep khi KHONG egress trong cung run ----
allow if {
	not deny
	input.data_classification == "internal"
	input.egress_enabled == false
}

# reason luon khong rong - tuong duong yeu cau "reason khong bao gio duoc de
# trong" trong agent/policy.py (docstring dong 9-11).
reason := r if {
	deny_restricted_egress
	r := sprintf(
		"deny: restricted data khong duoc phep egress trong cung 1 run (agent_owner=%s, purpose=%s)",
		[input.agent_owner, input.request_purpose],
	)
} else := r if {
	deny_delegated_restricted
	r := sprintf(
		"deny: delegation_depth > 0 khong duoc doc du lieu restricted (agent_owner=%s, depth=%d)",
		[input.agent_owner, input.delegation_depth],
	)
} else := r if {
	allow
	input.data_classification == "public"
	r := sprintf(
		"allow: data_classification=public, khong co rui ro ro ri (agent_owner=%s, purpose=%s)",
		[input.agent_owner, input.request_purpose],
	)
} else := r if {
	allow
	input.data_classification == "internal"
	r := sprintf(
		"allow: internal data, egress_enabled=False trong run nay (agent_owner=%s, purpose=%s)",
		[input.agent_owner, input.request_purpose],
	)
} else := r if {
	r := sprintf(
		"deny: khong co rule nao cho phep classification=%s voi egress_enabled=%v (agent_owner=%s, purpose=%s)",
		[input.data_classification, input.egress_enabled, input.agent_owner, input.request_purpose],
	)
}
