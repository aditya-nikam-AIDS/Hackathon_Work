from dataclasses import dataclass


DEFAULT_ROUTES = {
    "billing": "Billing Operations",
    "technical": "Technical Support",
    "delivery": "Logistics Support",
    "product_quality": "Quality Assurance",
    "account": "Account Operations",
    "fraud_security": "Security Response",
    "refund": "Refunds Desk",
    "general": "Customer Care",
}


@dataclass
class RoutingDecision:
    team: str
    rule_name: str


class RoutingEngine:
    def __init__(self, routes: dict[str, str] | None = None):
        self.routes = routes or DEFAULT_ROUTES

    def route(self, *, category: str, priority: str, customer_tier: str) -> RoutingDecision:
        if category == "fraud_security" and priority in {"critical", "high"}:
            return RoutingDecision(team="Security Incident Desk", rule_name="fraud_high_priority_override")

        if customer_tier == "vip" and priority == "critical":
            return RoutingDecision(team="Executive Support", rule_name="vip_critical_override")

        return RoutingDecision(
            team=self.routes.get(category, self.routes["general"]),
            rule_name=f"category_to_team:{category}",
        )

