"""
Dashboard UI Components & Executive Theme Styling
Clean, non-overlapping design system inspired by modern retail executive dashboards.
Zero emoji clutter; professional corporate typography and responsive layouts.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional
import pandas as pd
from src.database.connection import query_df

# Modern Executive Color Palette
PALETTE = {
    "primary": "#1E3A8A",      # Deep Navy
    "secondary": "#0284C7",    # Ocean Blue
    "accent": "#0D9488",       # Teal
    "success": "#16A34A",      # Green
    "warning": "#D97706",      # Amber
    "danger": "#DC2626",       # Red
    "neutral_dark": "#0F172A", # Slate 900
    "neutral_mid": "#475569",  # Slate 600
    "neutral_light": "#F8FAFC",# Slate 50
    "border": "#E2E8F0",       # Slate 200
    "chart_sequence": [
        "#1E3A8A", "#0284C7", "#0D9488", "#D97706", "#7C3AED",
        "#DB2777", "#059669", "#4F46E5", "#EA580C", "#64748B"
    ]
}


def apply_custom_styles():
    """Inject clean, professional corporate CSS without emoji clutter or overlapping elements."""
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            
            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                color: #0F172A;
            }
            
            /* Main Container Padding */
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 3rem;
                padding-left: 2.5rem;
                padding-right: 2.5rem;
                max-width: 1440px;
            }
            
            /* Clean Metric Card Styling (Zero Overlap) */
            [data-testid="stMetric"] {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 16px 20px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
                transition: transform 0.15s ease, box-shadow 0.15s ease;
                min-height: 105px;
            }
            [data-testid="stMetric"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
            }
            [data-testid="stMetricLabel"] {
                font-size: 0.80rem !important;
                font-weight: 600 !important;
                color: #64748B !important;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 4px;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.65rem !important;
                font-weight: 700 !important;
                color: #0F172A !important;
                line-height: 1.25;
            }
            [data-testid="stMetricDelta"] {
                font-size: 0.80rem !important;
                font-weight: 600 !important;
                margin-top: 4px;
            }
            
            /* Tabs Navigation */
            .stTabs [data-baseweb="tab-list"] {
                gap: 6px;
                border-bottom: 2px solid #E2E8F0;
                margin-bottom: 1.5rem;
            }
            .stTabs [data-baseweb="tab"] {
                height: 42px;
                white-space: nowrap;
                background-color: transparent;
                border-radius: 6px 6px 0px 0px;
                padding: 8px 16px;
                color: #475569;
                font-weight: 500;
                font-size: 0.90rem;
                border-bottom: 2px solid transparent;
                transition: all 0.15s ease;
            }
            .stTabs [aria-selected="true"] {
                color: #0284C7 !important;
                font-weight: 600 !important;
                border-bottom: 2px solid #0284C7 !important;
            }
            
            /* Sidebar Styling */
            [data-testid="stSidebar"] {
                background-color: #F8FAFC;
                border-right: 1px solid #E2E8F0;
            }
            [data-testid="stSidebar"] .block-container {
                padding-top: 2rem;
                padding-left: 1.5rem;
                padding-right: 1.5rem;
            }
            
            /* Section Headers */
            .executive-header {
                font-size: 1.5rem;
                font-weight: 700;
                color: #0F172A;
                margin-bottom: 0.25rem;
                letter-spacing: -0.02em;
            }
            .executive-subheader {
                font-size: 0.90rem;
                color: #64748B;
                margin-bottom: 1.5rem;
            }
            .section-title {
                font-size: 1.10rem;
                font-weight: 600;
                color: #0F172A;
                margin-top: 1rem;
                margin-bottom: 0.75rem;
                padding-bottom: 0.25rem;
                border-bottom: 1px solid #F1F5F9;
            }
            
            /* Callout / Insight Container */
            .insight-card {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-left: 4px solid #0284C7;
                border-radius: 6px;
                padding: 14px 18px;
                margin-top: 1rem;
                margin-bottom: 1rem;
                font-size: 0.88rem;
                color: #334155;
                line-height: 1.6;
            }
            
            /* Table Styling */
            [data-testid="stDataFrame"] {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                overflow: hidden;
            }
            
            /* Primary Buttons */
            .stButton button {
                border-radius: 6px;
                font-weight: 500;
                font-size: 0.88rem;
            }
        </style>
    """, unsafe_allow_html=True)


def render_header(title: str, subtitle: str = "", metadata_badge: str = ""):
    """Render a clean, modern executive title header without emojis."""
    apply_custom_styles()
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown(f'<div class="executive-header">{title}</div>', unsafe_allow_html=True)
        if subtitle:
            st.markdown(f'<div class="executive-subheader">{subtitle}</div>', unsafe_allow_html=True)
    with col_t2:
        if metadata_badge:
            st.markdown(
                f'<div style="text-align:right; font-size:0.80rem; color:#64748B; padding-top:8px;">{metadata_badge}</div>',
                unsafe_allow_html=True
            )
    st.markdown("<hr style='margin: 0.25rem 0 1.25rem 0; border: none; border-top: 1px solid #E2E8F0;' />", unsafe_allow_html=True)


def load_filter_options():
    """Load filter options from database."""
    states_df = query_df("SELECT DISTINCT customer_state FROM dim_customer WHERE customer_state IS NOT NULL ORDER BY customer_state;")
    states = ["All States"] + states_df["customer_state"].tolist()

    cats_df = query_df("SELECT DISTINCT product_category_name_english FROM dim_product WHERE product_category_name_english IS NOT NULL ORDER BY product_category_name_english;")
    categories = ["All Categories"] + [c for c in cats_df["product_category_name_english"].tolist() if c]

    return states, categories


def get_plotly_layout(height: int = 380, title: str = "") -> dict:
    """Return unified Plotly layout parameters for crisp corporate appearance."""
    return dict(
        height=height,
        title=dict(
            text=title,
            font=dict(family="Inter, sans-serif", size=13, color="#0F172A", weight=600),
            x=0.01,
            y=0.96,
        ),
        font=dict(family="Inter, sans-serif", size=11, color="#64748B"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=45, r=30, t=55 if title else 25, b=45),
        xaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            linecolor="#E2E8F0",
            tickfont=dict(size=10, color="#64748B"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            linecolor="#E2E8F0",
            tickfont=dict(size=10, color="#64748B"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color="#475569"),
        ),
    )
