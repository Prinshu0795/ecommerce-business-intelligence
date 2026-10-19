"""
Page 1: Executive Overview Dashboard
Commercial KPIs, monthly trends, Pareto category analysis, and regional performance.
Clean executive styling with zero emoji clutter and non-overlapping layouts.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.dashboard.ui_components import (
    render_header,
    load_filter_options,
    get_plotly_layout,
    PALETTE,
)
from src.analytics.sales_analysis import (
    get_executive_kpis,
    get_monthly_sales_trends,
    get_category_pareto_breakdown,
    get_order_status_distribution,
    get_state_sales_distribution,
)

st.set_page_config(page_title="Executive Overview | E-Commerce BI", layout="wide")

render_header(
    title="Executive Overview: Sales & Order Performance",
    subtitle="Commercial KPIs, revenue trajectory, category Pareto dynamics, and regional demand.",
)

# Sidebar Filters
states, categories = load_filter_options()

with st.sidebar:
    st.markdown("### Dashboard Filters")
    selected_state = st.selectbox("Customer State", states, index=0)
    selected_category = st.selectbox("Product Category", categories, index=0)
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("Start Date", value=pd.to_datetime("2016-09-01"), key="exec_start")
    with col_d2:
        end_date = st.date_input("End Date", value=pd.to_datetime("2018-10-18"), key="exec_end")

filter_state_param = None if selected_state == "All States" else selected_state
filter_cat_param = None if selected_category == "All Categories" else selected_category

# Fetch KPIs
kpis = get_executive_kpis(
    start_date=str(start_date),
    end_date=str(end_date),
    customer_state=filter_state_param,
    category_name=filter_cat_param,
)

# Render Clean Native Streamlit Metric Cards (Zero Overlap, 4 Columns)
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric(
        label="Total Delivered Revenue",
        value=f"R$ {kpis['delivered_gmv']:,.0f}",
        delta=f"AOV R$ {kpis['delivered_aov']:.2f}",
        help="Gross Merchandise Value for completed delivered orders.",
    )

with k2:
    st.metric(
        label="Delivered Orders",
        value=f"{kpis['delivered_orders']:,}",
        delta=f"{round(kpis['delivered_orders'] * 100 / max(1, kpis['total_orders']), 1)}% Fulfillment",
        help="Orders successfully delivered to customers.",
    )

with k3:
    st.metric(
        label="Delivered Freight",
        value=f"R$ {kpis['delivered_freight']:,.0f}",
        delta=f"{round(kpis['delivered_freight'] * 100 / max(1, kpis['delivered_gmv']), 1)}% of GMV",
        delta_color="off",
        help="Total customer shipping fees paid for delivered orders.",
    )

with k4:
    st.metric(
        label="Order Cancellation Rate",
        value=f"{kpis['cancellation_rate_pct']:.2f}%",
        delta=f"{kpis['canceled_orders']:,} Canceled",
        delta_color="inverse",
        help="Canceled orders divided by total recorded orders.",
    )

st.markdown("<br>", unsafe_allow_html=True)

# Trend Charts
col_trend1, col_trend2 = st.columns(2)

monthly_df = get_monthly_sales_trends(
    start_date=str(start_date),
    end_date=str(end_date),
    customer_state=filter_state_param,
)

with col_trend1:
    fig_orders = go.Figure()
    fig_orders.add_trace(go.Bar(
        x=monthly_df["year_month"],
        y=monthly_df["delivered_orders"],
        name="Delivered Orders",
        marker_color=PALETTE["secondary"],
        hovertemplate="<b>%{x}</b><br>Delivered Orders: %{y:,}<extra></extra>",
    ))
    fig_orders.add_trace(go.Scatter(
        x=monthly_df["year_month"],
        y=monthly_df["delivered_orders"],
        name="Order Volume Trend",
        mode="lines+markers",
        line=dict(color=PALETTE["primary"], width=2),
        marker=dict(size=4),
        hoverinfo="skip",
    ))
    fig_orders.update_layout(get_plotly_layout(
        height=340,
        title="Monthly Delivered Order Volume Trend"
    ))
    st.plotly_chart(fig_orders, use_container_width=True)

with col_trend2:
    fig_gmv = go.Figure()
    fig_gmv.add_trace(go.Bar(
        x=monthly_df["year_month"],
        y=monthly_df["monthly_gmv"],
        name="Monthly GMV (R$)",
        marker_color=PALETTE["accent"],
        hovertemplate="<b>%{x}</b><br>GMV: R$ %{y:,.2f}<extra></extra>",
    ))
    fig_gmv.add_trace(go.Scatter(
        x=monthly_df["year_month"],
        y=monthly_df["gmv_3month_ma"],
        name="3-Month Moving Average",
        mode="lines",
        line=dict(color=PALETTE["warning"], width=2.5, dash="dot"),
        hovertemplate="<b>%{x}</b><br>3-Mo MA: R$ %{y:,.2f}<extra></extra>",
    ))
    fig_gmv.update_layout(get_plotly_layout(
        height=340,
        title="Monthly Delivered Merchandise Value (GMV) & 3-Mo Moving Avg"
    ))
    st.plotly_chart(fig_gmv, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# Category Pareto & Order Status Funnel
col_cat, col_status = st.columns([1.4, 1.0])

with col_cat:
    pareto_df = get_category_pareto_breakdown(top_n=12)
    top_pareto = pareto_df.head(12)
    
    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Bar(
        x=top_pareto["category_name"],
        y=top_pareto["category_revenue"],
        name="Revenue (R$)",
        marker_color=PALETTE["primary"],
        hovertemplate="<b>%{x}</b><br>Revenue: R$ %{y:,.2f}<extra></extra>",
        yaxis="y",
    ))
    fig_pareto.add_trace(go.Scatter(
        x=top_pareto["category_name"],
        y=top_pareto["cumulative_share_pct"],
        name="Cumulative Share %",
        mode="lines+markers",
        line=dict(color=PALETTE["danger"], width=2),
        marker=dict(size=5),
        hovertemplate="<b>%{x}</b><br>Cumulative: %{y:.1f}%<extra></extra>",
        yaxis="y2",
    ))
    
    pareto_layout = get_plotly_layout(
        height=360,
        title="Category Pareto Analysis (Top 12 Categories vs Cumulative Share)"
    )
    pareto_layout["yaxis2"] = dict(
        title="Cumulative Share %",
        overlaying="y",
        side="right",
        range=[0, 105],
        showgrid=False,
        tickfont=dict(size=10, color="#64748B"),
    )
    pareto_layout["xaxis"]["tickangle"] = -30
    fig_pareto.update_layout(pareto_layout)
    st.plotly_chart(fig_pareto, use_container_width=True)

with col_status:
    status_df = get_order_status_distribution()
    fig_status = px.pie(
        status_df,
        names="order_status",
        values="order_count",
        hole=0.45,
        color_discrete_sequence=PALETTE["chart_sequence"],
    )
    fig_status.update_layout(get_plotly_layout(
        height=360,
        title="Order Lifecycle & Status Distribution"
    ))
    fig_status.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Orders: %{value:,} (%{percent})<extra></extra>",
    )
    st.plotly_chart(fig_status, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# Geographic Demand Breakdown
st.markdown('<div class="section-title">Geographic Revenue Concentration by Customer State</div>', unsafe_allow_html=True)
state_df = get_state_sales_distribution()

col_geo1, col_geo2 = st.columns([1.5, 1.0])

with col_geo1:
    fig_state = px.bar(
        state_df.head(12),
        x="customer_state",
        y="total_gmv",
        color="total_gmv",
        color_continuous_scale="Blues",
        labels={"customer_state": "State", "total_gmv": "GMV (R$)"},
    )
    fig_state.update_layout(get_plotly_layout(
        height=320,
        title="Top 12 States by Delivered Merchandise Value (BRL)"
    ))
    fig_state.update_coloraxes(showscale=False)
    fig_state.update_traces(hovertemplate="<b>State: %{x}</b><br>Delivered GMV: R$ %{y:,.2f}<extra></extra>")
    st.plotly_chart(fig_state, use_container_width=True)

with col_geo2:
    st.markdown("**Top 5 States Summary:**")
    st.dataframe(
        state_df.head(5)[["customer_state", "total_orders", "total_gmv", "gmv_share_pct", "aov"]].rename(
            columns={
                "customer_state": "State",
                "total_orders": "Orders",
                "total_gmv": "GMV (R$)",
                "gmv_share_pct": "Share %",
                "aov": "AOV (R$)",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

# Evidence-Based Executive Insights Section
st.markdown("""
<div class="insight-card">
    <b>Commercial Insights:</b> High fulfillment reliability (97.02% delivered) with very low cancellation rate (0.63%). 
    Revenue is concentrated in lifestyle and home categories, with São Paulo (SP) capturing 37.5% of national sales.
</div>
""", unsafe_allow_html=True)

# Export Data Button
csv_monthly = monthly_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Filtered Monthly Trends CSV",
    data=csv_monthly,
    file_name="executive_monthly_trends.csv",
    mime="text/csv",
)
