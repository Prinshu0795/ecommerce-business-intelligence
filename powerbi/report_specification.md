# Power BI Dashboard Report Specification

## 1. Design System & Theme Standards
- **Page Size:** 16:9 widescreen (1920 x 1080 px).
- **Background:** Flat light neutral (`#F8FAFC`).
- **Card Background:** Pure white (`#FFFFFF`) with 1px border (`#E2E8F0`) and 4px corner radius.
- **Color Palette:**
  - Primary Brand: Navy (`#1E3A8A`)
  - Secondary: Ocean Blue (`#0284C7`)
  - Positive/On-Time: Forest Green (`#16A34A`)
  - Warning/Neutral: Amber (`#F59E0B`)
  - Danger/Delayed: Crimson (`#DC2626`)
- **Typography:**
  - Titles: Segoe UI / Inter Bold (18-20 pt)
  - KPI Values: Segoe UI Semibold (28-32 pt)
  - Body & Axis Labels: Segoe UI Regular (9-10 pt)

---

## 2. Multi-Page Layout Blueprints

### Page 1: Executive Overview
- **Top Bar:** Page Title, Global Date Slicer (`dim_date[full_date]`), Customer State Slicer (`dim_customer[customer_state]`).
- **KPI Ribbon (Cards):**
  1. `[Delivered GMV]` (Formatted as Currency R$)
  2. `[Delivered Orders]`
  3. `[Delivered AOV]`
  4. `[On-Time Delivery Rate %]`
  5. `[Cancellation Rate %]`
- **Row 1 Visuals:**
  - **Left:** Line & Clustered Column Chart (`dim_date[year_month]`), Columns: `[Delivered GMV]`, Line: `[MoM GMV Growth %]`.
  - **Right:** Donut Chart (`fact_order[order_status]`) showing order lifecycle distribution.
- **Row 2 Visuals:**
  - **Left:** Pareto Chart (`dim_product[product_category_name_english]`), Bars: `[Delivered GMV]`, Line: `[Cumulative Share %]`.
  - **Right:** Filled Choropleth Map or Horizontal Bar Chart by Brazilian Customer State (`dim_customer[customer_state]`).

### Page 2: Customer Intelligence
- **KPI Ribbon:** `[Unique Customers]`, `[Repeat Customer Count]`, `[Repeat Purchase Rate %]`, `[Delivered AOV]`.
- **Visuals:**
  - **Treemap / Donut:** Customer distribution across RFM Segments (`Champions`, `Loyal`, `At Risk`, `Hibernating`).
  - **Bar Chart:** Total Delivered GMV by RFM Segment.
  - **Matrix Visual:** Monthly Customer Cohort Retention Matrix (`Cohort Month` in Rows, `Cohort Index` in Columns, Values: `Retention Rate %` with gradient color conditional formatting).
  - **Drill-Through Table:** Customer lookup with `customer_unique_id`, `customer_state`, `frequency`, `monetary`, `recency_days`, and `rfm_segment`.

### Page 3: Delivery Analytics
- **KPI Ribbon:** `[On-Time Delivery Rate %]`, `[Late Delivery Rate %]`, `[Avg Delivery Duration Days]`, `[Avg Delay When Late]`.
- **Visuals:**
  - **Funnel / Stacked Bar:** Lead time decomposition (`Approval`, `Carrier Transit`, `Total Delivery`).
  - **Histogram:** Distribution of delivery delay days (bins: 2 days) with a vertical reference line at 0 days.
  - **Bar Chart:** Average delivery duration by Customer State (`customer_state`), color-coded by on-time percentage.
  - **Leaderboard Table:** Seller performance ranked by order volume with seller state, fulfilled orders, on-time rate %, and CSAT rating.

### Page 4: Customer Experience & Reviews
- **KPI Ribbon:** `[Avg Review Score]`, `[5-Star Rating Rate %]`, `[Low-Rating Rate %]`, `[Written Comments Rate %]`.
- **Visuals:**
  - **Column Chart:** Review Score distribution (1, 2, 3, 4, 5 stars) with color-coded sentiment.
  - **Clustered Column & Line:** Delivery Delay Brackets on X-axis, Bars: `[Avg Review Score]`, Line: `[Low Rating Rate %]`.
  - **Table / Heatmap:** Product category satisfaction table showing average score and low-rating rate sorted by review volume.

---

## 3. Database Connection Instructions for Power BI
1. Open Power BI Desktop.
2. Select **Get Data** -> **PostgreSQL Database** (or ODBC -> DuckDB).
3. Enter Server: `localhost:5432`, Database: `olist_bi`.
4. Data Connectivity mode: Select **Import** (or **DirectQuery**).
5. Enter user credentials (`postgres` / `postgres`).
6. Select tables: `dim_date`, `dim_customer`, `dim_product`, `dim_seller`, `dim_geography`, `fact_order`, `fact_order_item`, `fact_payment`, `fact_review`.
7. Verify table relationships match the star-schema diagram.
8. Create a dedicated `_Measures` table and paste the canonical DAX measures from `powerbi/dax_measures.md`.
