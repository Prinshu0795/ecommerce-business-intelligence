# Technical Data Dictionary

This document details all tables, columns, data types, nullability, primary keys, and foreign keys in the dimensional star schema.

---

## 1. Dimension Tables

### `dim_date`
*Grain: Exactly 1 row per calendar day (2016-01-01 to 2019-12-31).*

| Column | Data Type | Nullable | Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `date_id` | INT | No | PK | Surrogate key in YYYYMMDD format (e.g. 20180101) |
| `full_date` | DATE | No | | Full calendar date |
| `year` | INT | No | | Four-digit calendar year (e.g. 2018) |
| `quarter` | INT | No | | Calendar quarter (1 to 4) |
| `month` | INT | No | | Month number (1 to 12) |
| `month_name` | VARCHAR(20) | No | | Full English month name (e.g. January) |
| `day` | INT | No | | Day of month (1 to 31) |
| `day_of_week` | INT | No | | Day of week number (1=Monday, 7=Sunday) |
| `day_name` | VARCHAR(20) | No | | English day name (e.g. Monday) |
| `is_weekend` | INT | No | | Binary flag: 1 if Saturday/Sunday, else 0 |
| `year_month` | VARCHAR(7) | No | | Standard period identifier (YYYY-MM) |
| `year_quarter` | VARCHAR(7) | No | | Period quarter identifier (YYYY-QX) |

---

### `dim_geography`
*Grain: 1 row per Brazilian postal zip code prefix (centroid coordinates).*

| Column | Data Type | Nullable | Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `zip_code_prefix` | INT | No | PK | 5-digit Brazilian zip code prefix |
| `latitude` | DOUBLE PRECISION | Yes | | Mean geographic latitude within postal prefix |
| `longitude` | DOUBLE PRECISION | Yes | | Mean geographic longitude within postal prefix |
| `city` | VARCHAR(100) | Yes | | Dominant municipality/city name |
| `state` | VARCHAR(5) | Yes | | Two-letter Brazilian federal state abbreviation |

---

### `dim_customer`
*Grain: 1 row per unique order-level customer token.*

| Column | Data Type | Nullable | Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `customer_id` | VARCHAR(50) | No | PK | Order-scoped customer identifier token |
| `customer_unique_id` | VARCHAR(50) | No | | Unique human identifier across multiple orders |
| `customer_zip_code_prefix` | INT | Yes | FK | References `dim_geography.zip_code_prefix` |
| `customer_city` | VARCHAR(100) | Yes | | Customer registered municipality |
| `customer_state` | VARCHAR(5) | Yes | | Customer two-letter state code |

---

### `dim_product`
*Grain: 1 row per unique product SKU.*

| Column | Data Type | Nullable | Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `product_id` | VARCHAR(50) | No | PK | Unique product identifier hash |
| `product_category_name` | VARCHAR(100) | Yes | | Original Portuguese category name |
| `product_category_name_english` | VARCHAR(100) | Yes | | Standardized English translated category |
| `product_name_lenght` | DOUBLE PRECISION | Yes | | Length of product title characters |
| `product_description_lenght` | DOUBLE PRECISION | Yes | | Length of description text characters |
| `product_photos_qty` | DOUBLE PRECISION | Yes | | Number of published product photos |
| `product_weight_g` | DOUBLE PRECISION | Yes | | Product package weight in grams |
| `product_length_cm` | DOUBLE PRECISION | Yes | | Package length in centimeters |
| `product_height_cm` | DOUBLE PRECISION | Yes | | Package height in centimeters |
| `product_width_cm` | DOUBLE PRECISION | Yes | | Package width in centimeters |

---

### `dim_seller`
*Grain: 1 row per merchant / marketplace vendor.*

| Column | Data Type | Nullable | Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `seller_id` | VARCHAR(50) | No | PK | Unique merchant identifier hash |
| `seller_zip_code_prefix` | INT | Yes | FK | References `dim_geography.zip_code_prefix` |
| `seller_city` | VARCHAR(100) | Yes | | Merchant municipality / warehouse location |
| `seller_state` | VARCHAR(5) | Yes | | Merchant two-letter state code |

---

## 2. Fact Tables

### `fact_order`
*Grain: Exactly 1 row per customer order (Header Grain).*

| Column | Data Type | Nullable | Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `order_id` | VARCHAR(50) | No | PK | Unique purchase order identifier |
| `customer_id` | VARCHAR(50) | No | FK | References `dim_customer.customer_id` |
| `order_status` | VARCHAR(30) | No | | Lifecycle status (`delivered`, `canceled`, etc.) |
| `order_purchase_timestamp` | TIMESTAMP | No | | Timestamp when customer placed purchase |
| `order_approved_at` | TIMESTAMP | Yes | | Timestamp when payment was authorized |
| `order_delivered_carrier_date` | TIMESTAMP | Yes | | Timestamp when seller dispatched to carrier |
| `order_delivered_customer_date` | TIMESTAMP | Yes | | Timestamp when customer received package |
| `order_estimated_delivery_date` | TIMESTAMP | Yes | | Promised SLA estimated delivery date |
| `order_purchase_date_id` | INT | Yes | FK | References `dim_date.date_id` |
| `item_count` | INT | No | | Total number of line items in order |
| `merchandise_value` | NUMERIC(12, 2) | No | | Sum of product item prices (BRL) |
| `freight_value` | NUMERIC(12, 2) | No | | Sum of shipping freight charges (BRL) |
| `total_order_value` | NUMERIC(12, 2) | No | | Merchandise value + Freight value (BRL) |
| `total_payment_value` | NUMERIC(12, 2) | No | | Sum of all payment installments recorded (BRL) |
| `delivery_duration_days` | DOUBLE PRECISION | Yes | | Elapsed days from purchase to doorstep |
| `carrier_duration_days` | DOUBLE PRECISION | Yes | | Elapsed days from carrier dispatch to doorstep |
| `estimated_duration_days` | DOUBLE PRECISION | Yes | | Expected transit days promised at checkout |
| `approval_duration_hours` | DOUBLE PRECISION | Yes | | Elapsed hours from order placement to payment approval |
| `delivery_delay_days` | DOUBLE PRECISION | Yes | | Actual delivery date minus Estimated delivery date (Days) |
| `is_delivered_on_time` | INT | Yes | | Binary flag: 1 if on-time/early, 0 if late, NULL if missing dates |
| `delivery_status_category` | VARCHAR(50) | Yes | | Descriptive delivery classification |
| `review_score` | DOUBLE PRECISION | Yes | | Mean customer review score (1.0 to 5.0) |

---

### `fact_order_item`
*Grain: 1 row per physical product item within an order.*

| Column | Data Type | Nullable | Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `order_id` | VARCHAR(50) | No | PK, FK | References `fact_order.order_id` |
| `order_item_id` | INT | No | PK | Item sequence number within order (1, 2, 3...) |
| `product_id` | VARCHAR(50) | No | FK | References `dim_product.product_id` |
| `seller_id` | VARCHAR(50) | No | FK | References `dim_seller.seller_id` |
| `shipping_limit_date` | TIMESTAMP | Yes | | Seller deadline to hand over order to carrier |
| `price` | NUMERIC(10, 2) | No | | Item purchase price in Brazilian Real (BRL) |
| `freight_value` | NUMERIC(10, 2) | No | | Item shipping freight charge in BRL |
| `total_item_value` | NUMERIC(10, 2) | No | | Item price + item freight value |

---

### `fact_payment`
*Grain: 1 row per installment payment transaction.*

| Column | Data Type | Nullable | Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `order_id` | VARCHAR(50) | No | PK, FK | References `fact_order.order_id` |
| `payment_sequential` | INT | No | PK | Installment payment sequence (1, 2, 3...) |
| `payment_type` | VARCHAR(30) | No | | Method (`credit_card`, `boleto`, `voucher`, `debit_card`) |
| `payment_installments` | INT | No | | Number of financing installment months |
| `payment_value` | NUMERIC(12, 2) | No | | Monetary amount charged in this sequence (BRL) |

---

### `fact_review`
*Grain: 1 row per customer review survey.*

| Column | Data Type | Nullable | Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `review_id` | VARCHAR(50) | No | PK | Unique customer survey identifier |
| `order_id` | VARCHAR(50) | No | PK, FK | References `fact_order.order_id` |
| `review_score` | INT | No | | Customer satisfaction rating (1 to 5 stars) |
| `review_comment_title` | TEXT | Yes | | Customer submitted review title |
| `review_comment_message` | TEXT | Yes | | Customer submitted text feedback message |
| `review_creation_date` | TIMESTAMP | Yes | | Timestamp when survey was issued to customer |
| `review_answer_timestamp` | TIMESTAMP | Yes | | Timestamp when customer responded to survey |
