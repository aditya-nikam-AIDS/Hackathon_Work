from dataclasses import dataclass


# Banking domain team routing
DEFAULT_ROUTES = {
    "transaction_issue": "Payments Team",
    "account_issue": "Customer Support Team",
    "fraud_security": "Fraud Investigation Team",
    "loan_credit_issue": "Loan Department",
    "technical_issue": "IT Support Team",
    "general": "Customer Support Team",
}


@dataclass
class RoutingDecision:
    team: str
    rule_name: str


class RoutingEngine:
    def __init__(self, routes: dict[str, str] | None = None):
        self.routes = routes or DEFAULT_ROUTES

    def route(self, *, category: str, priority: str, customer_tier: str) -> RoutingDecision:
        # Fraud/security incidents get escalated to dedicated desk for critical/high priority
        if category == "fraud_security" and priority in {"critical", "high"}:
            return RoutingDecision(team="Fraud Incident Response Team", rule_name="fraud_high_priority_override")

        # VIP customers with critical issues get executive banking support
        if customer_tier == "vip" and priority == "critical":
            return RoutingDecision(team="Priority Banking Desk", rule_name="vip_critical_override")

        # Premium customers with high priority get relationship manager escalation
        if customer_tier == "premium" and priority in {"critical", "high"}:
            return RoutingDecision(team="Relationship Manager Team", rule_name="premium_high_priority_override")

        return RoutingDecision(
            team=self.routes.get(category, self.routes["general"]),
            rule_name=f"category_to_team:{category}",
        )

