"""
Page 2: Customer Intelligence & Segmentation
RFM Analysis, Rule-Based Segmentation, K-Means Clustering,
and Cohort Retention Dynamics. Clean executive styling with zero emoji clutter.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from config.settings import RFM_REFERENCE_DATE
from src.dashboard.ui_components import (
    render_header,
    get_plotly_layout,
    PALETTE,
)
from src.analytics.customer_analysis import (
    get_customer_rfm_dataset,
    get_rfm_segment_summary,
    run_kmeans_clustering,
    get_cohort_retention_data,
)

st.set_page_config(page_title="Customer Intelligence | E-Commerce BI", layout="wide")

render_header(
    title="Customer Intelligence & RFM Segmentation",
    subtitle="Behavioral customer segmentation, cohort lifecycle retention, and machine learning cluster validation.",
    metadata_badge=f"Snapshot: {RFM_REFERENCE_DATE}"
)

# Load RFM Data (Cached per session)
@st.cache_data(show_spinner=False)
def load_cached_rfm():
    return get_customer_rfm_dataset()

df_rfm = load_cached_rfm()
segment_summary = get_rfm_segment_summary(df_rfm)

# High Level Customer Metrics (Clean Native st.metric, Zero Overlap)
c1, c2, c3, c4 = st.columns(4)
total_unique_cust = len(df_rfm)
repeat_cust_count = int((df_rfm["frequency"] > 1).sum())
repeat_rate = (repeat_cust_count / total_unique_cust) * 100.0
total_spend = df_rfm["monetary"].sum()
avg_clv = total_spend / total_unique_cust

with c1:
    st.metric(
        label="Unique Customer Base",
        value=f"{total_unique_cust:,}",
        help="Count of unique customer_unique_id tokens.",
    )

with c2:
    st.metric(
        label="Repeat Purchase Rate",
        value=f"{repeat_rate:.2f}%",
        delta=f"{repeat_cust_count:,} Repeat Buyers",
        help="Percentage of customers with more than one completed order.",
    )

with c3:
    st.metric(
        label="Average Customer Spend",
        value=f"R$ {avg_clv:.2f}",
        help="Total delivered merchandise spend divided by total unique customers.",
    )

with c4:
    st.metric(
        label="Analysis Snapshot Date",
        value=RFM_REFERENCE_DATE,
        help="Standard baseline date used to calculate historical recency in days.",
    )

st.markdown("<br>", unsafe_allow_html=True)

# Segment Distribution & Monetary Contribution
col_dist, col_rev = st.columns([1.1, 1.2])

with col_dist:
    fig_seg = px.pie(
        segment_summary,
        names="rfm_segment",
        values="customer_count",
        hole=0.4,
        color_discrete_sequence=PALETTE["chart_sequence"],
    )
    fig_seg.update_layout(get_plotly_layout(
        height=360,
        title="Customer Base Share by RFM Segment"
    ))
    fig_seg.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Customers: %{value:,} (%{percent})<extra></extra>",
    )
    st.plotly_chart(fig_seg, use_container_width=True)

with col_rev:
    fig_bar = px.bar(
        segment_summary,
        x="rfm_segment",
        y="total_revenue",
        color="rfm_segment",
        color_discrete_sequence=PALETTE["chart_sequence"],
        labels={"rfm_segment": "Segment", "total_revenue": "Total Spend (R$)"},
    )
    fig_bar.update_layout(get_plotly_layout(
        height=360,
        title="Total Revenue Contribution by RFM Segment (BRL)"
    ))
    fig_bar.update_layout(showlegend=False)
    fig_bar.update_traces(hovertemplate="<b>%{x}</b><br>Total Spend: R$ %{y:,.2f}<extra></extra>")
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# Segment Performance Table
st.markdown('<div class="section-title">Segment Performance Breakdown & Rule Definitions</div>', unsafe_allow_html=True)
st.dataframe(
    segment_summary.rename(columns={
        "rfm_segment": "RFM Segment",
        "customer_count": "Customer Count",
        "customer_share_pct": "Customer Share %",
        "total_revenue": "Total GMV (R$)",
        "revenue_share_pct": "Revenue Share %",
        "avg_recency_days": "Avg Recency (Days)",
        "avg_frequency": "Avg Orders",
        "avg_monetary": "Avg Spend (R$)",
    }),
    use_container_width=True,
    hide_index=True,
)

st.markdown("<br>", unsafe_allow_html=True)

# Cohort Retention Heatmap
st.markdown('<div class="section-title">Customer Cohort Retention Matrix</div>', unsafe_allow_html=True)
cohort_sizes, retention_matrix = get_cohort_retention_data()
retention_display = retention_matrix.iloc[:, :13]

fig_cohort = px.imshow(
    retention_display,
    labels=dict(x="Months Since First Purchase (Cohort Index)", y="Acquisition Cohort Month", color="Retention %"),
    x=[f"Month {col}" for col in retention_display.columns],
    y=retention_display.index.astype(str),
    color_continuous_scale="Blues",
    aspect="auto",
    text_auto=".1f",
)
fig_cohort.update_layout(get_plotly_layout(
    height=440,
    title="Monthly Customer Cohort Retention Rates (%)"
))
fig_cohort.update_traces(hovertemplate="<b>Cohort: %{y}</b><br>%{x}<br>Retention Rate: %{z:.2f}%<extra></extra>")
st.plotly_chart(fig_cohort, use_container_width=True)

st.markdown("""
<div class="insight-card">
    <b>Cohort Retention Insight:</b> The Olist marketplace operates predominantly as an acquisition engine. 
    Month 1 repeat retention hovers between 0.4% and 0.8%, indicating that the overwhelming majority of customers 
    are one-off buyers, highlighting the strategic business opportunity for post-purchase re-engagement incentives.
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# K-Means Clustering Extension
st.markdown('<div class="section-title">Unsupervised Customer Clustering (K-Means Extension)</div>', unsafe_allow_html=True)
col_k_ctrl, col_k_info = st.columns([1, 2])
with col_k_ctrl:
    n_clusters = st.slider("Select Number of Clusters (k)", min_value=3, max_value=6, value=4)

df_clustered, km_meta = run_kmeans_clustering(df_rfm, n_clusters=n_clusters)

with col_k_info:
    st.markdown(f"""
    - **Algorithm:** K-Means on standardized log features: `log1p(Recency)`, `log1p(Frequency)`, `log1p(Monetary)`.
    - **Silhouette Score:** `{km_meta['silhouette_score']:.3f}` (Evaluated on out-of-sample partition).
    - **Methodology:** Uncovers natural data clusters without manual thresholding, complementing rule-based business segments.
    """)

# 2D Scatter of Clusters
fig_cluster = px.scatter(
    df_clustered,
    x="recency_days",
    y="monetary",
    color=df_clustered["cluster"].astype(str),
    log_y=True,
    title=f"K-Means Customer Clusters (k={n_clusters}) - Recency vs Monetary Spend",
    labels={"recency_days": "Recency (Days)", "monetary": "Monetary Spend (R$, Log Scale)", "color": "Cluster"},
    color_discrete_sequence=PALETTE["chart_sequence"],
    hover_data=["customer_unique_id", "frequency", "rfm_segment"],
    opacity=0.6,
)
fig_cluster.update_layout(get_plotly_layout(height=360))
st.plotly_chart(fig_cluster, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# Customer Drill-Down Table & CSV Export
st.markdown('<div class="section-title">Customer Analytical Drill-Down</div>', unsafe_allow_html=True)
col_s1, col_s2 = st.columns([1.5, 1.0])
with col_s1:
    search_query = st.text_input("Search Customer ID or State", placeholder="Enter ID prefix or state abbreviation...")
with col_s2:
    filter_seg = st.selectbox("Filter Segment", ["All Segments"] + sorted(df_rfm["rfm_segment"].unique().tolist()))

df_filtered_view = df_rfm.copy()
if filter_seg != "All Segments":
    df_filtered_view = df_filtered_view[df_filtered_view["rfm_segment"] == filter_seg]
if search_query:
    q = search_query.strip().lower()
    df_filtered_view = df_filtered_view[
        df_filtered_view["customer_unique_id"].str.lower().str.contains(q)
        | df_filtered_view["customer_state"].str.lower().str.contains(q)
    ]

st.dataframe(
    df_filtered_view.head(60)[[
        "customer_unique_id", "customer_state", "customer_city",
        "frequency", "monetary", "recency_days", "rfm_segment"
    ]].rename(columns={
        "customer_unique_id": "Customer Unique ID",
        "customer_state": "State",
        "customer_city": "City",
        "frequency": "Orders",
        "monetary": "Spend (R$)",
        "recency_days": "Recency (Days)",
        "rfm_segment": "Segment",
    }),
    use_container_width=True,
    hide_index=True,
)

# Download CSV
csv_cust = df_filtered_view.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Filtered Customers CSV",
    data=csv_cust,
    file_name="segmented_customers.csv",
    mime="text/csv",
)
