"""
Optimization utilities for the banking ticketing system.
Includes caching, duplicate detection, and performance improvements.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import Ticket


class TicketOptimizer:
    """Optimization utilities for ticket processing."""

    def __init__(self, cache_ttl_minutes: int = 30):
        self.cache_ttl_minutes = cache_ttl_minutes
        self._llm_cache: dict[str, tuple[Any, datetime]] = {}

    def get_cached_llm_response(self, complaint_text: str) -> Any | None:
        """Get cached LLM response if available and not expired."""
        cache_key = self._get_cache_key(complaint_text)
        if cache_key in self._llm_cache:
            response, cached_at = self._llm_cache[cache_key]
            if datetime.now(timezone.utc) - cached_at < timedelta(minutes=self.cache_ttl_minutes):
                return response
            del self._llm_cache[cache_key]
        return None

    def cache_llm_response(self, complaint_text: str, response: Any) -> None:
        """Cache LLM response for reuse."""
        cache_key = self._get_cache_key(complaint_text)
        self._llm_cache[cache_key] = (response, datetime.now(timezone.utc))
        
        # Cleanup old cache entries (keep last 1000)
        if len(self._llm_cache) > 1000:
            sorted_items = sorted(self._llm_cache.items(), key=lambda x: x[1][1])
            self._llm_cache = dict(sorted_items[-500:])

    def find_similar_tickets(
        self,
        db: Session,
        complaint_text: str,
        customer_id: str | None,
        threshold_hours: int = 24,
        similarity_threshold: float = 0.85,
    ) -> list[Ticket]:
        """
        Find similar recent tickets to detect duplicates.
        Uses simple text similarity based on common words.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=threshold_hours)
        
        # Get recent tickets
        query = select(Ticket).where(Ticket.created_at >= cutoff)
        if customer_id:
            query = query.where(Ticket.customer_id == customer_id)
        
        recent_tickets = db.execute(query).scalars().all()
        
        # Calculate similarity
        similar = []
        text_words = set(self._normalize_text(complaint_text).split())
        
        for ticket in recent_tickets:
            ticket_words = set(self._normalize_text(ticket.complaint_text).split())
            if text_words and ticket_words:
                intersection = len(text_words & ticket_words)
                union = len(text_words | ticket_words)
                similarity = intersection / union if union > 0 else 0
                
                if similarity >= similarity_threshold:
                    similar.append(ticket)
        
        return similar

    def get_workload_balance(self, db: Session) -> dict[str, dict[str, Any]]:
        """Get current team workload for intelligent routing."""
        # Query open tickets grouped by team
        from sqlalchemy import func as sql_func
        
        open_tickets = select(
            Ticket.team,
            sql_func.count(Ticket.id).label("open_count"),
        ).where(
            Ticket.status.in_(["open", "in_progress"])
        ).group_by(Ticket.team)
        
        results = db.execute(open_tickets).all()
        
        return {
            row.team: {
                "open_tickets": row.open_count,
                "avg_sla_remaining": 0,  # Would need to calculate from SLA deadline
                "load_factor": row.open_count / 10  # Assume 10 is ideal capacity
            }
            for row in results
        }

    def calculate_confidence_score(
        self,
        classification_confidence: float,
        priority_score: float,
        has_similar_tickets: bool,
    ) -> float:
        """Calculate overall confidence score for ticket processing."""
        base_confidence = classification_confidence * 0.6 + (priority_score / 10) * 0.3
        
        if has_similar_tickets:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)

    def suggest_auto_response(self, category: str, priority: str) -> str | None:
        """Suggest automated response templates based on category."""
        responses = {
            ("transaction_issue", "high"): (
                "Thank you for reporting this transaction issue. We have escalated your case "
                "to our Payments Team with high priority. You will receive a resolution within 4 hours. "
                "Reference ID: {ticket_id}"
            ),
            ("fraud_security", "critical"): (
                "Your security concern has been received and is being handled by our Fraud Investigation Team "
                "immediately. Please do not share any OTPs or passwords. We will contact you within 1 hour. "
                "Reference ID: {ticket_id}"
            ),
            ("account_issue", "medium"): (
                "We have received your account-related query. Our Customer Support Team will "
                "assist you within 12 hours. Reference ID: {ticket_id}"
            ),
        }
        return responses.get((category, priority))

    @staticmethod
    def _get_cache_key(text: str) -> str:
        """Generate cache key from text."""
        normalized = text.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


# Ticket templates for common banking issues
BANKING_TICKET_TEMPLATES = {
    "upi_failed": {
        "title": "UPI Payment Failed",
        "template": "My UPI payment to {merchant} for Rs {amount} failed but money was deducted from my account. Transaction ID: {txn_id}. Please help.",
        "category_hint": "transaction_issue",
        "priority_hint": "high",
    },
    "unauthorized_txn": {
        "title": "Unauthorized Transaction",
        "template": "I see an unauthorized transaction of Rs {amount} on my account dated {date}. I did not make this transaction. Transaction ID: {txn_id}.",
        "category_hint": "fraud_security",
        "priority_hint": "critical",
    },
    "account_locked": {
        "title": "Account Locked",
        "template": "My account has been locked/blocked and I cannot access net banking or mobile app. Please help unlock my account urgently.",
        "category_hint": "account_issue",
        "priority_hint": "high",
    },
    "kyc_update": {
        "title": "KYC Update Request",
        "template": "I need to update my KYC details - {detail_type}. Please guide me on the process.",
        "category_hint": "account_issue",
        "priority_hint": "medium",
    },
    "emi_issue": {
        "title": "EMI/Loan Issue",
        "template": "I have an issue with my {loan_type} loan. EMI amount showing is incorrect. Loan account number: {account_no}.",
        "category_hint": "loan_credit_issue",
        "priority_hint": "medium",
    },
    "app_not_working": {
        "title": "Mobile App Issue",
        "template": "The mobile banking app is {issue_description}. I am unable to access my account. App version: {version}.",
        "category_hint": "technical_issue",
        "priority_hint": "medium",
    },
}


# Performance metrics tracking
class PerformanceMetrics:
    """Track system performance metrics."""
    
    def __init__(self):
        self.metrics = {
            "total_tickets_processed": 0,
            "llm_cache_hits": 0,
            "llm_cache_misses": 0,
            "duplicate_tickets_detected": 0,
            "avg_processing_time_ms": 0,
            "classification_accuracy": 0,  # Needs feedback loop
        }
    
    def record_cache_hit(self) -> None:
        self.metrics["llm_cache_hits"] += 1
    
    def record_cache_miss(self) -> None:
        self.metrics["llm_cache_misses"] += 1
    
    def record_duplicate_detected(self) -> None:
        self.metrics["duplicate_tickets_detected"] += 1
    
    def record_processing_time(self, time_ms: float) -> None:
        total = self.metrics["total_tickets_processed"]
        current_avg = self.metrics["avg_processing_time_ms"]
        self.metrics["avg_processing_time_ms"] = (current_avg * total + time_ms) / (total + 1)
        self.metrics["total_tickets_processed"] += 1
    
    def get_cache_hit_rate(self) -> float:
        total = self.metrics["llm_cache_hits"] + self.metrics["llm_cache_misses"]
        return self.metrics["llm_cache_hits"] / total if total > 0 else 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            **self.metrics,
            "cache_hit_rate": self.get_cache_hit_rate(),
        }


# Global instances
ticket_optimizer = TicketOptimizer()
performance_metrics = PerformanceMetrics()
