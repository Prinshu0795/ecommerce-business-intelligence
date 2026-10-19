# Executive Business Intelligence & Empirical Findings Report

**Platform:** Brazilian E-Commerce Public Dataset by Olist (99,441 Real Records)  
**Evaluation Snapshot:** October 18, 2018  
**Author:** Senior Analytics Engineering & BI Team  

---

## 1. Executive Summary
This report presents empirical findings derived strictly from the complete Olist relational database. All statistics, tests, and metrics are computed from real records without estimation or synthetic inflation.

```
Total Eligible Orders:            99,441
Delivered Orders:                 96,478 (97.02%)
Canceled Orders:                     625 (0.63%)
Delivered Merchandise Value (GMV): R$ 13,221,498.11
Delivered Freight Expenditure:    R$  2,198,275.64 (16.63% of GMV)
Delivered Average Order Value:    R$     137.04
Overall On-Time Delivery Rate:     91.89%
Mean Customer Review Score:         4.15 ★
Repeat Purchase Rate:               3.12%
```

---

## 2. Finding 1: The One-Time Purchase Bottleneck & Customer Lifetime Value
### Method
Customer aggregation at the `customer_unique_id` grain across all completed delivered orders, tracking multi-order frequency and total monetary spend.

### Evidence
- **Total Unique Customers:** 96,096 distinct individuals.
- **One-Time Buyers:** 93,099 customers (**96.88%**).
- **Repeat Buyers (>=2 Orders):** 2,997 customers (**3.12%**).
- **Average Spend:**
  - One-time buyers: **R$ 133.05**
  - Repeat buyers: **R$ 261.27** (+96.4% higher CLV).
- **Cohort Month 1 Retention:** Across all acquisition cohorts from Jan 2017 to Aug 2018, Month-1 retention never exceeded **0.8%**, decaying toward 0.2% by Month 6.

### Business Interpretation
Olist functions almost exclusively as an unbranded acquisition funnel rather than a recurring consumer destination. However, repeat buyers deliver nearly double the gross merchandise value. Capturing just a 2% incremental increase in repeat purchases would generate over R$ 500,000 in high-margin marketplace GMV without incremental customer acquisition costs (CAC).

### Strategic Recommendations
1. **Automated Post-Purchase Re-Engagement:** Trigger automated category-specific consumable replenishment emails 30 to 60 days post-delivery.
2. **Category Cross-Selling Programs:** Offer seller-funded cross-category discounts (e.g., Bed & Bath purchasers receiving a voucher for Home Decor).

### Limitations
Dataset lacks direct marketing campaign attribution, email engagement logs, and advertising spend data, preventing direct ROI calculation on historical acquisition channels.

---

## 3. Finding 2: Severe Customer Satisfaction Degradation from Delivery Delays
### Method
Two-sample Welch's t-test, Mann-Whitney U test, Cohen's d effect size calculation, and Spearman rank correlation comparing customer review scores across On-Time ($N_1 = 88,649$) versus Delayed ($N_2 = 7,827$) deliveries.

### Evidence
- **On-Time Mean Review Score:** **4.29 ★** ($\pm 1.20$)
- **Delayed Mean Review Score:** **2.57 ★** ($\pm 1.63$)
- **Score Difference ($\Delta$):** **+1.73 Stars** (95% CI: `[+1.69, +1.76]`)
- **Statistical Significance:** Welch's $t = 92.4$, $p < 0.001$; Mann-Whitney $p < 0.001$.
- **Effect Size:** Cohen's $d = 1.34$ (Large practical significance).
- **Severe Dissatisfaction (Scores 1-2):**
  - On-time orders: **8.4%**
  - Delayed orders: **55.4%** (a **6.6x escalation** in detractor probability).
- **Delay Severity Threshold:** Customer rating drops precipitously once an order is delayed by even 1 to 3 days (mean rating drops from 4.29 to 2.87 ★).

### Business Interpretation
Delivery delays represent the primary operational driver of customer dissatisfaction on the platform. More than half of all delayed orders produce a 1- or 2-star detractor review, directly depressing repeat purchase likelihood and brand reputation.

### Strategic Recommendations
1. **Proactive Delay Notifications:** Automatically notify customers 48 hours before an SLA breach occurs with an updated tracking estimate and a courtesy credit or freight refund.
2. **Seller Carrier SLA Penalties:** Enforce dispatch SLAs on merchants with late-handover rates exceeding 15%.

### Limitations
This observational association does not prove that delivery delay is the sole causal factor. Substandard product packaging, damaged items, or poor seller customer support may co-occur with logistical bottlenecks.

---

## 4. Finding 3: Regional Logistical Disparities & Freight Burden
### Method
Geographic aggregation of customer order delivery durations, freight-to-merchandise ratios, and destination state SLA compliance.

### Evidence
- **Southeast Concentration:** São Paulo (SP), Rio de Janeiro (RJ), and Minas Gerais (MG) account for over **65%** of national orders.
- **São Paulo Logistics Hub:** SP orders achieve an average transit time of only **8.3 days** with a **95.2%** on-time compliance rate and average freight cost of R$ 15.15.
- **Northern Frontier Latency:** Customers in the North face severe delivery lead times:
  - Roraima (RR): **28.9 days** average transit
  - Amapá (AP): **25.7 days** average transit
  - Amazonas (AM): **25.9 days** average transit
  - Maranhão (MA): **21.1 days** average transit
- **National Freight Burden:** Total freight value equals **R$ 2,198,275.64**, representing **16.63%** of merchandise value. For long-haul inter-state shipments into the North and Northeast, freight charges frequently exceed 30% of basket price.

### Business Interpretation
Because marketplace sellers are heavily clustered in São Paulo and the South, national long-haul shipping creates an asymmetric barrier to customer acquisition and retention outside the Southeast corridor.

### Strategic Recommendations
1. **Regional Fulfillment Hubs:** Partner with 3PL logistics hubs in Northeast metropolitan centers (e.g., Recife, Salvador) to forward-position high-velocity Pareto inventory.
2. **Tiered Shipping SLAs:** Adjust promised delivery estimate windows for outer states to prevent false SLA breaches and customer frustration.

---

## 5. Finding 4: Product Category Pareto Concentration
### Method
Category revenue aggregation with cumulative share calculations (Pareto 80/20 analysis).

### Evidence
- Out of 71 distinct product categories, the top 10 categories account for **64.2%** of total delivered GMV:
  1. *Health & Beauty:* R$ 1,258,681.34 (9.52% of GMV)
  2. *Watches & Gifts:* R$ 1,205,005.68 (9.11% of GMV)
  3. *Bed, Bath & Table:* R$ 1,036,988.70 (7.84% of GMV)
  4. *Sports & Leisure:* R$ 988,048.97 (7.47% of GMV)
  5. *Computers & Accessories:* R$ 911,958.24 (6.90% of GMV)
- The bottom 40 categories combined generate less than **10%** of total platform sales.

### Business Interpretation
Commercial platform growth is driven by a concentrated core of lifestyle, home, and electronics categories. Category management should prioritize deepening seller supply and merchant pricing competitiveness within these top 10 categories rather than expending resources on low-velocity long-tail categories.
