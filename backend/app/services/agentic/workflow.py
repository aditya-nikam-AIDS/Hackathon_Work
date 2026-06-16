from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.core.config import Settings
from backend.app.services.nlp.classifier import ClassificationResult, ComplaintClassifier
from backend.app.services.nlp.llm_client import LLMClient
from backend.app.services.nlp.preprocessor import clean_text
from backend.app.services.priority_engine import PriorityDecision, PriorityEngine
from backend.app.services.routing_engine import RoutingDecision, RoutingEngine
from backend.app.services.sla_engine import SLAEngine


WORKFLOW_VERSION = "langgraph-agentic-v1"


class ComplaintWorkflowState(TypedDict, total=False):
    complaint_text: str
    customer_id: str | None
    customer_tier: str
    metadata: dict[str, Any]
    classification_mode: Literal["auto", "llm", "tfidf"]
    created_at: datetime
    cleaned_text: str
    classification: ClassificationResult
    priority_decision: PriorityDecision
    routing_decision: RoutingDecision
    sla_deadline: datetime
    requires_human_review: bool
    recommended_actions: list[str]
    escalation_summary: str
    agent_trace: list[dict[str, Any]]


@dataclass
class AgenticTicketDecision:
    classification: ClassificationResult
    priority_decision: PriorityDecision
    routing_decision: RoutingDecision
    sla_deadline: datetime
    cleaned_text: str
    requires_human_review: bool
    recommended_actions: list[str]
    escalation_summary: str
    agent_trace: list[dict[str, Any]]
    workflow_version: str = WORKFLOW_VERSION


class ComplaintAgentWorkflow:
    def __init__(self, settings: Settings):
        self.classifier = ComplaintClassifier(settings)
        self.priority_engine = PriorityEngine()
        self.routing_engine = RoutingEngine()
        self.sla_engine = SLAEngine()
        self.llm_client = LLMClient(settings)
        self.graph = self._build_graph()

    async def process(
        self,
        *,
        complaint_text: str,
        customer_id: str | None,
        customer_tier: str,
        metadata: dict[str, Any],
        created_at: datetime,
        classification_mode: Literal["auto", "llm", "tfidf"] = "auto",
    ) -> AgenticTicketDecision:
        state = await self.graph.ainvoke(
            {
                "complaint_text": complaint_text,
                "customer_id": customer_id,
                "customer_tier": customer_tier,
                "metadata": metadata,
                "classification_mode": classification_mode,
                "created_at": created_at,
                "agent_trace": [],
                "recommended_actions": [],
                "requires_human_review": False,
                "escalation_summary": "",
            }
        )
        return AgenticTicketDecision(
            classification=state["classification"],
            priority_decision=state["priority_decision"],
            routing_decision=state["routing_decision"],
            sla_deadline=state["sla_deadline"],
            cleaned_text=state["cleaned_text"],
            requires_human_review=state.get("requires_human_review", False),
            recommended_actions=state.get("recommended_actions", []),
            escalation_summary=state.get("escalation_summary", ""),
            agent_trace=state.get("agent_trace", []),
        )

    def _build_graph(self):
        workflow = StateGraph(ComplaintWorkflowState)
        workflow.add_node("preprocess", self._preprocess)
        workflow.add_node("classify", self._classify)
        workflow.add_node("prioritize", self._prioritize)
        workflow.add_node("route", self._route)
        workflow.add_node("assign_sla", self._assign_sla)
        workflow.add_node("agent_review", self._agent_review)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "preprocess")
        workflow.add_edge("preprocess", "classify")
        workflow.add_edge("classify", "prioritize")
        workflow.add_edge("prioritize", "route")
        workflow.add_edge("route", "assign_sla")
        workflow.add_conditional_edges(
            "assign_sla",
            self._should_agent_review,
            {"agent_review": "agent_review", "finalize": "finalize"},
        )
        workflow.add_edge("agent_review", "finalize")
        workflow.add_edge("finalize", END)
        return workflow.compile()

    def _preprocess(self, state: ComplaintWorkflowState) -> dict[str, Any]:
        cleaned_text = clean_text(state["complaint_text"])
        return {
            "cleaned_text": cleaned_text,
            "agent_trace": self._trace(state, "preprocess", {"characters": len(cleaned_text)}),
        }

    async def _classify(self, state: ComplaintWorkflowState) -> dict[str, Any]:
        classification = await self.classifier.classify(
            state["complaint_text"],
            mode=state.get("classification_mode", "auto"),
        )
        return {
            "classification": classification,
            "agent_trace": self._trace(
                state,
                "classify",
                {
                    "category": classification.category,
                    "confidence": round(classification.confidence, 3),
                    "source": classification.source,
                    "requested_mode": state.get("classification_mode", "auto"),
                },
            ),
        }

    def _prioritize(self, state: ComplaintWorkflowState) -> dict[str, Any]:
        classification = state["classification"]
        priority_decision = self.priority_engine.decide(
            text=state["complaint_text"],
            category=classification.category,
            sentiment_score=classification.sentiment_score,
            customer_tier=state["customer_tier"],
        )
        return {
            "priority_decision": priority_decision,
            "agent_trace": self._trace(
                state,
                "prioritize",
                {"priority": priority_decision.priority, "score": priority_decision.score},
            ),
        }

    def _route(self, state: ComplaintWorkflowState) -> dict[str, Any]:
        classification = state["classification"]
        priority_decision = state["priority_decision"]
        routing_decision = self.routing_engine.route(
            category=classification.category,
            priority=priority_decision.priority,
            customer_tier=state["customer_tier"],
        )
        return {
            "routing_decision": routing_decision,
            "agent_trace": self._trace(
                state,
                "route",
                {"team": routing_decision.team, "rule": routing_decision.rule_name},
            ),
        }

    def _assign_sla(self, state: ComplaintWorkflowState) -> dict[str, Any]:
        priority_decision = state["priority_decision"]
        sla_deadline = self.sla_engine.deadline_for(
            created_at=state["created_at"],
            priority=priority_decision.priority,
        )
        return {
            "sla_deadline": sla_deadline,
            "agent_trace": self._trace(
                state,
                "assign_sla",
                {"deadline": sla_deadline.isoformat()},
            ),
        }

    def _should_agent_review(self, state: ComplaintWorkflowState) -> Literal["agent_review", "finalize"]:
        classification = state["classification"]
        priority = state["priority_decision"].priority
        if priority in {"critical", "high"}:
            return "agent_review"
        if classification.category == "fraud_security":
            return "agent_review"
        if classification.confidence < 0.60:
            return "agent_review"
        return "finalize"

    async def _agent_review(self, state: ComplaintWorkflowState) -> dict[str, Any]:
        classification = state["classification"]
        priority_decision = state["priority_decision"]
        routing_decision = state["routing_decision"]
        action_plan = await self.llm_client.generate_action_plan(
            complaint_text=state["complaint_text"],
            category=classification.category,
            priority=priority_decision.priority,
            team=routing_decision.team,
            sla_deadline=state["sla_deadline"].isoformat(),
        )

        if action_plan:
            return {
                "requires_human_review": action_plan.requires_human_review,
                "recommended_actions": action_plan.recommended_actions,
                "escalation_summary": action_plan.escalation_summary,
                "agent_trace": self._trace(
                    state,
                    "agent_review",
                    {
                        "source": "llm_action_planner",
                        "confidence": action_plan.confidence,
                        "requires_human_review": action_plan.requires_human_review,
                    },
                ),
            }

        fallback_actions = self._fallback_actions(priority_decision.priority, classification.category)
        return {
            "requires_human_review": priority_decision.priority in {"critical", "high"},
            "recommended_actions": fallback_actions,
            "escalation_summary": "Deterministic agent review used because LLM action planning was unavailable.",
            "agent_trace": self._trace(
                state,
                "agent_review",
                {"source": "deterministic_fallback", "actions": len(fallback_actions)},
            ),
        }

    def _finalize(self, state: ComplaintWorkflowState) -> dict[str, Any]:
        return {
            "agent_trace": self._trace(
                state,
                "finalize",
                {
                    "workflow_version": WORKFLOW_VERSION,
                    "human_review": state.get("requires_human_review", False),
                },
            )
        }

    def _fallback_actions(self, priority: str, category: str) -> list[str]:
        actions = ["Acknowledge the complaint and confirm the assigned support team."]
        if priority in {"critical", "high"}:
            actions.append("Notify the team lead and monitor SLA countdown closely.")
        if category == "fraud_security":
            actions.append("Lock risky account actions and ask Security Incident Desk to verify exposure.")
        if category == "billing":
            actions.append("Check invoice, payment, and refund history before responding.")
        return actions

    def _trace(
        self,
        state: ComplaintWorkflowState,
        node: str,
        details: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            *state.get("agent_trace", []),
            {
                "node": node,
                "details": details,
            },
        ]
