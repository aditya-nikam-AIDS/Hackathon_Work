import html
import math
import time
from datetime import datetime, timezone
from typing import Any

import altair as alt
import pandas as pd
import requests
import streamlit as st


DEFAULT_API_URL = "http://localhost:8000"
PRIORITIES = ["all", "critical", "high", "medium", "low"]
STATUSES = ["all", "open", "in_progress", "resolved", "closed"]
SORT_OPTIONS = ["SLA urgency", "Priority", "Newest first", "Oldest first"]
PAGE_SIZES = [10, 25, 50, 100]

# ----------------------------------------------------------------------------
# Color tokens — Banking theme with professional colors
# ----------------------------------------------------------------------------
PRIORITY_COLORS = {
    "critical": "#DC2626",
    "high": "#EA580C",
    "medium": "#CA8A04",
    "low": "#059669",
}
STATUS_COLORS = {
    "open": "#2563EB",
    "in_progress": "#7C3AED",
    "resolved": "#059669",
    "closed": "#475569",
}
SLA_COLORS = {
    "breached": "#DC2626",
    "due_soon": "#D97706",
}
SLA_DEFAULT_COLOR = "#059669"

# Banking customer tiers
TIER_COLORS = {
    "vip": "#B45309",
    "premium": "#7C3AED",
    "standard": "#2563EB",
    "trial": "#64748B",
}
TIER_ICONS = {"vip": "VIP", "premium": "PRE", "standard": "STD", "trial": "NEW"}

# Classification source icons
SOURCE_ICONS = {
    "model": "AI",
    "llm": "LLM",
    "tfidf_model": "ML",
    "rule": "RULE",
    "rule_based": "RULE",
    "keyword_fallback": "KW",
    "heuristic": "RULE",
    "manual": "MAN",
    "human": "MAN",
}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Banking category display names
CATEGORY_DISPLAY = {
    "transaction_issue": "Transaction Issue",
    "account_issue": "Account Issue",
    "fraud_security": "Fraud / Security",
    "loan_credit_issue": "Loan / Credit Issue",
    "technical_issue": "Technical Issue",
    "general": "General Inquiry",
}

st.set_page_config(page_title="Banking Support Dashboard", layout="wide", page_icon=":bank:")


# ----------------------------------------------------------------------------
# Styling — Modern glassmorphism with banking theme
# ----------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
    --glass-bg: rgba(255, 255, 255, 0.03);
    --glass-border: rgba(255, 255, 255, 0.08);
    --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
    --accent-primary: #1E40AF;
    --accent-secondary: #7C3AED;
    --accent-tertiary: #059669;
    --glow-primary: rgba(30, 64, 175, 0.4);
    --glow-secondary: rgba(124, 58, 237, 0.3);
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Animated gradient background overlay */
.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: 
        radial-gradient(ellipse 80% 50% at 20% 40%, rgba(30, 64, 175, 0.12), transparent),
        radial-gradient(ellipse 60% 40% at 80% 60%, rgba(124, 58, 237, 0.08), transparent),
        radial-gradient(ellipse 50% 30% at 50% 80%, rgba(5, 150, 105, 0.06), transparent);
    pointer-events: none;
    z-index: 0;
    animation: gradientShift 20s ease-in-out infinite alternate;
}
@keyframes gradientShift {
    0% { opacity: 0.8; transform: scale(1); }
    100% { opacity: 1; transform: scale(1.05); }
}

/* Header banner with banking theme */
.app-header {
    background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 30%, #3730A3 70%, #4C1D95 100%);
    background-size: 300% 300%;
    animation: headerGradient 8s ease infinite;
    padding: 2rem 2.5rem;
    border-radius: 24px;
    margin-bottom: 1.8rem;
    box-shadow: 
        0 20px 60px -15px rgba(30, 64, 175, 0.5),
        0 10px 30px -10px rgba(124, 58, 237, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
    position: relative;
    overflow: hidden;
}
.app-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: linear-gradient(
        to bottom right,
        rgba(255, 255, 255, 0.1) 0%,
        transparent 50%
    );
    animation: shimmer 3s infinite linear;
    pointer-events: none;
}
@keyframes headerGradient {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes shimmer {
    0% { transform: translateX(-100%) rotate(45deg); }
    100% { transform: translateX(100%) rotate(45deg); }
}
.app-header h1 {
    color: #ffffff;
    margin: 0;
    font-size: 2.1rem;
    font-weight: 900;
    letter-spacing: -0.02em;
    text-shadow: 0 2px 20px rgba(0, 0, 0, 0.2);
    font-family: 'Space Grotesk', sans-serif;
}
.app-header p {
    color: rgba(255, 255, 255, 0.92);
    margin: 0.5rem 0 0 0;
    font-size: 0.9rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.live-indicator {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.25);
    padding: 4px 12px;
    border-radius: 20px;
    border: 1px solid rgba(16, 185, 129, 0.4);
}
.live-dot {
    width: 8px;
    height: 8px;
    background: #10B981;
    border-radius: 50%;
    animation: livePulse 2s ease-in-out infinite;
    box-shadow: 0 0 10px #10B981;
}
@keyframes livePulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.3); opacity: 0.7; }
}

/* KPI cards with glassmorphism */
.kpi-card {
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 1.25rem 1.4rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent, #1E40AF), transparent);
    border-radius: 20px 20px 0 0;
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 100px;
    height: 100px;
    background: radial-gradient(circle, var(--accent, rgba(30, 64, 175, 0.15)), transparent 70%);
    transform: translate(30%, -30%);
    pointer-events: none;
}
.kpi-card:hover {
    transform: translateY(-4px) scale(1.02);
    box-shadow: 
        0 20px 40px -15px rgba(0, 0, 0, 0.3),
        0 0 0 1px rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.2);
}
.kpi-icon {
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}
.kpi-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    opacity: 0.6;
    font-weight: 700;
    margin-bottom: 0.4rem;
}
.kpi-value {
    font-size: 2.4rem;
    font-weight: 800;
    font-family: 'Space Grotesk', sans-serif;
    background: linear-gradient(135deg, #ffffff 30%, rgba(255,255,255,0.7));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
}
.kpi-value.danger { background: linear-gradient(135deg, #DC2626, #EA580C); -webkit-background-clip: text; background-clip: text; }
.kpi-value.warning { background: linear-gradient(135deg, #D97706, #CA8A04); -webkit-background-clip: text; background-clip: text; }

/* Enhanced badges */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #ffffff;
    white-space: nowrap;
    box-shadow: 0 2px 8px -2px currentColor;
    transition: all 0.2s ease;
}
.badge:hover {
    transform: scale(1.05);
}
.badge.pulse {
    animation: badgePulse 1.5s ease-in-out infinite;
}
@keyframes badgePulse {
    0%, 100% { 
        box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.6), 0 2px 8px -2px currentColor;
        transform: scale(1);
    }
    50% { 
        box-shadow: 0 0 0 8px rgba(220, 38, 38, 0), 0 2px 8px -2px currentColor;
        transform: scale(1.02);
    }
}

/* Alert cards with glow effect */
.alert-card {
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.01));
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-radius: 16px;
    padding: 1rem 1.3rem;
    margin-bottom: 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-left: 4px solid var(--alert-color, #1E40AF);
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
}
.alert-card::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 60px;
    background: linear-gradient(90deg, var(--alert-color, rgba(30, 64, 175, 0.15)), transparent);
    pointer-events: none;
}
.alert-card:hover {
    transform: translateX(4px);
    box-shadow: 0 8px 24px -8px rgba(0, 0, 0, 0.25);
}
.alert-card.breached {
    animation: alertGlow 2s ease-in-out infinite;
}
@keyframes alertGlow {
    0%, 100% { box-shadow: 0 0 20px -5px rgba(220, 38, 38, 0.3); }
    50% { box-shadow: 0 0 30px -5px rgba(220, 38, 38, 0.5); }
}

/* Ticket cards — premium glass effect */
.ticket-card {
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.01));
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 0.85rem;
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.ticket-card::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: linear-gradient(180deg, var(--accent, #1E40AF), var(--accent-fade, rgba(30, 64, 175, 0.3)));
    border-radius: 4px 0 0 4px;
}
.ticket-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, var(--accent-glow, rgba(30, 64, 175, 0.08)), transparent 40%);
    pointer-events: none;
}
.ticket-card:hover {
    transform: translateY(-2px) translateX(2px);
    box-shadow: 
        0 20px 40px -15px rgba(0, 0, 0, 0.25),
        0 0 0 1px rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.15);
}
.ticket-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    position: relative;
    z-index: 1;
}
.ticket-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    opacity: 0.5;
    margin-left: 0.5rem;
    background: rgba(127, 127, 127, 0.1);
    padding: 2px 8px;
    border-radius: 6px;
}
.ticket-text {
    margin: 0.6rem 0 0.7rem 0;
    font-size: 0.95rem;
    line-height: 1.55;
    position: relative;
    z-index: 1;
    color: rgba(255, 255, 255, 0.9);
}
.sla-bar {
    height: 8px;
    border-radius: 10px;
    background: rgba(127, 127, 127, 0.12);
    overflow: hidden;
    margin: 0.5rem 0 0.6rem 0;
    position: relative;
    z-index: 1;
}
.sla-fill {
    height: 100%;
    border-radius: 10px;
    transition: width 0.4s ease;
    position: relative;
    overflow: hidden;
}
.sla-fill::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    animation: slaShine 2s ease-in-out infinite;
}
@keyframes slaShine {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
.ticket-meta {
    font-size: 0.78rem;
    opacity: 0.75;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.7;
    position: relative;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 0.6rem;
    align-items: center;
}
.meta-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(127, 127, 127, 0.08);
    padding: 3px 10px;
    border-radius: 8px;
    transition: background 0.2s ease;
}
.meta-item:hover {
    background: rgba(127, 127, 127, 0.15);
}

/* Section titles with accent */
.section-title {
    font-size: 1.15rem;
    font-weight: 800;
    margin: 0.5rem 0 1rem 0;
    font-family: 'Space Grotesk', sans-serif;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 2px;
    background: linear-gradient(90deg, rgba(30, 64, 175, 0.4), transparent);
    border-radius: 2px;
    margin-left: 0.5rem;
}

/* Empty state with illustration feel */
.empty-state {
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
    border: 2px dashed rgba(127, 127, 127, 0.25);
    border-radius: 20px;
    padding: 3rem 2rem;
    text-align: center;
    font-size: 1.1rem;
}

/* Sidebar enhancements */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.98));
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}
section[data-testid="stSidebar"] .stMarkdown h3 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    letter-spacing: -0.01em;
    border-bottom: 2px solid rgba(30, 64, 175, 0.3);
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}

/* Form styling */
.stTextArea textarea, .stTextInput input, .stSelectbox > div > div {
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    background: rgba(255, 255, 255, 0.03) !important;
    transition: all 0.2s ease !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: rgba(30, 64, 175, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.15) !important;
}

/* Button enhancements */
.stButton > button {
    background: linear-gradient(135deg, #1E40AF, #3730A3) !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px -3px rgba(30, 64, 175, 0.4) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px -5px rgba(30, 64, 175, 0.5) !important;
}

/* Table styling */
.stDataFrame {
    border-radius: 16px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Selectbox and radio styling */
.stRadio > div {
    background: rgba(255, 255, 255, 0.03);
    padding: 0.5rem;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Chart container styling */
.stAltairChart {
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
    backdrop-filter: blur(10px);
    border-radius: 18px;
    padding: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Divider styling */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(30, 64, 175, 0.3), transparent) !important;
    margin: 1.5rem 0 !important;
}

/* Scrollbar styling */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #1E40AF, #3730A3);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #2563EB, #4F46E5);
}

/* Number input styling */
.stNumberInput > div > div > input {
    border-radius: 10px !important;
}

/* Loading animation override */
.stSpinner > div {
    border-color: #1E40AF transparent transparent transparent !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def esc(value: Any) -> str:
    """HTML-escape any value before it goes into a markdown(unsafe_allow_html) block."""
    if value is None:
        return "—"
    return html.escape(str(value))


def api_get(api_url: str, path: str) -> Any:
    response = requests.get(f"{api_url.rstrip('/')}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(api_url: str, path: str, payload: dict[str, Any]) -> Any:
    response = requests.post(f"{api_url.rstrip('/')}{path}", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def format_duration(seconds: int) -> str:
    prefix = "-" if seconds < 0 else ""
    seconds = abs(int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours >= 24:
        days, hours = divmod(hours, 24)
        return f"{prefix}{days}d {hours}h"
    if hours:
        return f"{prefix}{hours}h {minutes}m"
    return f"{prefix}{minutes}m {secs}s"


def sentiment_badge(score: Any) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return '<span style="opacity:0.5;">— sentiment</span>'
    if value > 0.15:
        color, label = "#059669", "Positive"
    elif value < -0.15:
        color, label = "#DC2626", "Negative"
    else:
        color, label = "#CA8A04", "Neutral"
    return f'<span style="color:{color};">{label} ({value:+.2f})</span>'


def confidence_label(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "—"


def get_category_display(category: str) -> str:
    return CATEGORY_DISPLAY.get(category, category.replace("_", " ").title())


def normalize_tickets(tickets: list[dict[str, Any]]) -> pd.DataFrame:
    if not tickets:
        return pd.DataFrame()
    frame = pd.DataFrame(tickets)
    frame["sla_countdown"] = frame["sla_remaining_seconds"].apply(format_duration)

    created = pd.to_datetime(frame["created_at"])
    deadline = pd.to_datetime(frame["sla_deadline"])
    total_seconds = (deadline - created).dt.total_seconds().clip(lower=1)
    elapsed_seconds = total_seconds - frame["sla_remaining_seconds"]
    frame["sla_progress"] = (elapsed_seconds / total_seconds * 100).clip(lower=0, upper=100)

    frame["created_at"] = created.dt.strftime("%Y-%m-%d %H:%M")
    frame["sla_deadline"] = deadline.dt.strftime("%Y-%m-%d %H:%M")
    return frame


def sort_tickets(frame: pd.DataFrame, sort_key: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    if sort_key == "SLA urgency":
        return frame.sort_values("sla_remaining_seconds")
    if sort_key == "Priority":
        rank = frame["priority"].map(PRIORITY_ORDER).fillna(99)
        return frame.assign(_rank=rank).sort_values(["_rank", "sla_remaining_seconds"]).drop(columns="_rank")
    if sort_key == "Newest first":
        return frame.sort_values("created_at", ascending=False)
    return frame.sort_values("created_at")


def render_ticket_card(row: dict[str, Any]) -> None:
    priority = str(row.get("priority", "unknown")).lower()
    status = str(row.get("status", "unknown")).lower()
    sla_state = str(row.get("sla_state", "")).lower()

    p_color = PRIORITY_COLORS.get(priority, "#64748B")
    s_color = STATUS_COLORS.get(status, "#64748B")
    sla_color = SLA_COLORS.get(sla_state, SLA_DEFAULT_COLOR)
    pulse_class = "pulse" if sla_state == "breached" else ""

    try:
        progress = max(0.0, min(100.0, float(row.get("sla_progress", 0))))
    except (TypeError, ValueError):
        progress = 0.0

    tier = str(row.get("customer_tier", "standard")).lower()
    tier_color = TIER_COLORS.get(tier, "#64748B")
    tier_label = TIER_ICONS.get(tier, "STD")

    source = str(row.get("classification_source", "")).lower()
    source_label = SOURCE_ICONS.get(source, "—")
    
    category = str(row.get("category", "general"))
    category_display = get_category_display(category)

    st.markdown(
        f"""
        <div class="ticket-card" style="--accent:{p_color}; --accent-fade:{p_color}40; --accent-glow:{p_color}15;">
            <div class="ticket-row">
                <div>
                    <span class="badge" style="background:linear-gradient(135deg, {p_color}, {p_color}dd);">{esc(priority)}</span>
                    <span class="badge" style="background:linear-gradient(135deg, {s_color}, {s_color}dd); margin-left:0.3rem;">{esc(status.replace('_', ' '))}</span>
                    <span class="ticket-id">#{esc(row.get('id'))}</span>
                </div>
                <div>
                    <span class="badge {pulse_class}" style="background:linear-gradient(135deg, {sla_color}, {sla_color}cc);">{esc(sla_state.replace('_', ' ')) if sla_state else '—'}</span>
                    <span style="font-family:'JetBrains Mono', monospace; font-size:0.8rem; opacity:0.8; margin-left:0.5rem; background:rgba(127,127,127,0.1); padding:3px 10px; border-radius:8px;">{esc(row.get('sla_countdown'))}</span>
                </div>
            </div>
            <div class="ticket-text">{esc(row.get('complaint_text', ''))}</div>
            <div class="sla-bar"><div class="sla-fill" style="width:{progress:.0f}%; background:linear-gradient(90deg, {sla_color}, {sla_color}cc);"></div></div>
            <div class="ticket-meta">
                <span class="meta-item">{esc(category_display)}</span>
                <span class="meta-item">{esc(row.get('team'))}</span>
                <span class="meta-item" style="color:{tier_color};">[{tier_label}] {esc(tier)}</span>
                <span class="meta-item">{sentiment_badge(row.get('sentiment_score'))}</span>
                <span class="meta-item">[{source_label}] {confidence_label(row.get('classification_confidence'))}</span>
                <span class="meta-item">{esc(row.get('created_at'))} - {esc(row.get('sla_deadline'))}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Banking Support Settings")
    api_url = st.text_input("Backend API URL", value=DEFAULT_API_URL)
    auto_refresh = st.toggle("Auto Refresh", value=True)
    refresh_seconds = st.slider("Refresh Interval", min_value=5, max_value=60, value=15, step=5, format="%ds")
    if auto_refresh:
        st.caption(f"Dashboard refreshes every {refresh_seconds} seconds")

    st.divider()
    
    # Fetch templates and metrics
    try:
        templates_data = api_get(api_url, "/templates")
        templates = templates_data.get("templates", {})
        
        metrics_data = api_get(api_url, "/metrics")
    except:
        templates = {}
        metrics_data = {}
    
    # Quick actions with templates
    st.markdown("### 🎯 Quick Templates")
    template_options = ["Custom"] + list(templates.keys())
    selected_template = st.selectbox(
        "Use Template",
        template_options,
        format_func=lambda x: templates.get(x, {}).get("title", "Custom Entry") if x != "Custom" else "Custom Entry",
        key="template_selector",
    )
    
    st.divider()
    st.markdown("### ✨ Create Banking Ticket")
    
    with st.form("create_ticket_form", clear_on_submit=True):
        # Pre-fill if template selected
        if selected_template != "Custom" and selected_template in templates:
            template_data = templates[selected_template]
            default_text = template_data.get("template", "")
            hint_category = template_data.get("category_hint", "")
            hint_priority = template_data.get("priority_hint", "")
            st.info(f"📋 Template: {template_data['title']}")
            if hint_category or hint_priority:
                st.caption(f"Expected: {hint_category.replace('_', ' ').title()} | {hint_priority.title()} Priority")
        else:
            default_text = ""
        
        complaint_text = st.text_area(
            "Customer Complaint",
            value=default_text,
            height=140,
            placeholder="Describe the banking issue (e.g., UPI failed, unauthorized transaction, loan query)...",
        )
        
        col1, col2 = st.columns(2)
        with col1:
            customer_id = st.text_input("Customer ID", placeholder="e.g., CUST-1001")
        with col2:
            customer_tier = st.selectbox(
                "Tier",
                ["standard", "premium", "vip", "trial"],
                format_func=lambda t: f"[{TIER_ICONS.get(t, 'STD')}] {t.title()}",
            )
        
        # Validation hints
        char_count = len(complaint_text)
        if char_count < 10:
            st.warning("⚠️ Complaint too short (min 10 characters)")
        elif char_count < 20:
            st.info("💡 Add more details for better classification")
        
        submitted = st.form_submit_button("🚀 Submit Ticket", use_container_width=True)

    if submitted:
        if not complaint_text.strip():
            st.error("❌ Please enter a complaint description before submitting.")
        elif len(complaint_text.strip()) < 10:
            st.error("❌ Complaint is too short. Please provide more details.")
        else:
            with st.spinner("Processing ticket... This may take up to 90 seconds for LLM classification."):
                try:
                    created = api_post(
                        api_url,
                        "/create-ticket",
                        {
                            "complaint_text": complaint_text,
                            "customer_id": customer_id or None,
                            "customer_tier": customer_tier,
                            "metadata": {"source": "banking_dashboard", "template_used": selected_template if selected_template != "Custom" else None},
                        },
                    )
                    created_priority = str(created.get("priority", "")).lower()
                    p_color = PRIORITY_COLORS.get(created_priority, "#64748B")
                    
                    # Check for duplicate warning
                    metadata = created.get("metadata", {})
                    dup_warning = metadata.get("duplicate_warning", {})
                    
                    # Calculate confidence percentage
                    confidence_pct = int(created.get('classification_confidence', 0) * 100)
                    
                    success_msg = f"""
                        <div class="alert-card" style="--alert-color:#059669; border-left-color:#059669;">
                            <strong>✅ Ticket Created Successfully!</strong><br>
                            <span style="font-family:'JetBrains Mono', monospace; font-size:0.85rem;">
                                ID: <strong>{esc(created.get('id'))}</strong> | 
                                Priority: <span class="badge" style="background:{p_color}; font-size:0.65rem;">{esc(created_priority)}</span> | 
                                Team: <strong>{esc(created.get('team'))}</strong><br>
                                Category: <strong>{esc(get_category_display(created.get('category', '')))}</strong> | 
                                Confidence: <strong>{confidence_pct}%</strong>
                            </span>
                        </div>
                    """
                    
                    if dup_warning.get("similarity_detected"):
                        similar_ids = dup_warning.get("similar_ticket_ids", [])
                        success_msg += f"""
                        <div class="alert-card" style="--alert-color:#D97706; border-left-color:#D97706; margin-top:0.5rem;">
                            <strong>⚠️ Similar Tickets Detected</strong><br>
                            <span style="font-size:0.8rem;">Found {len(similar_ids)} similar recent ticket(s). Check for duplicates: {', '.join(similar_ids[:2])}</span>
                        </div>
                        """
                    
                    st.markdown(success_msg, unsafe_allow_html=True)
                    
                except requests.Timeout:
                    st.error("⏱️ Request timed out. The LLM may be slow to respond. Please try again or check if Ollama is running.")
                except requests.RequestException as exc:
                    st.error(f"❌ Failed to create ticket: {exc}")
    
    # Performance metrics display
    if metrics_data:
        st.divider()
        st.markdown("### 📊 System Metrics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Processed", metrics_data.get("total_tickets_processed", 0))
            st.metric("Avg Time (ms)", f"{metrics_data.get('avg_processing_time_ms', 0):.0f}")
        with col2:
            cache_hit_rate = metrics_data.get("cache_hit_rate", 0) * 100
            st.metric("Cache Hit Rate", f"{cache_hit_rate:.0f}%")
            st.metric("Duplicates", metrics_data.get("duplicate_tickets_detected", 0))


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="app-header">
        <h1>Banking Customer Support Dashboard</h1>
        <p>
            <span class="live-indicator"><span class="live-dot"></span>LIVE</span>
            Real-time SLA Monitoring | Last Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    dashboard = api_get(api_url, "/dashboard")
except requests.RequestException as exc:
    st.markdown(
        f"""
        <div class="alert-card" style="--alert-color:#DC2626; border-left-color:#DC2626;">
            <strong>Backend Unavailable</strong> — Could not reach <code>{esc(api_url)}</code><br>
            <span style="opacity:0.75;">{esc(exc)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ----------------------------------------------------------------------------
# KPI cards
# ----------------------------------------------------------------------------
kpi_items = [
    ("Total Tickets", dashboard["total_tickets"], "TOTAL", "#1E40AF", ""),
    ("Open Cases", dashboard["open_tickets"], "OPEN", "#2563EB", ""),
    ("SLA Breached", dashboard["breached_tickets"], "BREACH", "#DC2626", "danger"),
    ("Due Soon", dashboard["due_soon_tickets"], "URGENT", "#D97706", "warning"),
    ("Escalated", dashboard["escalated_tickets"], "ESC", "#7C3AED", ""),
]
kpi_cols = st.columns(5)
for col, (label, value, icon, color, value_class) in zip(kpi_cols, kpi_items):
    col.markdown(
        f"""
        <div class="kpi-card" style="--accent:{color};">
            <div class="kpi-icon">[{icon}]</div>
            <div class="kpi-label">{esc(label)}</div>
            <div class="kpi-value {value_class}">{esc(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")


# ----------------------------------------------------------------------------
# Escalation alerts
# ----------------------------------------------------------------------------
if dashboard["alerts"]:
    st.markdown('<div class="section-title">Escalation Alerts</div>', unsafe_allow_html=True)
    for alert in dashboard["alerts"][:5]:
        sla_state = alert["sla_state"]
        is_breached = sla_state == "breached"
        border_color = SLA_COLORS.get(sla_state, SLA_DEFAULT_COLOR)
        priority_color = PRIORITY_COLORS.get(alert["priority"], "#64748B")
        icon = "[BREACH]" if is_breached else "[URGENT]"
        time_label = (
            f"Breached by {format_duration(alert['sla_remaining_seconds'])}"
            if is_breached
            else f"Due in {format_duration(alert['sla_remaining_seconds'])}"
        )
        pulse_class = "pulse" if is_breached else ""
        breached_class = "breached" if is_breached else ""
        st.markdown(
            f"""
            <div class="alert-card {breached_class}" style="--alert-color:{border_color};">
                <span class="badge {pulse_class}" style="background:{priority_color};">{esc(alert['priority'])}</span>
                <strong style="margin-left:0.5rem;">{esc(alert['team'])}</strong>
                <span style="opacity:0.8; margin-left:0.5rem; font-family:'JetBrains Mono', monospace; font-size:0.82rem;">{icon} {time_label}</span>
                <div class="ticket-text" style="margin-top:0.5rem;">{esc(alert['complaint_text'][:140])}...</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.write("")


# ----------------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.markdown('<div class="section-title">Priority Distribution</div>', unsafe_allow_html=True)
    priority_counts = dashboard["by_priority"]
    if priority_counts:
        df_priority = pd.DataFrame(
            {"priority": list(priority_counts.keys()), "count": list(priority_counts.values())}
        )
        domain = list(PRIORITY_COLORS.keys())
        range_ = list(PRIORITY_COLORS.values())
        chart = (
            alt.Chart(df_priority)
            .mark_arc(innerRadius=70, outerRadius=120, cornerRadius=6, padAngle=0.03)
            .encode(
                theta=alt.Theta("count:Q", stack=True),
                color=alt.Color(
                    "priority:N",
                    scale=alt.Scale(domain=domain, range=range_),
                    legend=alt.Legend(title="Priority", orient="bottom", titleFontSize=12, labelFontSize=11),
                ),
                order=alt.Order("count:Q", sort="descending"),
                tooltip=[
                    alt.Tooltip("priority:N", title="Priority"),
                    alt.Tooltip("count:Q", title="Tickets"),
                ],
            )
            .properties(height=320)
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.markdown('<div class="empty-state">No tickets yet.</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">Team Workload</div>', unsafe_allow_html=True)
    team_counts = dashboard["by_team"]
    if team_counts:
        df_team = pd.DataFrame({"team": list(team_counts.keys()), "count": list(team_counts.values())})
        chart = (
            alt.Chart(df_team)
            .mark_bar(cornerRadius=8)
            .encode(
                x=alt.X("count:Q", title="Tickets", axis=alt.Axis(grid=False)),
                y=alt.Y("team:N", sort="-x", title=None, axis=alt.Axis(labelFontSize=12)),
                color=alt.Color("count:Q", scale=alt.Scale(scheme="blues"), legend=None),
                tooltip=[
                    alt.Tooltip("team:N", title="Team"),
                    alt.Tooltip("count:Q", title="Tickets"),
                ],
            )
            .properties(height=320)
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.markdown('<div class="empty-state">No routing data yet.</div>', unsafe_allow_html=True)

st.write("")


# ----------------------------------------------------------------------------
# Ticket queue
# ----------------------------------------------------------------------------
st.markdown('<div class="section-title">Banking Ticket Queue</div>', unsafe_allow_html=True)

filter_cols = st.columns(4)
priority_filter = filter_cols[0].selectbox("Priority", PRIORITIES)
status_filter = filter_cols[1].selectbox("Status", STATUSES)
team_options = ["all"] + sorted(dashboard["by_team"].keys())
team_filter = filter_cols[2].selectbox("Team", team_options)
category_options = ["all"] + sorted(dashboard["by_category"].keys())
category_filter = filter_cols[3].selectbox("Category", category_options, format_func=lambda c: get_category_display(c) if c != "all" else "All Categories")

control_cols = st.columns([2, 2, 2])
sort_key = control_cols[0].selectbox("Sort by", SORT_OPTIONS)
view_mode = control_cols[1].radio("View", ["Cards", "Table"], horizontal=True)
page_size = control_cols[2].selectbox("Per page", PAGE_SIZES, index=1)

tickets = dashboard["tickets"]
if priority_filter != "all":
    tickets = [ticket for ticket in tickets if ticket["priority"] == priority_filter]
if status_filter != "all":
    tickets = [ticket for ticket in tickets if ticket["status"] == status_filter]
if team_filter != "all":
    tickets = [ticket for ticket in tickets if ticket["team"] == team_filter]
if category_filter != "all":
    tickets = [ticket for ticket in tickets if ticket["category"] == category_filter]

frame = normalize_tickets(tickets)
frame = sort_tickets(frame, sort_key)

if frame.empty:
    st.markdown(
        """
        <div class="empty-state">
            No tickets match your current filters<br>
            <span style="opacity:0.6; font-size:0.9rem;">Try adjusting your search criteria above</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    total = len(frame)
    total_pages = max(1, math.ceil(total / page_size))
    page_col, info_col = st.columns([1, 5])
    page = page_col.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1, label_visibility="collapsed")
    info_col.markdown(
        f"""<div style='padding-top:0.5rem; opacity:0.8; font-family:JetBrains Mono, monospace; font-size:0.85rem;
            background: rgba(127,127,127,0.08); padding: 0.6rem 1rem; border-radius: 10px; display: inline-block;'>
            Showing <strong>{min((page - 1) * page_size + 1, total)}–{min(page * page_size, total)}</strong> of <strong>{total}</strong> tickets
            | Page <strong>{page}</strong> of <strong>{total_pages}</strong>
        </div>""",
        unsafe_allow_html=True,
    )

    start = (page - 1) * page_size
    end = start + page_size
    page_frame = frame.iloc[start:end]

    if view_mode == "Cards":
        for row in page_frame.to_dict("records"):
            render_ticket_card(row)
    else:
        st.dataframe(
            page_frame[
                [
                    "id",
                    "priority",
                    "status",
                    "sla_state",
                    "sla_countdown",
                    "sla_progress",
                    "team",
                    "category",
                    "customer_tier",
                    "sentiment_score",
                    "classification_source",
                    "classification_confidence",
                    "created_at",
                    "sla_deadline",
                    "complaint_text",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "sla_progress": st.column_config.ProgressColumn(
                    "SLA used", min_value=0, max_value=100, format="%.0f%%"
                ),
                "sla_countdown": st.column_config.TextColumn("SLA countdown"),
                "complaint_text": st.column_config.TextColumn("Complaint", width="large"),
            },
        )


# ----------------------------------------------------------------------------
# Auto refresh
# ----------------------------------------------------------------------------
if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
