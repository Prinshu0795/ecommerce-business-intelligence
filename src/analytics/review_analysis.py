"""
Customer Experience & Review Analytics Module
Evaluates CSAT scores, rating distributions, category satisfaction,
and the empirical relationship between logistical delays and customer sentiment.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
from src.database.connection import query_df

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_review_summary_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate core review KPIs with explicit denominators."""
    where_clauses = ["o.order_status = 'delivered'", "r.review_score IS NOT NULL"]
    params = {}

    if start_date:
        where_clauses.append("o.order_purchase_timestamp >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where_clauses.append("o.order_purchase_timestamp <= :end_date")
        params["end_date"] = end_date
    if category_name and category_name != "All":
        where_clauses.append(
            "o.order_id IN (SELECT oi.order_id FROM fact_order_item oi "
            "JOIN dim_product p ON oi.product_id = p.product_id "
            "WHERE p.product_category_name_english = :category_name)"
        )
        params["category_name"] = category_name

    where_sql = " AND ".join(where_clauses)

    sql = f"""
    SELECT
        COUNT(r.review_id) AS total_reviews,
        ROUND(AVG(r.review_score), 2) AS avg_review_score,
        COUNT(CASE WHEN r.review_score IN (1, 2) THEN 1 END) AS low_rating_count,
        COUNT(CASE WHEN r.review_score = 5 THEN 1 END) AS five_star_count,
        COUNT(CASE WHEN r.review_comment_message != '' AND r.review_comment_message IS NOT NULL THEN 1 END) AS text_comment_count
    FROM fact_review r
    JOIN fact_order o ON r.order_id = o.order_id
    WHERE {where_sql};
    """
    df = query_df(sql, params)
    row = df.iloc[0].to_dict()

    total_reviews = int(row["total_reviews"] or 0)
    low_ratings = int(row["low_rating_count"] or 0)
    five_star = int(row["five_star_count"] or 0)

    return {
        "total_reviews": total_reviews,
        "avg_review_score": float(row["avg_review_score"] or 0.0),
        "low_rating_count": low_ratings,
        "low_rating_rate_pct": round((low_ratings * 100.0) / total_reviews, 2) if total_reviews else 0.0,
        "five_star_count": five_star,
        "five_star_rate_pct": round((five_star * 100.0) / total_reviews, 2) if total_reviews else 0.0,
        "text_comment_count": int(row["text_comment_count"] or 0),
    }


def get_review_score_distribution() -> pd.DataFrame:
    """Retrieve review score frequency distribution."""
    sql = """
    SELECT
        review_score,
        COUNT(review_id) AS review_count,
        ROUND(COUNT(review_id) * 100.0 / SUM(COUNT(review_id)) OVER (), 2) AS percentage,
        CASE
            WHEN review_score IN (4, 5) THEN 'Positive'
            WHEN review_score = 3 THEN 'Neutral'
            ELSE 'Negative (Dissatisfied)'
        END AS sentiment
    FROM fact_review
    GROUP BY review_score
    ORDER BY review_score ASC;
    """
    return query_df(sql)


def get_delay_vs_review_score() -> pd.DataFrame:
    """Retrieve review scores across delay severity brackets."""
    sql = """
    WITH delay_buckets AS (
        SELECT
            o.order_id,
            r.review_score,
            o.delivery_delay_days,
            CASE
                WHEN o.delivery_delay_days <= -7.0 THEN '1. Early (>7 days)'
                WHEN o.delivery_delay_days <= -2.0 THEN '2. Early (2-7 days)'
                WHEN o.delivery_delay_days <= 0.0 THEN '3. On-Time (0-1 day early)'
                WHEN o.delivery_delay_days <= 3.0 THEN '4. Minor Delay (1-3 days)'
                WHEN o.delivery_delay_days <= 7.0 THEN '5. Moderate Delay (4-7 days)'
                ELSE '6. Severe Delay (>7 days)'
            END AS delay_bracket
        FROM fact_order o
        JOIN fact_review r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
          AND o.delivery_delay_days IS NOT NULL
    )
    SELECT
        delay_bracket,
        COUNT(*) AS total_reviews,
        ROUND(AVG(review_score), 2) AS avg_review_score,
        COUNT(CASE WHEN review_score IN (1, 2) THEN 1 END) AS low_rating_count,
        ROUND(COUNT(CASE WHEN review_score IN (1, 2) THEN 1 END) * 100.0 / COUNT(*), 2) AS low_rating_pct,
        ROUND(AVG(delivery_delay_days), 1) AS avg_delay_days
    FROM delay_buckets
    GROUP BY delay_bracket
    ORDER BY delay_bracket ASC;
    """
    return query_df(sql)


def get_category_review_scores(min_reviews: int = 50) -> pd.DataFrame:
    """Retrieve average review score by product category."""
    sql = f"""
    SELECT
        COALESCE(p.product_category_name_english, 'Other Or Unlabeled') AS category_name,
        COUNT(r.review_id) AS total_reviews,
        ROUND(AVG(r.review_score), 2) AS avg_review_score,
        ROUND(COUNT(CASE WHEN r.review_score IN (1, 2) THEN 1 END) * 100.0 / COUNT(r.review_id), 2) AS low_rating_rate_pct
    FROM fact_review r
    JOIN fact_order o ON r.order_id = o.order_id
    JOIN fact_order_item oi ON o.order_id = oi.order_id
    JOIN dim_product p ON oi.product_id = p.product_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.product_category_name_english
    HAVING COUNT(r.review_id) >= {min_reviews}
    ORDER BY avg_review_score DESC;
    """
    return query_df(sql)
