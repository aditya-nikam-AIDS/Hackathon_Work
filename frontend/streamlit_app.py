import html
import math
import os
import time
from datetime import datetime, timezone
from typing import Any

import altair as alt
import pandas as pd
import requests
import streamlit as st


DEFAULT_API_URL = os.getenv("DASHBOARD_API_URL", "http://localhost:8000")
PRIORITIES = ["all", "critical", "high", "medium", "low"]
STATUSES = ["all", "open", "in_progress", "resolved", "closed"]
SORT_OPTIONS = ["SLA urgency", "Priority", "Newest first", "Oldest first"]
PAGE_SIZES = [10, 25, 50, 100]

# ----------------------------------------------------------------------------
# Color tokens — kept in one place so badges, charts, and cards stay in sync
# ----------------------------------------------------------------------------
PRIORITY_COLORS = {
    "critical": "#EF4444",
    "high": "#F97316",
    "medium": "#EAB308",
    "low": "#10B981",
}
STATUS_COLORS = {
    "open": "#3B82F6",
    "in_progress": "#8B5CF6",
    "resolved": "#10B981",
    "closed": "#64748B",
}
SLA_COLORS = {
    "breached": "#EF4444",
    "due_soon": "#F59E0B",
}
SLA_DEFAULT_COLOR = "#10B981"
TIER_COLORS = {
    "vip": "#F59E0B",
    "premium": "#8B5CF6",
    "standard": "#3B82F6",
    "trial": "#64748B",
}
TIER_ICONS = {"vip": "👑", "premium": "💎", "standard": "👤", "trial": "🧪"}
SOURCE_ICONS = {
    "model": "🤖",
    "llm": "🤖",
    "rule": "📐",
    "rule_based": "📐",
    "heuristic": "📐",
    "manual": "🧑‍💻",
    "human": "🧑‍💻",
}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

st.set_page_config(page_title="Complaint Routing Dashboard", layout="wide", page_icon="📨")


# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Header banner */
.app-header {
    background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 55%, #DB2777 100%);
    padding: 1.6rem 2rem;
    border-radius: 18px;
    margin-bottom: 1.4rem;
    box-shadow: 0 10px 30px -10px rgba(124, 58, 237, 0.5);
}
.app-header h1 {
    color: #ffffff;
    margin: 0;
    font-size: 1.85rem;
    font-weight: 800;
    letter-spacing: -0.01em;
}
.app-header p {
    color: rgba(255,255,255,0.88);
    margin: 0.3rem 0 0 0;
    font-size: 0.85rem;
    font-family: 'JetBrains Mono', monospace;
}

/* KPI cards */
.kpi-card {
    background: rgba(127,127,127,0.07);
    border: 1px solid rgba(127,127,127,0.16);
    border-left: 4px solid var(--accent, #7C3AED);
    border-radius: 14px;
    padding: 0.95rem 1.1rem;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px -8px rgba(0,0,0,0.35);
}
.kpi-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.65;
    font-weight: 700;
    margin-bottom: 0.3rem;
}
.kpi-value {
    font-size: 1.9rem;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #ffffff;
    white-space: nowrap;
}
.badge.pulse {
    animation: pulse 1.6s infinite;
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.55); }
    50% { box-shadow: 0 0 0 6px rgba(239,68,68,0); }
}

/* Alert cards */
.alert-card {
    border-radius: 12px;
    padding: 0.8rem 1.1rem;
    margin-bottom: 0.55rem;
    border-left: 5px solid;
    background: rgba(127,127,127,0.06);
}

/* Ticket cards */
.ticket-card {
    border: 1px solid rgba(127,127,127,0.16);
    border-left: 5px solid var(--accent, #7C3AED);
    border-radius: 12px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.6rem;
    background: rgba(127,127,127,0.045);
    transition: box-shadow 0.15s ease;
}
.ticket-card:hover {
    box-shadow: 0 6px 18px -10px rgba(0,0,0,0.35);
}
.ticket-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
}
.ticket-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    opacity: 0.55;
    margin-left: 0.4rem;
}
.ticket-text {
    margin: 0.45rem 0 0.55rem 0;
    font-size: 0.93rem;
    line-height: 1.45;
}
.sla-bar {
    height: 6px;
    border-radius: 4px;
    background: rgba(127,127,127,0.18);
    overflow: hidden;
    margin: 0.35rem 0 0.5rem 0;
}
.sla-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}
.ticket-meta {
    font-size: 0.78rem;
    opacity: 0.7;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.6;
}

/* Section titles */
.section-title {
    font-size: 1.05rem;
    font-weight: 800;
    margin: 0.3rem 0 0.7rem 0;
}

/* Empty state */
.empty-state {
    border: 1px dashed rgba(127,127,127,0.35);
    border-radius: 14px;
    padding: 1.6rem;
    text-align: center;
    opacity: 0.8;
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
    response = requests.post(f"{api_url.rstrip('/')}{path}", json=payload, timeout=20)
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
        color, icon = "#10B981", "🙂"
    elif value < -0.15:
        color, icon = "#EF4444", "🙁"
    else:
        color, icon = "#EAB308", "😐"
    return f'<span style="color:{color};">{icon} sentiment {value:+.2f}</span>'


def confidence_label(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "—"


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
    tier_icon = TIER_ICONS.get(tier, "👤")

    source = str(row.get("classification_source", "")).lower()
    source_icon = SOURCE_ICONS.get(source, "🔎")

    st.markdown(
        f"""
        <div class="ticket-card" style="--accent:{p_color};">
            <div class="ticket-row">
                <div>
                    <span class="badge" style="background:{p_color};">{esc(priority)}</span>
                    <span class="badge" style="background:{s_color}; margin-left:0.3rem;">{esc(status.replace('_', ' '))}</span>
                    <span class="ticket-id">#{esc(row.get('id'))}</span>
                </div>
                <div>
                    <span class="badge {pulse_class}" style="background:{sla_color};">{esc(sla_state.replace('_', ' ')) if sla_state else '—'}</span>
                    <span style="font-family:'JetBrains Mono', monospace; font-size:0.8rem; opacity:0.75; margin-left:0.4rem;">{esc(row.get('sla_countdown'))}</span>
                </div>
            </div>
            <div class="ticket-text">{esc(row.get('complaint_text', ''))}</div>
            <div class="sla-bar"><div class="sla-fill" style="width:{progress:.0f}%; background:{sla_color};"></div></div>
            <div class="ticket-meta">
                🏷️ {esc(row.get('category'))} &nbsp;·&nbsp;
                🧭 {esc(row.get('team'))} &nbsp;·&nbsp;
                <span style="color:{tier_color};">{tier_icon} {esc(tier)}</span> &nbsp;·&nbsp;
                {sentiment_badge(row.get('sentiment_score'))} &nbsp;·&nbsp;
                {source_icon} {esc(source) if source else '—'} ({confidence_label(row.get('classification_confidence'))}) &nbsp;·&nbsp;
                🗓️ {esc(row.get('created_at'))} → ⏰ {esc(row.get('sla_deadline'))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Control Panel")
    api_url = st.text_input("Backend API URL", value=DEFAULT_API_URL)
    auto_refresh = st.toggle("🔄 Auto refresh", value=True)
    refresh_seconds = st.slider("Refresh interval (s)", min_value=5, max_value=60, value=15, step=5)
    if auto_refresh:
        st.caption(f"⏱️ Refreshing every {refresh_seconds}s")

    st.divider()
    st.markdown("### 📝 Create Ticket")
    with st.form("create_ticket_form", clear_on_submit=True):
        complaint_text = st.text_area("Complaint text", height=140, placeholder="Customer says...")
        customer_id = st.text_input("Customer ID", placeholder="CUST-1001")
        customer_tier = st.selectbox(
            "Customer tier",
            ["standard", "premium", "vip", "trial"],
            format_func=lambda t: f"{TIER_ICONS.get(t, '')} {t.title()}",
        )
        submitted = st.form_submit_button("🚀 Create ticket", use_container_width=True)

    if submitted:
        if not complaint_text.strip():
            st.warning("⚠️ Please enter complaint text before submitting.")
        else:
            try:
                created = api_post(
                    api_url,
                    "/create-ticket",
                    {
                        "complaint_text": complaint_text,
                        "customer_id": customer_id or None,
                        "customer_tier": customer_tier,
                        "metadata": {"source": "streamlit_dashboard"},
                    },
                )
                created_priority = str(created.get("priority", "")).lower()
                p_color = PRIORITY_COLORS.get(created_priority, "#64748B")
                st.markdown(
                    f"""
                    <div class="alert-card" style="border-color:{p_color};">
                        ✅ Created <strong>{esc(created.get('id'))}</strong> as
                        <span class="badge" style="background:{p_color};">{esc(created_priority)}</span>
                        → routed to <strong>{esc(created.get('team'))}</strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            except requests.RequestException as exc:
                st.error(f"❌ Could not create ticket: {exc}")


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="app-header">
        <h1>📨 Customer Complaint Classification &amp; Routing Engine</h1>
        <p>🟢 Live SLA monitoring · Last refreshed {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    dashboard = api_get(api_url, "/dashboard")
except requests.RequestException as exc:
    st.markdown(
        f"""
        <div class="alert-card" style="border-color:#EF4444;">
            🔌 <strong>Backend unavailable</strong> — could not reach <code>{esc(api_url)}</code><br>
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
    ("Total Tickets", dashboard["total_tickets"], "📊", "#6366F1"),
    ("Open", dashboard["open_tickets"], "📂", "#3B82F6"),
    ("SLA Breached", dashboard["breached_tickets"], "🔥", "#EF4444"),
    ("Due Soon", dashboard["due_soon_tickets"], "⏳", "#F59E0B"),
    ("Escalated", dashboard["escalated_tickets"], "🚨", "#8B5CF6"),
]
kpi_cols = st.columns(5)
for col, (label, value, icon, color) in zip(kpi_cols, kpi_items):
    col.markdown(
        f"""
        <div class="kpi-card" style="--accent:{color};">
            <div class="kpi-label">{icon} {esc(label)}</div>
            <div class="kpi-value">{esc(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")


# ----------------------------------------------------------------------------
# Escalation alerts
# ----------------------------------------------------------------------------
if dashboard["alerts"]:
    st.markdown('<div class="section-title">🔔 Escalation Alerts</div>', unsafe_allow_html=True)
    for alert in dashboard["alerts"][:5]:
        sla_state = alert["sla_state"]
        is_breached = sla_state == "breached"
        border_color = SLA_COLORS.get(sla_state, SLA_DEFAULT_COLOR)
        priority_color = PRIORITY_COLORS.get(alert["priority"], "#64748B")
        icon = "🔥" if is_breached else "⏳"
        time_label = (
            f"Breached by {format_duration(alert['sla_remaining_seconds'])}"
            if is_breached
            else f"Due in {format_duration(alert['sla_remaining_seconds'])}"
        )
        pulse_class = "pulse" if is_breached else ""
        st.markdown(
            f"""
            <div class="alert-card" style="border-color:{border_color};">
                <span class="badge {pulse_class}" style="background:{priority_color};">{esc(alert['priority'])}</span>
                <strong style="margin-left:0.4rem;">{esc(alert['team'])}</strong>
                <span style="opacity:0.75; margin-left:0.4rem; font-family:'JetBrains Mono', monospace; font-size:0.82rem;">{icon} {time_label}</span>
                <div class="ticket-text">{esc(alert['complaint_text'][:140])}</div>
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
    st.markdown('<div class="section-title">🎯 Tickets by Priority</div>', unsafe_allow_html=True)
    priority_counts = dashboard["by_priority"]
    if priority_counts:
        df_priority = pd.DataFrame(
            {"priority": list(priority_counts.keys()), "count": list(priority_counts.values())}
        )
        domain = list(PRIORITY_COLORS.keys())
        range_ = list(PRIORITY_COLORS.values())
        chart = (
            alt.Chart(df_priority)
            .mark_arc(innerRadius=60, outerRadius=110, cornerRadius=4, padAngle=0.02)
            .encode(
                theta=alt.Theta("count:Q", stack=True),
                color=alt.Color(
                    "priority:N",
                    scale=alt.Scale(domain=domain, range=range_),
                    legend=alt.Legend(title="Priority", orient="bottom"),
                ),
                order=alt.Order("count:Q", sort="descending"),
                tooltip=[
                    alt.Tooltip("priority:N", title="Priority"),
                    alt.Tooltip("count:Q", title="Tickets"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.markdown('<div class="empty-state">No tickets yet.</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">🧭 Tickets by Team</div>', unsafe_allow_html=True)
    team_counts = dashboard["by_team"]
    if team_counts:
        df_team = pd.DataFrame({"team": list(team_counts.keys()), "count": list(team_counts.values())})
        chart = (
            alt.Chart(df_team)
            .mark_bar(cornerRadius=6)
            .encode(
                x=alt.X("count:Q", title="Tickets"),
                y=alt.Y("team:N", sort="-x", title=None),
                color=alt.Color("count:Q", scale=alt.Scale(scheme="purplered"), legend=None),
                tooltip=[
                    alt.Tooltip("team:N", title="Team"),
                    alt.Tooltip("count:Q", title="Tickets"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.markdown('<div class="empty-state">No routing data yet.</div>', unsafe_allow_html=True)

st.write("")


# ----------------------------------------------------------------------------
# Ticket queue
# ----------------------------------------------------------------------------
st.markdown('<div class="section-title">🗂️ Ticket Queue</div>', unsafe_allow_html=True)

filter_cols = st.columns(4)
priority_filter = filter_cols[0].selectbox("Priority", PRIORITIES)
status_filter = filter_cols[1].selectbox("Status", STATUSES)
team_options = ["all"] + sorted(dashboard["by_team"].keys())
team_filter = filter_cols[2].selectbox("Team", team_options)
category_options = ["all"] + sorted(dashboard["by_category"].keys())
category_filter = filter_cols[3].selectbox("Category", category_options)

control_cols = st.columns([2, 2, 2])
sort_key = control_cols[0].selectbox("Sort by", SORT_OPTIONS)
view_mode = control_cols[1].radio("View", ["🗂️ Cards", "📋 Table"], horizontal=True)
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
            🕊️ No tickets match these filters.<br>
            <span style="opacity:0.7; font-size:0.85rem;">Try widening your search or clearing a filter above.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    total = len(frame)
    total_pages = max(1, math.ceil(total / page_size))
    page_col, info_col = st.columns([1, 5])
    page = page_col.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
    info_col.markdown(
        f"<div style='padding-top:1.7rem; opacity:0.7; font-family:JetBrains Mono, monospace; font-size:0.85rem;'>"
        f"Showing {min((page - 1) * page_size + 1, total)}–{min(page * page_size, total)} of {total} tickets"
        f"</div>",
        unsafe_allow_html=True,
    )

    start = (page - 1) * page_size
    end = start + page_size
    page_frame = frame.iloc[start:end]

    if view_mode.endswith("Cards"):
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

