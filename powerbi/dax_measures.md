# Canonical DAX Measure Repository

All measures are designed to ensure numerical reconciliation with canonical SQL KPI definitions.

---

### 1. Volume & Fulfillment Measures

#### Total Orders
```dax
Total Orders = 
DISTINCTCOUNT(fact_order[order_id])
```

#### Delivered Orders
```dax
Delivered Orders = 
CALCULATE(
    DISTINCTCOUNT(fact_order[order_id]),
    fact_order[order_status] = "delivered"
)
```

#### Canceled Orders
```dax
Canceled Orders = 
CALCULATE(
    DISTINCTCOUNT(fact_order[order_id]),
    fact_order[order_status] = "canceled"
)
```

#### Cancellation Rate %
```dax
Cancellation Rate % = 
DIVIDE([Canceled Orders], [Total Orders], 0) * 100
```

---

### 2. Monetary & Commercial Measures

#### Delivered Merchandise Value (GMV)
```dax
Delivered GMV = 
CALCULATE(
    SUM(fact_order_item[price]),
    fact_order[order_status] = "delivered"
)
```

#### Delivered Freight Value
```dax
Delivered Freight = 
CALCULATE(
    SUM(fact_order_item[freight_value]),
    fact_order[order_status] = "delivered"
)
```

#### Delivered Average Order Value (AOV)
```dax
Delivered AOV = 
DIVIDE([Delivered GMV], [Delivered Orders], 0)
```

#### Previous Month Delivered GMV
```dax
Previous Month GMV = 
CALCULATE(
    [Delivered GMV],
    DATEADD(dim_date[full_date], -1, MONTH)
)
```

#### MoM GMV Growth %
```dax
MoM GMV Growth % = 
DIVIDE([Delivered GMV] - [Previous Month GMV], [Previous Month GMV], 0) * 100
```

---

### 3. Logistics & SLA Compliance Measures

#### On-Time Delivered Orders
```dax
On-Time Orders = 
CALCULATE(
    DISTINCTCOUNT(fact_order[order_id]),
    fact_order[order_status] = "delivered",
    fact_order[is_delivered_on_time] = 1
)
```

#### Evaluable Delivered Orders
```dax
Evaluable Delivered Orders = 
CALCULATE(
    DISTINCTCOUNT(fact_order[order_id]),
    fact_order[order_status] = "delivered",
    NOT(ISBLANK(fact_order[is_delivered_on_time]))
)
```

#### On-Time Delivery Rate %
```dax
On-Time Delivery Rate % = 
DIVIDE([On-Time Orders], [Evaluable Delivered Orders], 0) * 100
```

#### Average Delivery Duration (Days)
```dax
Avg Delivery Duration Days = 
CALCULATE(
    AVERAGE(fact_order[delivery_duration_days]),
    fact_order[order_status] = "delivered"
)
```

---

### 4. Customer Satisfaction & Retention Measures

#### Average Review Score
```dax
Avg Review Score = 
AVERAGE(fact_review[review_score])
```

#### Low-Rating Rate % (1 & 2 Stars)
```dax
Low Rating Rate % = 
VAR LowReviews = CALCULATE(COUNTROWS(fact_review), fact_review[review_score] IN {1, 2})
VAR TotalReviews = COUNTROWS(fact_review)
RETURN
DIVIDE(LowReviews, TotalReviews, 0) * 100
```

#### Repeat Customer Count
```dax
Repeat Customer Count = 
COUNTROWS(
    FILTER(
        VALUES(dim_customer[customer_unique_id]),
        CALCULATE(DISTINCTCOUNT(fact_order[order_id]), fact_order[order_status] = "delivered") >= 2
    )
)
```

#### Repeat Purchase Rate %
```dax
Repeat Purchase Rate % = 
VAR TotalUniqueCustomers = DISTINCTCOUNT(dim_customer[customer_unique_id])
RETURN
DIVIDE([Repeat Customer Count], TotalUniqueCustomers, 0) * 100
```
