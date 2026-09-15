-- ============================================================
-- SQL Companion Analysis: US Beverage-Alcohol Demand Forecasting
-- ============================================================
-- Database: SQLite
-- Tables:
--   beer_wine_liquor_sales (date TEXT, sales_millions INTEGER)
--   events (date TEXT, event_name TEXT)  -- supplementary promo/event tags
--
-- This file recreates key pieces of the Python/pandas analysis
-- (see demand_forecasting_analysis.ipynb in this repo) directly in SQL,
-- demonstrating the same business logic using window functions,
-- conditional logic, and joins instead of pandas operations.
-- ============================================================


-- ============================================================
-- 1. DATA EXPLORATION
-- ============================================================

-- 1.1 Row count check across the full historical dataset
SELECT COUNT(*) AS total_rows
FROM beer_wine_liquor_sales;
-- Returns 414 -- full Jan 1992 to Jun 2026 history

-- 1.2 Row count for the working window used in the main analysis
SELECT COUNT(*) AS working_window_rows
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01';
-- Returns 78 -- matches the 2020-2026 window used in the notebook


-- ============================================================
-- 2. AGGREGATION & GROUPING
-- ============================================================

-- 2.1 Total sales per year
-- Business question: is the category genuinely growing year over year?
SELECT
    substr(date, 1, 4) AS year,
    SUM(sales_millions) AS total_sales
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01'
GROUP BY year
ORDER BY year;

-- 2.2 Average monthly sales per year
-- Same grouping, different aggregate -- sanity-checks 2.1 against a
-- per-month scale (useful cross-check against the raw monthly chart)
SELECT
    substr(date, 1, 4) AS year,
    AVG(sales_millions) AS avg_monthly_sales
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01'
GROUP BY year
ORDER BY year;

-- 2.3 WHERE vs HAVING -- years that exceeded 70,000 in total sales
-- WHERE filters rows before grouping; HAVING filters groups after
-- aggregation, since a raw row has no "yearly total" to compare against
-- until GROUP BY has already run.
SELECT
    substr(date, 1, 4) AS year,
    SUM(sales_millions) AS total_sales
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01'
GROUP BY year
HAVING SUM(sales_millions) > 70000;


-- ============================================================
-- 3. WINDOW FUNCTIONS -- RANKING
-- ============================================================

-- 3.1 Rank each month within its own year by sales
-- Confirms the seasonal finding from the notebook: December should
-- rank #1 every single year, without collapsing any rows (unlike
-- GROUP BY, every month stays visible).
SELECT
    date,
    sales_millions,
    RANK() OVER (
        PARTITION BY substr(date, 1, 4)
        ORDER BY sales_millions DESC
    ) AS rank_in_year
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01';


-- ============================================================
-- 4. WINDOW FUNCTIONS -- LAG (DIFFERENCING)
-- ============================================================

-- 4.1 Lag-1 differencing -- removes TREND
-- Each month's value minus the immediately preceding month's value.
-- Matches the hand-calculated lag-1 differencing exercise: this
-- correctly flattens trend but leaves the December seasonal spike
-- fully visible in the differenced series.
SELECT
    date,
    sales_millions,
    LAG(sales_millions, 1) OVER (ORDER BY date) AS prior_month,
    sales_millions - LAG(sales_millions, 1) OVER (ORDER BY date) AS month_over_month_change
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01';

-- 4.2 Seasonal (lag-12) differencing -- removes SEASONALITY
-- Each month's value minus the SAME month one year earlier.
-- Note: the first 12 rows return NULL for prior_year_month, since
-- rows before 2020-01-01 were filtered out by the WHERE clause before
-- LAG had a chance to look back that far -- a real, worth-remembering
-- interaction between WHERE and window functions.
SELECT
    date,
    sales_millions,
    LAG(sales_millions, 12) OVER (ORDER BY date) AS prior_year_month,
    sales_millions - LAG(sales_millions, 12) OVER (ORDER BY date) AS year_over_year_change
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01';


-- ============================================================
-- 5. WINDOW FUNCTIONS -- MOVING AVERAGE
-- ============================================================

-- 5.1 3-month moving average
-- ROWS BETWEEN 2 PRECEDING AND CURRENT ROW = current row + 2 rows
-- before it = 3 rows total, matching the MA(3) model from the
-- Python notebook.
SELECT
    date,
    sales_millions,
    AVG(sales_millions) OVER (
        ORDER BY date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS moving_avg_3
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01';

-- 5.2 6-month moving average
-- Same logic, wider window: 5 PRECEDING + current row = 6 rows total.
SELECT
    date,
    sales_millions,
    AVG(sales_millions) OVER (
        ORDER BY date
        ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
    ) AS moving_avg_6
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01';


-- ============================================================
-- 6. CONDITIONAL LOGIC (CASE WHEN)
-- ============================================================

-- 6.1 Categorize each month into High/Medium/Low sales tiers
-- Conditions are checked top to bottom, and SQL stops at the FIRST
-- true match -- so the >= 6500 check must come before >= 5000, or
-- every high month would be silently mislabeled Medium.
SELECT
    date,
    sales_millions,
    CASE
        WHEN sales_millions >= 6500 THEN 'High'
        WHEN sales_millions >= 5000 THEN 'Medium'
        ELSE 'Low'
    END AS sales_category
FROM beer_wine_liquor_sales
WHERE date >= '2020-01-01';


-- ============================================================
-- 7. JOINS
-- ============================================================
-- Supplementary table: events(date, event_name) -- tags specific
-- months with known promotional/seasonal events, for demonstration.

-- 7.1 LEFT JOIN -- keep every sales row, whether or not an event exists
SELECT
    s.date,
    s.sales_millions,
    e.event_name
FROM beer_wine_liquor_sales AS s
LEFT JOIN events AS e
    ON s.date = e.date
WHERE s.date >= '2020-01-01';
-- Returns all 78 rows; event_name is NULL for months with no tagged event.

-- 7.2 INNER JOIN -- keep only rows with a matching event
SELECT
    s.date,
    s.sales_millions,
    e.event_name
FROM beer_wine_liquor_sales AS s
INNER JOIN events AS e
    ON s.date = e.date
WHERE s.date >= '2020-01-01';
-- Returns only 4 rows -- only months with a real tagged event survive.


-- ============================================================
-- END OF FILE
-- ============================================================
