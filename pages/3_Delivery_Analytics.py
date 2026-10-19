"""
Page 3: Delivery Logistics & Fulfillment Analytics
Lead times, SLA compliance, delay severity distributions, and seller benchmarks.
Clean executive styling with zero emoji clutter and non-overlapping layouts.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from src.dashboard.ui_components import (
    render_header,
    load_filter_options,
    get_plotly_layout,
    PALETTE,
)
from src.analytics.delivery_analysis import (
    get_delivery_summary_metrics,
    get_delivery_delay_distribution,
    get_state_delivery_performance,
    get_monthly_delivery_trends,
    get_seller_delivery_rankings,
)

st.set_page_config(page_title="Delivery Analytics | E-Commerce BI", layout="wide")

render_header(
    title="Logistics & Delivery Performance Analytics",
    subtitle="Order-to-door transit lead times, SLA compliance, delay severity distributions, and seller benchmarks.",
)

# Sidebar Filters
states, _ = load_filter_options()
with st.sidebar:
    st.markdown("### Logistics Filters")
    selected_state = st.selectbox("Destination State", states, index=0)
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("Start Date", value=pd.to_datetime("2016-09-01"), key="del_start_p3")
    with col_d2:
        end_date = st.date_input("End Date", value=pd.to_datetime("2018-10-18"), key="del_end_p3")

filter_state_param = None if selected_state == "All States" else selected_state

# Metrics
del_metrics = get_delivery_summary_metrics(
    start_date=str(start_date),
    end_date=str(end_date),
    customer_state=filter_state_param,
)

# Clean Native Streamlit Metric Cards (Zero Overlap, 4 Columns)
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="On-Time Delivery Rate",
        value=f"{del_metrics['on_time_rate_pct']:.1f}%",
        delta=f"{del_metrics['on_time_orders']:,} On-Time Orders",
        help="Orders delivered on or before estimated delivery SLA date.",
    )

with c2:
    st.metric(
        label="Late Delivery Rate",
        value=f"{del_metrics['late_delivery_rate_pct']:.1f}%",
        delta=f"{del_metrics['delayed_orders']:,} Delayed Orders",
        delta_color="inverse",
        help="Orders delivered strictly after estimated delivery date.",
    )

with c3:
    st.metric(
        label="Average Total Transit",
        value=f"{del_metrics['avg_delivery_duration_days']:.1f} Days",
        delta="Purchase to Doorstep",
        delta_color="off",
        help="Average elapsed calendar days between order purchase and customer receipt.",
    )

with c4:
    st.metric(
        label="Carrier In-Transit Duration",
        value=f"{del_metrics['avg_carrier_transit_days']:.1f} Days",
        delta="Dispatch to Doorstep",
        delta_color="off",
        help="Average calendar days between carrier handoff and customer receipt.",
    )

st.markdown("<br>", unsafe_allow_html=True)

# Lead-Time Decomposition & Delay Distribution
col_decomp, col_hist = st.columns([1.1, 1.3])

with col_decomp:
    stages = ["Approval", "Dispatch to Carrier", "Carrier to Door", "Total Lead Time"]
    durations = [
        del_metrics["avg_approval_hours"] / 24.0,
        max(0.1, del_metrics["avg_delivery_duration_days"] - del_metrics["avg_carrier_transit_days"] - (del_metrics["avg_approval_hours"] / 24.0)),
        del_metrics["avg_carrier_transit_days"],
        del_metrics["avg_delivery_duration_days"],
    ]
    
    fig_lead = go.Figure(go.Bar(
        x=stages,
        y=[round(d, 2) for d in durations],
        marker_color=[PALETTE["secondary"], PALETTE["warning"], PALETTE["accent"], PALETTE["primary"]],
        text=[f"{d:.1f} d" for d in durations],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Duration: %{y:.2f} Days<extra></extra>",
    ))
    fig_lead.update_layout(get_plotly_layout(
        height=340,
        title="Average Lead-Time Decomposition (Days)"
    ))
    st.plotly_chart(fig_lead, use_container_width=True)

with col_hist:
    dist_df = get_delivery_delay_distribution()
    
    fig_dist = px.histogram(
        dist_df,
        x="delivery_delay_days",
        color="is_delivered_on_time",
        nbins=60,
        color_discrete_map={1: PALETTE["success"], 0: PALETTE["danger"]},
        labels={"delivery_delay_days": "Days Early (-) or Days Late (+)", "is_delivered_on_time": "Delivery Status"},
    )
    fig_dist.add_vline(x=0, line_width=2, line_dash="dash", line_color="#0F172A", annotation_text="SLA Delivery Estimate")
    fig_dist.update_layout(get_plotly_layout(
        height=340,
        title="Delivery Delay Distribution Relative to Estimated SLA"
    ))
    fig_dist.for_each_trace(lambda t: t.update(name="On-Time / Early" if t.name == "1" else "Delayed (Late)"))
    st.plotly_chart(fig_dist, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# State-Level Delivery Latency
st.markdown('<div class="section-title">State-Level Logistics Latency & SLA Compliance</div>', unsafe_allow_html=True)
state_del_df = get_state_delivery_performance()

col_state_plot, col_state_table = st.columns([1.4, 1.0])

with col_state_plot:
    fig_state_del = px.bar(
        state_del_df.sort_values("avg_delivery_days", ascending=False),
        x="customer_state",
        y="avg_delivery_days",
        color="on_time_rate_pct",
        color_continuous_scale="RdYlGn",
        labels={"customer_state": "State", "avg_delivery_days": "Avg Delivery (Days)", "on_time_rate_pct": "On-Time %"},
    )
    fig_state_del.update_layout(get_plotly_layout(
        height=340,
        title="Average Delivery Duration (Days) & On-Time Rate % by State"
    ))
    fig_state_del.update_traces(hovertemplate="<b>%{x}</b><br>Avg Delivery: %{y:.1f} Days<br>On-Time: %{marker.color:.1f}%<extra></extra>")
    st.plotly_chart(fig_state_del, use_container_width=True)

with col_state_table:
    st.markdown("**Longest Transit States vs Shortest:**")
    top_and_bottom = pd.concat([state_del_df.head(4), state_del_df.tail(4)])
    st.dataframe(
        top_and_bottom[[
            "customer_state", "delivered_orders", "avg_delivery_days", "avg_delay_days", "on_time_rate_pct"
        ]].rename(columns={
            "customer_state": "State",
            "delivered_orders": "Orders",
            "avg_delivery_days": "Avg Days",
            "avg_delay_days": "Avg Delay",
            "on_time_rate_pct": "On-Time %",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# Monthly Delivery Timeliness Trends
st.markdown('<div class="section-title">Monthly Delivery Timeliness Trajectory</div>', unsafe_allow_html=True)
monthly_del = get_monthly_delivery_trends()

fig_monthly_del = go.Figure()
fig_monthly_del.add_trace(go.Scatter(
    x=monthly_del["year_month"],
    y=monthly_del["on_time_rate_pct"],
    name="On-Time Rate %",
    mode="lines+markers",
    line=dict(color=PALETTE["success"], width=2.5),
    marker=dict(size=5),
    yaxis="y1",
    hovertemplate="<b>%{x}</b><br>On-Time: %{y:.1f}%<extra></extra>",
))
fig_monthly_del.add_trace(go.Bar(
    x=monthly_del["year_month"],
    y=monthly_del["avg_delivery_days"],
    name="Avg Delivery Days",
    marker_color=PALETTE["secondary"],
    opacity=0.6,
    yaxis="y2",
    hovertemplate="<b>%{x}</b><br>Avg Days: %{y:.1f} Days<extra></extra>",
))

monthly_del_layout = get_plotly_layout(
    height=340,
    title="Monthly On-Time Rate (%) vs Average Transit Duration (Days)"
)
monthly_del_layout["yaxis"] = dict(title="On-Time Rate %", range=[60, 100], showgrid=True, gridcolor="#F1F5F9")
monthly_del_layout["yaxis2"] = dict(title="Avg Transit Days", overlaying="y", side="right", range=[0, 35], showgrid=False)
fig_monthly_del.update_layout(monthly_del_layout)
st.plotly_chart(fig_monthly_del, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# Seller Fulfillment Leaderboard
st.markdown('<div class="section-title">Seller Fulfillment Performance Leaderboard</div>', unsafe_allow_html=True)
col_sel_ctrl, _ = st.columns([1.5, 2])
with col_sel_ctrl:
    min_seller_orders = st.slider("Minimum Orders Threshold per Seller", min_value=10, max_value=100, value=25)

seller_df = get_seller_delivery_rankings(min_orders=min_seller_orders)

st.dataframe(
    seller_df.head(40)[[
        "seller_id", "seller_state", "seller_city", "eligible_orders_count",
        "total_revenue", "on_time_rate_pct", "avg_delay_days", "avg_delivery_days", "avg_review_score"
    ]].rename(columns={
        "seller_id": "Seller ID",
        "seller_state": "State",
        "seller_city": "City",
        "eligible_orders_count": "Orders",
        "total_revenue": "Revenue (R$)",
        "on_time_rate_pct": "On-Time %",
        "avg_delay_days": "Avg Delay",
        "avg_delivery_days": "Avg Days",
        "avg_review_score": "Rating",
    }),
    use_container_width=True,
    hide_index=True,
)

csv_sellers = seller_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Seller Benchmarking CSV",
    data=csv_sellers,
    file_name="seller_fulfillment_benchmarks.csv",
    mime="text/csv",
)
