import os
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests
import streamlit as st


DEFAULT_API_URL = os.getenv("DASHBOARD_API_URL", "http://localhost:8000")
PRIORITIES = ["all", "critical", "high", "medium", "low"]
STATUSES = ["all", "open", "in_progress", "resolved", "closed"]


st.set_page_config(page_title="Complaint Routing Dashboard", layout="wide")


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


def normalize_tickets(tickets: list[dict[str, Any]]) -> pd.DataFrame:
    if not tickets:
        return pd.DataFrame()
    frame = pd.DataFrame(tickets)
    frame["sla_countdown"] = frame["sla_remaining_seconds"].apply(format_duration)
    frame["created_at"] = pd.to_datetime(frame["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    frame["sla_deadline"] = pd.to_datetime(frame["sla_deadline"]).dt.strftime("%Y-%m-%d %H:%M")
    return frame


with st.sidebar:
    st.title("Control Panel")
    api_url = st.text_input("Backend API URL", value=DEFAULT_API_URL)
    auto_refresh = st.toggle("Auto refresh", value=True)
    refresh_seconds = st.slider("Refresh interval", min_value=5, max_value=60, value=15, step=5)

    st.divider()
    st.subheader("Create Ticket")
    with st.form("create_ticket_form", clear_on_submit=True):
        complaint_text = st.text_area("Complaint text", height=140, placeholder="Customer says...")
        customer_id = st.text_input("Customer ID", placeholder="CUST-1001")
        customer_tier = st.selectbox("Customer tier", ["standard", "premium", "vip", "trial"])
        submitted = st.form_submit_button("Create ticket", use_container_width=True)

    if submitted:
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
            st.success(f"Created {created['id']} as {created['priority']} for {created['team']}.")
        except requests.RequestException as exc:
            st.error(f"Could not create ticket: {exc}")

st.title("Customer Complaint Classification & Routing Engine")
st.caption(f"Last refreshed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

try:
    dashboard = api_get(api_url, "/dashboard")
except requests.RequestException as exc:
    st.error(f"Backend unavailable: {exc}")
    st.stop()

metrics = st.columns(5)
metrics[0].metric("Total", dashboard["total_tickets"])
metrics[1].metric("Open", dashboard["open_tickets"])
metrics[2].metric("Breached SLA", dashboard["breached_tickets"])
metrics[3].metric("Due Soon", dashboard["due_soon_tickets"])
metrics[4].metric("Escalated", dashboard["escalated_tickets"])

if dashboard["alerts"]:
    st.subheader("Escalation Alerts")
    for alert in dashboard["alerts"][:5]:
        if alert["sla_state"] == "breached":
            st.error(
                f"{alert['priority'].upper()} | {alert['team']} | "
                f"SLA breached by {format_duration(alert['sla_remaining_seconds'])} | "
                f"{alert['complaint_text'][:140]}"
            )
        else:
            st.warning(
                f"{alert['priority'].upper()} | {alert['team']} | "
                f"Due in {format_duration(alert['sla_remaining_seconds'])} | "
                f"{alert['complaint_text'][:140]}"
            )

left, right = st.columns(2)
with left:
    st.subheader("Tickets by Priority")
    priority_counts = pd.Series(dashboard["by_priority"], dtype="int64")
    if not priority_counts.empty:
        st.bar_chart(priority_counts)
    else:
        st.info("No tickets yet.")

with right:
    st.subheader("Tickets by Team")
    team_counts = pd.Series(dashboard["by_team"], dtype="int64")
    if not team_counts.empty:
        st.bar_chart(team_counts)
    else:
        st.info("No routing data yet.")

st.subheader("Ticket Queue")
filter_cols = st.columns(4)
priority_filter = filter_cols[0].selectbox("Priority", PRIORITIES)
status_filter = filter_cols[1].selectbox("Status", STATUSES)
team_options = ["all"] + sorted(dashboard["by_team"].keys())
team_filter = filter_cols[2].selectbox("Team", team_options)
category_options = ["all"] + sorted(dashboard["by_category"].keys())
category_filter = filter_cols[3].selectbox("Category", category_options)

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
if frame.empty:
    st.info("No tickets match the current filters.")
else:
    st.dataframe(
        frame[
            [
                "id",
                "priority",
                "sla_state",
                "sla_countdown",
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
    )

if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()

