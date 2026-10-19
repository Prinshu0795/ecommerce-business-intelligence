-- ============================================================================
-- E-Commerce Business Intelligence & Customer Analytics Platform
-- Star Schema Dimensional Relational Data Model
-- Target Dialect: PostgreSQL 14+ (Standard ANSI SQL Compatible)
-- ============================================================================

-- Drop views if existing
DROP VIEW IF EXISTS vw_customer_rfm;
DROP VIEW IF EXISTS vw_seller_kpis;
DROP VIEW IF EXISTS vw_monthly_sales;
DROP VIEW IF EXISTS vw_order_summary;

-- Drop fact tables first (referential dependencies)
DROP TABLE IF EXISTS fact_review;
DROP TABLE IF EXISTS fact_payment;
DROP TABLE IF EXISTS fact_order_item;
DROP TABLE IF EXISTS fact_order;

-- Drop dimension tables
DROP TABLE IF EXISTS dim_seller;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_geography;
DROP TABLE IF EXISTS dim_date;

-- ============================================================================
-- 1. DIMENSION TABLES
-- ============================================================================

-- Date Dimension
-- Grain: One row per calendar day
CREATE TABLE dim_date (
    date_id INT PRIMARY KEY,                       -- e.g. 20170101
    full_date DATE NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day INT NOT NULL,
    day_of_week INT NOT NULL,                      -- 1=Monday, 7=Sunday
    day_name VARCHAR(20) NOT NULL,
    is_weekend INT NOT NULL,                       -- 1 if Saturday/Sunday else 0
    year_month VARCHAR(7) NOT NULL,                -- YYYY-MM
    year_quarter VARCHAR(7) NOT NULL               -- YYYY-QX
);

CREATE INDEX idx_dim_date_full_date ON dim_date(full_date);
CREATE INDEX idx_dim_date_year_month ON dim_date(year_month);

-- Geography Dimension
-- Grain: One row per Brazilian zip code prefix (deduplicated centroid coordinates)
CREATE TABLE dim_geography (
    zip_code_prefix INT PRIMARY KEY,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    city VARCHAR(100),
    state VARCHAR(5)
);

CREATE INDEX idx_dim_geography_state ON dim_geography(state);
CREATE INDEX idx_dim_geography_city ON dim_geography(city);

-- Customer Dimension
-- Grain: One row per unique order customer token (links to unique person)
CREATE TABLE dim_customer (
    customer_id VARCHAR(50) PRIMARY KEY,           -- Order-scoped customer token
    customer_unique_id VARCHAR(50) NOT NULL,      -- Unique real person identifier
    customer_zip_code_prefix INT,
    customer_city VARCHAR(100),
    customer_state VARCHAR(5),
    CONSTRAINT fk_cust_geo FOREIGN KEY (customer_zip_code_prefix) 
        REFERENCES dim_geography(zip_code_prefix) ON DELETE SET NULL
);

CREATE INDEX idx_dim_customer_unique_id ON dim_customer(customer_unique_id);
CREATE INDEX idx_dim_customer_state ON dim_customer(customer_state);

-- Product Dimension
-- Grain: One row per unique product SKU
CREATE TABLE dim_product (
    product_id VARCHAR(50) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_category_name_english VARCHAR(100),
    product_name_lenght DOUBLE PRECISION,
    product_description_lenght DOUBLE PRECISION,
    product_photos_qty DOUBLE PRECISION,
    product_weight_g DOUBLE PRECISION,
    product_length_cm DOUBLE PRECISION,
    product_height_cm DOUBLE PRECISION,
    product_width_cm DOUBLE PRECISION
);

CREATE INDEX idx_dim_product_category ON dim_product(product_category_name_english);

-- Seller Dimension
-- Grain: One row per merchant / marketplace seller
CREATE TABLE dim_seller (
    seller_id VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix INT,
    seller_city VARCHAR(100),
    seller_state VARCHAR(5),
    CONSTRAINT fk_seller_geo FOREIGN KEY (seller_zip_code_prefix) 
        REFERENCES dim_geography(zip_code_prefix) ON DELETE SET NULL
);

CREATE INDEX idx_dim_seller_state ON dim_seller(seller_state);

-- ============================================================================
-- 2. FACT TABLES
-- ============================================================================

-- Order Fact Table
-- Grain: One row per order (Header Grain)
-- Prevents Cartesian multiplication when aggregating sales, delays, and statuses
CREATE TABLE fact_order (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    order_status VARCHAR(30) NOT NULL,
    order_purchase_timestamp TIMESTAMP NOT NULL,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP,
    order_purchase_date_id INT,                    -- FK to dim_date
    item_count INT DEFAULT 0,
    merchandise_value NUMERIC(12, 2) DEFAULT 0.00,
    freight_value NUMERIC(12, 2) DEFAULT 0.00,
    total_order_value NUMERIC(12, 2) DEFAULT 0.00,
    total_payment_value NUMERIC(12, 2) DEFAULT 0.00,
    delivery_duration_days DOUBLE PRECISION,
    carrier_duration_days DOUBLE PRECISION,
    estimated_duration_days DOUBLE PRECISION,
    approval_duration_hours DOUBLE PRECISION,
    delivery_delay_days DOUBLE PRECISION,          -- Delivered - Estimated (days)
    is_delivered_on_time INT,                      -- 1 if on-time, 0 if late, NULL if missing
    delivery_status_category VARCHAR(50),
    review_score DOUBLE PRECISION,                 -- Average review score for this order
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) 
        REFERENCES dim_customer(customer_id),
    CONSTRAINT fk_order_date FOREIGN KEY (order_purchase_date_id) 
        REFERENCES dim_date(date_id)
);

CREATE INDEX idx_fact_order_customer ON fact_order(customer_id);
CREATE INDEX idx_fact_order_status ON fact_order(order_status);
CREATE INDEX idx_fact_order_purchase_ts ON fact_order(order_purchase_timestamp);
CREATE INDEX idx_fact_order_date_id ON fact_order(order_purchase_date_id);
CREATE INDEX idx_fact_order_ontime ON fact_order(is_delivered_on_time);

-- Order Items Fact Table
-- Grain: One row per line item within an order
CREATE TABLE fact_order_item (
    order_id VARCHAR(50) NOT NULL,
    order_item_id INT NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    seller_id VARCHAR(50) NOT NULL,
    shipping_limit_date TIMESTAMP,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    freight_value NUMERIC(10, 2) NOT NULL CHECK (freight_value >= 0),
    total_item_value NUMERIC(10, 2),
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_item_order FOREIGN KEY (order_id) 
        REFERENCES fact_order(order_id) ON DELETE CASCADE,
    CONSTRAINT fk_item_product FOREIGN KEY (product_id) 
        REFERENCES dim_product(product_id),
    CONSTRAINT fk_item_seller FOREIGN KEY (seller_id) 
        REFERENCES dim_seller(seller_id)
);

CREATE INDEX idx_fact_order_item_product ON fact_order_item(product_id);
CREATE INDEX idx_fact_order_item_seller ON fact_order_item(seller_id);
CREATE INDEX idx_fact_order_item_order ON fact_order_item(order_id);

-- Payment Fact Table
-- Grain: One row per payment transaction/installment sequence
CREATE TABLE fact_payment (
    order_id VARCHAR(50) NOT NULL,
    payment_sequential INT NOT NULL,
    payment_type VARCHAR(30) NOT NULL,
    payment_installments INT NOT NULL DEFAULT 1,
    payment_value NUMERIC(12, 2) NOT NULL CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payment_order FOREIGN KEY (order_id) 
        REFERENCES fact_order(order_id) ON DELETE CASCADE
);

CREATE INDEX idx_fact_payment_order ON fact_payment(order_id);
CREATE INDEX idx_fact_payment_type ON fact_payment(payment_type);

-- Review Fact Table
-- Grain: One row per review submission
CREATE TABLE fact_review (
    review_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    review_score INT NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (review_id, order_id),
    CONSTRAINT fk_review_order FOREIGN KEY (order_id) 
        REFERENCES fact_order(order_id) ON DELETE CASCADE
);

CREATE INDEX idx_fact_review_order ON fact_review(order_id);
CREATE INDEX idx_fact_review_score ON fact_review(review_score);

-- ============================================================================
-- 3. ANALYTICAL VIEWS
-- ============================================================================

-- View: Order Summary
-- Denormalizes order facts with customer location, primary dates, and review metrics
CREATE VIEW vw_order_summary AS
SELECT 
    o.order_id,
    o.order_status,
    o.order_purchase_timestamp,
    d.year,
    d.month,
    d.year_month,
    c.customer_unique_id,
    c.customer_state,
    c.customer_city,
    o.item_count,
    o.merchandise_value,
    o.freight_value,
    o.total_order_value,
    o.total_payment_value,
    o.delivery_duration_days,
    o.delivery_delay_days,
    o.is_delivered_on_time,
    o.delivery_status_category,
    o.review_score
FROM fact_order o
JOIN dim_customer c ON o.customer_id = c.customer_id
LEFT JOIN dim_date d ON o.order_purchase_date_id = d.date_id;

-- View: Monthly Sales KPIs (Delivered Orders baseline)
CREATE VIEW vw_monthly_sales AS
SELECT 
    d.year_month,
    d.year,
    d.month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
    SUM(CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END) AS canceled_orders,
    ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN o.merchandise_value ELSE 0 END), 2) AS delivered_merchandise_value,
    ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN o.freight_value ELSE 0 END), 2) AS delivered_freight_value,
    ROUND(
        SUM(CASE WHEN o.order_status = 'delivered' THEN o.merchandise_value ELSE 0 END) / 
        NULLIF(SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END), 0), 
        2
    ) AS delivered_aov,
    ROUND(
        AVG(CASE WHEN o.order_status = 'delivered' THEN o.is_delivered_on_time END) * 100.0, 
        2
    ) AS on_time_delivery_rate_pct,
    ROUND(AVG(o.review_score), 2) AS avg_review_score
FROM fact_order o
JOIN dim_date d ON o.order_purchase_date_id = d.date_id
GROUP BY d.year_month, d.year, d.month;

-- View: Seller Performance KPIs
CREATE VIEW vw_seller_kpis AS
SELECT 
    s.seller_id,
    s.seller_state,
    s.seller_city,
    COUNT(DISTINCT oi.order_id) AS total_orders,
    COUNT(oi.order_item_id) AS total_items_sold,
    ROUND(SUM(oi.price), 2) AS total_merchandise_value,
    ROUND(AVG(oi.price), 2) AS avg_item_price,
    ROUND(AVG(o.is_delivered_on_time) * 100.0, 2) AS on_time_delivery_rate_pct,
    ROUND(AVG(o.delivery_delay_days), 2) AS avg_delivery_delay_days,
    ROUND(AVG(o.review_score), 2) AS avg_seller_review_score
FROM dim_seller s
JOIN fact_order_item oi ON s.seller_id = oi.seller_id
JOIN fact_order o ON oi.order_id = o.order_id
GROUP BY s.seller_id, s.seller_state, s.seller_city;
