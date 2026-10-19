"""
Page 4: Customer Experience, Statistical Testing & Predictive Analytics
CSAT score distributions, delay impact, two-sample hypothesis testing,
and monthly order volume forecasting extension. Clean executive styling with zero emoji clutter.
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
from src.analytics.review_analysis import (
    get_review_summary_metrics,
    get_review_score_distribution,
    get_delay_vs_review_score,
    get_category_review_scores,
)
from src.analytics.statistical_analysis import run_delivery_review_statistical_test
from src.analytics.forecasting import run_monthly_order_forecasting

st.set_page_config(page_title="Customer Experience | E-Commerce BI", layout="wide")

render_header(
    title="Customer Experience & Empirical Statistical Analysis",
    subtitle="CSAT score distributions, delay impact on satisfaction, two-sample hypothesis testing, and order volume forecasting.",
)

# Sidebar Filters
_, categories = load_filter_options()
with st.sidebar:
    st.markdown("### Experience Filters")
    selected_category = st.selectbox("Product Category", categories, index=0)
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("Start Date", value=pd.to_datetime("2016-09-01"), key="csat_start_p4")
    with col_d2:
        end_date = st.date_input("End Date", value=pd.to_datetime("2018-10-18"), key="csat_end_p4")

filter_cat_param = None if selected_category == "All Categories" else selected_category

# High-Level CSAT Metrics
rev_metrics = get_review_summary_metrics(
    start_date=str(start_date),
    end_date=str(end_date),
    category_name=filter_cat_param,
)

# Clean Native Streamlit Metric Cards (Zero Overlap, 4 Columns)
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="Average Review Score",
        value=f"{rev_metrics['avg_review_score']:.2f} / 5.0",
        delta=f"{rev_metrics['total_reviews']:,} Reviews",
        help="Overall mean review rating for delivered orders.",
    )

with c2:
    st.metric(
        label="5-Star Ratings (Promoters)",
        value=f"{rev_metrics['five_star_rate_pct']:.1f}%",
        delta=f"{rev_metrics['five_star_count']:,} Top Reviews",
        help="Percentage of reviews giving the maximum rating of 5 stars.",
    )

with c3:
    st.metric(
        label="Low-Rating Rate (Detractors)",
        value=f"{rev_metrics['low_rating_rate_pct']:.1f}%",
        delta=f"{rev_metrics['low_rating_count']:,} Low (1-2 Stars)",
        delta_color="inverse",
        help="Percentage of reviews with 1 or 2 stars.",
    )

with c4:
    st.metric(
        label="Written Comments Rate",
        value=f"{round(rev_metrics['text_comment_count'] * 100 / max(1, rev_metrics['total_reviews']), 1)}%",
        delta=f"{rev_metrics['text_comment_count']:,} Explanatory Texts",
        delta_color="off",
        help="Percentage of reviews that included a written text message.",
    )

st.markdown("<br>", unsafe_allow_html=True)

# Score Distribution & Delay Bracket Impact
col_dist, col_delay = st.columns([1.0, 1.4])

with col_dist:
    score_dist = get_review_score_distribution()
    fig_score = px.bar(
        score_dist,
        x="review_score",
        y="review_count",
        color="sentiment",
        text="percentage",
        color_discrete_map={
            "Positive": PALETTE["success"],
            "Neutral": PALETTE["warning"],
            "Negative (Dissatisfied)": PALETTE["danger"],
        },
        labels={"review_score": "Star Rating (1-5)", "review_count": "Total Reviews"},
    )
    fig_score.update_layout(get_plotly_layout(
        height=340,
        title="Review Score Rating Distribution (1 to 5 Stars)"
    ))
    fig_score.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
        hovertemplate="<b>%{x} Stars</b><br>Reviews: %{y:,} (%{text:.1f}%)<extra></extra>",
    )
    st.plotly_chart(fig_score, use_container_width=True)

with col_delay:
    delay_csat = get_delay_vs_review_score()
    
    fig_bracket = go.Figure()
    fig_bracket.add_trace(go.Bar(
        x=delay_csat["delay_bracket"],
        y=delay_csat["avg_review_score"],
        name="Mean Review Rating (Stars)",
        marker_color=PALETTE["secondary"],
        yaxis="y1",
        text=delay_csat["avg_review_score"],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Avg Score: %{y:.2f} Stars<extra></extra>",
    ))
    fig_bracket.add_trace(go.Scatter(
        x=delay_csat["delay_bracket"],
        y=delay_csat["low_rating_pct"],
        name="Low-Rating Rate % (1-2 Stars)",
        mode="lines+markers",
        line=dict(color=PALETTE["danger"], width=2.5),
        marker=dict(size=6),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Low Rating Rate: %{y:.1f}%<extra></extra>",
    ))
    
    bracket_layout = get_plotly_layout(
        height=340,
        title="Impact of Delivery Timeliness on Average Review Score & Dissatisfaction"
    )
    bracket_layout["yaxis"] = dict(title="Avg Rating (Stars)", range=[0, 5.2], showgrid=True)
    bracket_layout["yaxis2"] = dict(title="Low Rating Rate %", overlaying="y", side="right", range=[0, 100], showgrid=False)
    bracket_layout["xaxis"]["tickangle"] = -25
    fig_bracket.update_layout(bracket_layout)
    st.plotly_chart(fig_bracket, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# RIGOROUS STATISTICAL HYPOTHESIS TESTING PANEL
st.markdown('<div class="section-title">Two-Sample Statistical Hypothesis Testing & Effect Size Analysis</div>', unsafe_allow_html=True)

stat_results = run_delivery_review_statistical_test()

sc1, sc2, sc3, sc4 = st.columns(4)

with sc1:
    st.metric(
        label="On-Time Mean Rating",
        value=f"{stat_results['mean_ontime']} ★",
        delta=f"N = {stat_results['n_ontime']:,}",
        help="Sample size and mean for on-time/early deliveries.",
    )

with sc2:
    st.metric(
        label="Delayed Mean Rating",
        value=f"{stat_results['mean_delayed']} ★",
        delta=f"N = {stat_results['n_delayed']:,}",
        delta_color="inverse",
        help="Sample size and mean for delayed deliveries.",
    )

with sc3:
    st.metric(
        label="Mean Difference (Δ)",
        value=f"+{stat_results['diff_in_means']} Stars",
        delta=f"95% CI: [{stat_results['ci_95_diff'][0]}, {stat_results['ci_95_diff'][1]}]",
        help="Difference in means between on-time and delayed groups.",
    )

with sc4:
    st.metric(
        label="Effect Size (Cohen's d)",
        value=f"d = {stat_results['cohens_d']}",
        delta="Large Practical Magnitude",
        help="Standardized mean difference measuring real-world magnitude.",
    )

st.markdown(f"""
<div class="insight-card">
    <b>Hypothesis Testing Inference & Confidence Intervals:</b><br>
    - <b>Welch's Two-Sample t-Test:</b> t-statistic = <b>{stat_results['t_statistic']}</b>, p-value &lt; <b>0.001</b> (Statistically Significant; reject H0).<br>
    - <b>Mann-Whitney U Test (Non-Parametric):</b> U-statistic = <b>{int(stat_results['mann_whitney_u']):,}</b>, p-value &lt; <b>0.001</b>.<br>
    - <b>Dissatisfaction Escalation:</b> Low-rating rate (1-2 stars) is only <b>{stat_results['low_rating_rate_ontime_pct']}%</b> for on-time orders, but surges to <b>{stat_results['low_rating_rate_delayed_pct']}%</b> for delayed deliveries.<br>
    <span style="font-size:0.80rem; color:#64748B;">Note: Observational correlation demonstrates operational vulnerability; product manufacturing defects or seller customer support may be confounding factors.</span>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# OPTIONAL ANALYTICAL EXTENSION: TIME SERIES ORDER FORECASTING
st.markdown('<div class="section-title">Time Series Predictive Extension: Monthly Order Volume Forecasting</div>', unsafe_allow_html=True)

fc_results = run_monthly_order_forecasting(test_horizon=4)
test_metrics = fc_results["metrics"]

fc_c1, fc_c2, fc_c3 = st.columns(3)

with fc_c1:
    st.metric(
        label="Exponential Smoothing Test WAPE",
        value=f"{test_metrics['exponential_smoothing']['test_wape_pct']:.1f}%",
        delta=f"MAE: {test_metrics['exponential_smoothing']['test_mae']} Orders",
    )

with fc_c2:
    st.metric(
        label="Naive Baseline Test WAPE",
        value=f"{test_metrics['naive_baseline']['test_wape_pct']:.1f}%",
        delta=f"MAE: {test_metrics['naive_baseline']['test_mae']} Orders",
        delta_color="off",
    )

with fc_c3:
    st.metric(
        label="Out-of-Sample Test Window",
        value=f"{fc_results['test_horizon']} Months",
        delta="Strict Time-Based Split",
    )

# Forecast Plot
hist_df = fc_results["historical_df"]
test_df = fc_results["test_results_df"]
future_df = fc_results["future_forecast_df"]

fig_fc = go.Figure()

fig_fc.add_trace(go.Scatter(
    x=hist_df["year_month"],
    y=hist_df["delivered_orders"],
    name="Historical Actual Orders",
    mode="lines+markers",
    line=dict(color=PALETTE["primary"], width=2),
    marker=dict(size=4),
))

fig_fc.add_trace(go.Scatter(
    x=test_df["year_month"],
    y=test_df["exponential_smoothing_forecast"],
    name="Test Forecast (Holt-Winters)",
    mode="lines+markers",
    line=dict(color=PALETTE["secondary"], width=2, dash="dash"),
    marker=dict(size=5),
))

fig_fc.add_trace(go.Scatter(
    x=test_df["year_month"],
    y=test_df["naive_baseline_forecast"],
    name="Test Baseline (Naive Drift)",
    mode="lines",
    line=dict(color="#94A3B8", width=1.5, dash="dot"),
))

fig_fc.add_trace(go.Scatter(
    x=future_df["year_month"],
    y=future_df["projected_orders"],
    name="Future Projection (3 Months)",
    mode="lines+markers",
    line=dict(color=PALETTE["accent"], width=2.5),
    marker=dict(size=6),
))

fig_fc.add_trace(go.Scatter(
    x=list(future_df["year_month"]) + list(future_df["year_month"][::-1]),
    y=list(future_df["upper_bound_90ci"]) + list(future_df["lower_bound_90ci"][::-1]),
    fill="toself",
    fillcolor="rgba(13, 148, 136, 0.12)",
    line=dict(color="rgba(255,255,255,0)"),
    name="90% Prediction Interval",
    hoverinfo="skip",
))

fig_fc.update_layout(get_plotly_layout(
    height=360,
    title="Delivered Monthly Order Volume: Actuals, Test Evaluation & Out-of-Sample Projection"
))
st.plotly_chart(fig_fc, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# Product Category CSAT Comparison Table
st.markdown('<div class="section-title">Category Customer Satisfaction League Table</div>', unsafe_allow_html=True)
cat_csat_df = get_category_review_scores(min_reviews=40)

st.dataframe(
    cat_csat_df.head(25).rename(columns={
        "category_name": "Category",
        "total_reviews": "Reviews Count",
        "avg_review_score": "Average Rating (Stars)",
        "low_rating_rate_pct": "Dissatisfaction Rate % (1-2 Stars)",
    }),
    use_container_width=True,
    hide_index=True,
)
