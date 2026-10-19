# E-Commerce Business Intelligence & Customer Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/PostgreSQL%20%7C%20DuckDB-Dual%20Engine-brightgreen.svg)](https://duckdb.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red.svg)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Visualizations-blueviolet.svg)](https://plotly.com/)
[![Tests](https://img.shields.io/badge/pytest-12%20Passed%20(100%25)-success.svg)](https://pytest.org/)

An end-to-end, enterprise-grade Data Engineering, SQL Analytics, and Business Intelligence platform built upon the **Brazilian E-Commerce Public Dataset by Olist** (99,441 real customer orders, 112,650 line items, and R$ 13.2M+ in delivered GMV).

Designed for Data Analyst and Analytics Engineering portfolio evaluation and technical placement interviews, this repository delivers a complete data lifecycle: automated ingestion, dimensional Kimball star modeling, data quality gatekeeping, 18+ advanced analytical SQL queries, customer RFM segmentation, unsupervised K-Means clustering, lead-time logistics analytics, two-sample statistical hypothesis testing, and an interactive Streamlit BI application.

---

## 📑 Table of Contents
1. [Business Problem & Objectives](#1-business-problem--objectives)
2. [Technical Architecture](#2-technical-architecture)
3. [Relational Data Model (Kimball Star Schema)](#3-relational-data-model-kimball-star-schema)
4. [Key Business Findings](#4-key-business-findings)
5. [Advanced SQL Analytics](#5-advanced-sql-analytics)
6. [Streamlit Interactive Dashboard](#6-streamlit-interactive-dashboard)
7. [Installation & Quickstart Guide](#7-installation--quickstart-guide)
8. [Docker Compose PostgreSQL Deployment](#8-docker-compose-postgresql-deployment)
9. [Automated Testing Suite](#9-automated-testing-suite)
10. [Power BI Semantic Model Specifications](#10-power-bi-semantic-model-specifications)
11. [Project Structure](#11-project-structure)
12. [Limitations & Methodological Disclosures](#12-limitations--methodological-disclosures)

---

## 1. Business Problem & Objectives
Operating a national e-commerce marketplace across Brazil presents severe operational, logistical, and retention challenges:
- **Revenue Trajectory:** How are order volumes, GMV, and AOV evolving month-over-month?
- **Category Pareto Dynamics:** Which product categories drive the core 80% of merchandise value?
- **Retention Dynamics:** What proportion of customers return for repeat purchases, and how do acquisition cohorts decay over time?
- **Logistics Latency:** How do delivery lead times and carrier transit delays vary across regional states, and where are systemic delivery bottlenecks located?
- **Customer Experience & CSAT:** Does delivery delay empirically drive customer dissatisfaction, and what is the exact magnitude of this effect?

---

## 2. Technical Architecture
The platform is organized into a clean, modular Python and SQL architecture:

```
Raw Olist Datasets (9 CSVs, ~120MB)
     │
     ▼
src/ingestion/load_raw_data.py (Schema validation & profiling)
     │
     ▼
src/preprocessing/clean_data.py (Normalization, English translations, geo deduplication)
     │
     ▼
src/preprocessing/feature_engineering.py (RFM scoring, delivery delay metrics, header-grain rollups)
     │
     ▼
src/database/load_database.py (Idempotent DDL execution & bulk load)
     │
     ├──► Dual Database Engine (PostgreSQL via psycopg / Embedded DuckDB)
     ├──► src/validation/data_quality.py (21 Automated assertion checks)
     └──► src/validation/reconciliation.py (100% Source-to-target reconciliation)
     │
     ▼
SQL Query Layer (sql/*.sql - 18 Advanced Analytical Queries)
     │
     ▼
src/analytics/ (Sales, Customer RFM, Logistics, CSAT Stats, Time Series Forecasting)
     │
     ▼
Streamlit Multi-Page BI Application (app.py + 4 Executive Pages)
```

---

## 3. Relational Data Model (Kimball Star Schema)
To prevent Cartesian multiplication and financial aggregation errors, the data model strictly separates grain levels:
- **`fact_order` (Header Grain):** Exactly 1 row per order with pre-aggregated financial totals (`merchandise_value`, `freight_value`) and pre-calculated delivery duration metrics.
- **`fact_order_item` (Line Item Grain):** 1 row per item with composite PK `(order_id, order_item_id)`.
- **`fact_payment` (Installment Grain):** 1 row per payment sequence with composite PK `(order_id, payment_sequential)`.
- **`fact_review` (Survey Grain):** 1 row per customer survey with composite PK `(review_id, order_id)`.
- **Dimension Tables:** `dim_date` (calendar dimension), `dim_customer`, `dim_product`, `dim_seller`, `dim_geography`.

---

## 4. Key Business Findings
All metrics reflect real computed data from the 99,441 records:

| Business Dimension | Empirical Computed Evidence | Actionable Interpretation |
| :--- | :--- | :--- |
| **Fulfillment Reliability** | **97.02%** delivered (96,478 orders); only **0.63%** canceled (625 orders). | Overall fulfillment pipeline is robust; cancellations are minimal. |
| **Gross Merchandise Value** | **R$ 13,221,498.11** delivered GMV; **R$ 137.04** delivered AOV. | Consistent baseline order basket size across active years. |
| **Customer Retention** | **3.12%** repeat purchase rate (2,997 repeat buyers out of 96,096 unique customers). | The marketplace functions as a customer acquisition engine; post-purchase loyalty is critically under-monetized. |
| **Repeat Buyer Value** | Repeat buyer lifetime spend is **R$ 261.27** vs **R$ 133.05** for one-time buyers (**+96.4%**). | High ROI opportunity: converting 2% more one-time buyers yields over R$ 500k in high-margin GMV. |
| **On-Time Delivery SLA** | **91.89%** on-time delivery rate (88,649 on-time vs 7,827 delayed). | Conservative estimated delivery dates cushion 90%+ of orders. |
| **Customer Dissatisfaction Impact** | Mean review for on-time is **4.29 ★** vs **2.57 ★** for delayed (**$\Delta = +1.73$ stars, $p < 0.001$, Cohen's $d = 1.34$**). | Delivery delays trigger a **6.6x surge** in low-rating detractor reviews (8.4% to 55.4%). |
| **Regional Logistical Latency** | São Paulo (SP) averages **8.3 days** transit vs **28.9 days** in Roraima (RR) and **25.7 days** in Amapá (AP). | Geographic concentration of sellers in the Southeast creates long transit barriers into outer regions. |

---

## 5. Advanced SQL Analytics
The repository includes 10 standalone, production-ready SQL scripts (`sql/`) implementing over 18 distinct queries utilizing CTEs, Window functions, and Conditional Aggregations:
1. `sales_kpis.sql`: Overall executive sales KPIs, delivered GMV, freight, cancellation rate, delivered AOV.
2. `monthly_trends.sql`: Monthly order volumes, GMV, MoM growth rate (`LAG()`), 3-month moving average (`AVG() OVER (ROWS BETWEEN)`).
3. `product_analysis.sql`: Category revenue contribution, cumulative share (Pareto 80/20 analysis), top 3 selling products per category (`DENSE_RANK() OVER (PARTITION BY)`).
4. `customer_cohorts.sql`: First purchase cohorts, monthly cohort retention rate matrix, repeat purchase behavior summary.
5. `rfm_analysis.sql`: Customer Recency, Frequency, Monetary calculation, `NTILE(5)` scoring, and segment classification (`Champions`, `Loyal`, `At Risk`, `Lost`).
6. `delivery_performance.sql`: On-time delivery rate, lead-time breakdown (Approval -> Carrier -> Doorstep), state-level logistics latency.
7. `seller_rankings.sql`: Seller quality leaderboard with minimum sample size threshold (`HAVING COUNT >= 10`), on-time dispatch rate, customer satisfaction rating.
8. `review_analysis.sql`: Review score distribution, low rating rate, delay bracket cross-tabulation.
9. `geographic_analysis.sql`: Customer state demand concentration and intra-state vs inter-state shipping comparison.
10. `order_status_analysis.sql`: Order status funnel, cancellation timing, payment method financing installment adoption.

---

## 6. Streamlit Interactive Dashboard
A modern, executive analytics web application built with Streamlit and Plotly:
- **`app.py`:** Portal home, database health, executive performance cards, architecture summary, and reconciliation audit modal.
- **`pages/1_Executive_Overview.py`:** Monthly sales and volume trends, MoM growth rates, category Pareto 80/20 curve, order status donut, Brazil state demand distribution, and evidence-based insights narrative.
- **`pages/2_Customer_Intelligence.py`:** RFM segment distribution and monetary contribution, K-Means clustering comparison (with Silhouette score), monthly cohort retention heatmap, and customer drill-down table with CSV export.
- **`pages/3_Delivery_Analytics.py`:** Logistics lead-time waterfall, delay distribution histogram with SLA threshold, state delivery latency comparison, monthly timeliness trajectory, and seller fulfillment leaderboard (with order threshold slider).
- **`pages/4_Customer_Experience.py`:** CSAT score distributions, delay bracket impact on ratings, two-sample Welch's t-test and Mann-Whitney U test panels, and time-series monthly order volume forecasting extension (Holt-Winters vs Naive drift baseline evaluated with MAE and WAPE).

---

## 7. Installation & Quickstart Guide

### Prerequisites
- Python 3.12, 3.13, or 3.14
- Git

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/your-username/ecommerce-business-intelligence.git
cd ecommerce-business-intelligence

python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Dataset Placement
The Brazilian E-Commerce dataset CSV files should be placed in `Brazilian E-Commerce Public Dataset/` (or `data/raw/`). The 9 expected files are:
- `olist_customers_dataset.csv`
- `olist_geolocation_dataset.csv`
- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_products_dataset.csv`
- `olist_sellers_dataset.csv`
- `product_category_name_translation.csv`

*(If missing, run `python -m src.ingestion.download_data` for step-by-step instructions).*

### Step 4: Run ETL Pipeline & Database Ingestion
```bash
python -m src.database.load_database
```
*Loads all tables idempotently into DuckDB (zero setup required) or PostgreSQL, executes 21 automated data quality checks, and generates the reconciliation audit.*

### Step 5: Launch Streamlit BI Dashboard
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 8. Docker Compose PostgreSQL Deployment
For PostgreSQL deployment via Docker:

```bash
# 1. Copy environment template
copy .env.example .env

# 2. Start PostgreSQL container with persistent volume
docker-compose up -d

# 3. Update .env: set DB_BACKEND=postgresql
# 4. Run the ETL pipeline against PostgreSQL
python -m src.database.load_database

# 5. Launch dashboard
streamlit run app.py
```

---

## 9. Automated Testing Suite
Execute the comprehensive Pytest suite:
```bash
python -m pytest -v
```

### Test Coverage Highlights:
- `tests/test_data_quality.py`: Cleaning functions, duplicate handling, negative price filtering, date dimension generator, PK uniqueness.
- `tests/test_metrics.py`: Delivery delay formulas, evaluable order denominator exclusions, live database KPI bounds.
- `tests/test_customer_features.py`: Customer RFM frequency/monetary rollups, RFM score binning, cohort index arithmetic.
- `tests/test_sql_reconciliation.py`: Exact row counts and financial totals matching between raw CSVs and relational database tables (100% pass).

---

## 10. Power BI Semantic Model Specifications
Comprehensive enterprise Power BI documentation is included in the `powerbi/` folder:
- **`powerbi/data_model.md`:** Star-schema diagram, cardinality specifications (1:N single-directional filtering), and grain definitions.
- **`powerbi/dax_measures.md`:** Production DAX formulas (Total Orders, Delivered GMV, AOV, MoM Growth %, On-Time Delivery Rate %, Low-Rating Rate %, Repeat Customer Rate).
- **`powerbi/report_specification.md`:** Page wireframes, visual slicers, design system, and database connection instructions.

---

## 11. Project Structure
```
ecommerce-business-intelligence/
├── app.py                           # Streamlit main entrypoint & executive portal
├── requirements.txt                 # Pinned project dependencies
├── .env.example                     # Environment template (secrets outside git)
├── .gitignore                       # Clean git exclusion rules
├── pytest.ini                       # Test configuration & pythonpath
├── docker-compose.yml               # PostgreSQL 16 Alpine container setup
├── README.md                        # Documentation
├── config/
│   ├── __init__.py
│   └── settings.py                  # Path resolver, database configs & constants
├── src/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── download_data.py         # Multi-source dataset resolver
│   │   └── load_raw_data.py         # Raw CSV loader & initial profiling
│   ├── preprocessing/
│   │   ├── clean_data.py            # Normalization, translation, deduplication
│   │   └── feature_engineering.py   # RFM scoring, delivery delay metrics, cohorts
│   ├── database/
│   │   ├── connection.py            # Unified PostgreSQL & DuckDB engine manager
│   │   ├── schema.sql               # Star schema DDL, constraints & views
│   │   └── load_database.py         # Idempotent ETL pipeline orchestration
│   ├── analytics/
│   │   ├── sales_analysis.py        # Executive KPIs, monthly trends, Pareto
│   │   ├── customer_analysis.py     # RFM segmentation, K-Means clustering, cohorts
│   │   ├── delivery_analysis.py     # Logistics lead-times, state latency, SLAs
│   │   ├── review_analysis.py       # CSAT rating distributions & category scores
│   │   ├── statistical_analysis.py  # Welch's t-test, Mann-Whitney U, Cohen's d
│   │   └── forecasting.py           # Holt-Winters vs Naive order volume forecast
│   ├── validation/
│   │   ├── data_quality.py          # 21 Automated integrity assertion checks
│   │   └── reconciliation.py        # Source-to-target financial audit
│   └── dashboard/
│       └── ui_components.py         # Executive CSS theme, KPI cards, Plotly layout
├── sql/
│   ├── sales_kpis.sql               # Executive KPIs & explicit denominators
│   ├── monthly_trends.sql           # Monthly volume, GMV, MoM growth & 3-mo MA
│   ├── product_analysis.sql         # Category Pareto & top products per category
│   ├── customer_cohorts.sql         # Cohort acquisition & monthly retention matrix
│   ├── rfm_analysis.sql             # Customer RFM quintiles & segment classification
│   ├── delivery_performance.sql     # On-time rates & state delivery latency
│   ├── seller_rankings.sql          # Seller leaderboard with volume threshold
│   ├── review_analysis.sql          # Rating distribution & delay bracket impact
│   ├── geographic_analysis.sql      # Demand concentration & trade flow balance
│   └── order_status_analysis.sql    # Order status lifecycle & payment installments
├── pages/
│   ├── 1_Executive_Overview.py      # Sales KPIs, trends, Pareto, geographic map
│   ├── 2_Customer_Intelligence.py   # RFM matrix, K-Means, cohorts, customer table
│   ├── 3_Delivery_Analytics.py      # Logistics lead-times, delay histogram, sellers
│   └── 4_Customer_Experience.py     # CSAT ratings, statistical tests, forecasting
├── tests/
│   ├── test_data_quality.py         # Cleaning & duplicate handling unit tests
│   ├── test_metrics.py              # KPI formula & denominator boundary tests
│   ├── test_customer_features.py    # RFM & cohort arithmetic unit tests
│   └── test_sql_reconciliation.py   # Database row count & financial total matches
├── notebooks/
│   ├── 01_data_audit.ipynb          # Exploratory raw data audit notebook
│   └── 02_exploratory_analysis.ipynb # Advanced SQL & statistical analysis notebook
├── powerbi/
│   ├── data_model.md                # Star schema diagram & relationship rules
│   ├── dax_measures.md              # Canonical DAX formulas repository
│   └── report_specification.md      # Visual layout wireframes & slicer guides
└── docs/
    ├── architecture.md              # System design, Kimball model, scalability
    ├── data_dictionary.md           # Schema column definitions, data types, keys
    └── business_findings.md         # Rigorous empirical findings & business insights
```

---

## 12. Limitations & Methodological Disclosures
1. **Profit Calculation Excluded:** Cost of Goods Sold (COGS), seller marketing expenses, platform commissions, and warehouse handling fees are not present in the public dataset. Gross Merchandise Value (GMV) is tracked, but net profit is not calculated.
2. **Observational Association vs Causality:** Delivery delays correlate strongly with low review scores ($p < 0.001$, Cohen's $d = 1.34$). However, observational data cannot isolate whether delays are the sole causal driver without controlling for product manufacturing defects or seller communication responsiveness.
3. **Historical Snapshot Recency:** Customer RFM Recency is evaluated relative to **October 18, 2018** (the dataset snapshot cutoff). Segments reflect historical behavior during the 2016-2018 operating window.
