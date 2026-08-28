# US Beverage-Alcohol Category Demand Forecasting

A complete demand planning & forecasting workflow applied to real, publicly available U.S. retail sales data — built to demonstrate the reasoning and methodology used in FMCG/beverage demand planning roles.

## Business Context

Demand planners in the beverage-alcohol industry (e.g., at a company like Diageo) monitor category-level demand signals alongside brand-specific POS data to answer a recurring question: **based on this category's historical pattern, what should we expect next period, and how much safety stock buffer is defensible given our forecast's actual uncertainty?**

This project answers that question end-to-end using real data — not synthetic examples — and documents the *reasoning* behind each modeling decision, not just the code.

## Data

- **Source:** U.S. Census Bureau, Monthly Retail Trade Survey — Retail Sales: Beer, Wine, and Liquor Stores (NAICS 4453)
- **Access:** via FRED (Federal Reserve Economic Data), series `MRTSSM4453USN`
- **Coverage:** January 1992 – June 2026, monthly, not seasonally adjusted (deliberately — seasonality is something we detect and model ourselves, not something pre-removed)
- **Scope note:** this is a national, category-level aggregate (beer + wine + liquor combined), not a single brand or SKU. The same methodology applies directly at brand/SKU granularity; see *Limitations & Next Steps* below.

## Methodology

The notebook (`demand_forecasting_analysis.ipynb`) walks through:

1. **Exploratory Data Analysis** — visualizing the raw series, identifying a real anomaly period (COVID-era panic buying, March–June 2020) before any modeling
2. **Time Series Decomposition** — comparing **classical decomposition** (fixed seasonal averages, centered moving-average trend) against **STL** (Loess-based, allows seasonal amplitude to drift, covers full date range including series edges)
3. **Stationarity Testing** — formal Augmented Dickey-Fuller (ADF) tests confirming the raw series is non-stationary, and evaluating lag-1 (trend-removing) vs. seasonal lag-12 (seasonality-removing) differencing
4. **Baseline Forecasting Models** — Naive, 3-month Moving Average, Simple Exponential Smoothing, and Holt's Method, evaluated via honest backtesting (last 6 months held out)
5. **ARIMA & SARIMA** — comparing a non-seasonal ARIMA model against a SARIMA model with an explicit 12-month seasonal component
6. **Model Evaluation** — MAE, RMSE, and MAPE calculated on the same held-out backtest window for a fair, apples-to-apples comparison
7. **Safety Stock Calculation** — deriving a defensible inventory buffer directly from the selected model's own backtested forecast error (Z × σ × √Lead Time), rather than an arbitrary flat percentage

## Key Findings

- **SARIMA substantially outperformed every other model on real, held-out data**: MAE of 216.69 vs. Naive's 2,068.83, RMSE of 251.44 vs. Holt's Method's 1,493.51, and MAPE under 4% vs. over 37% for Naive.
- **STL revealed the December seasonal effect is not fixed** — it grew from ~$1,660M (2020) to ~$1,835M (2023) before easing, a pattern classical decomposition's flat-averaging approach structurally cannot detect.
- **A real, current business signal surfaced directly from the data**: the trend component shows measurable softening in 2024–2026, consistent with recently reported industry-wide growth deceleration in the beverage-alcohol category.
- **An honest statistical nuance is documented, not hidden**: combining seasonal and lag-1 differencing together did not pass the ADF stationarity test (likely over-differencing), even though each differencing method individually did — a reminder that formal tests can behave counter-intuitively, and backtested model performance is ultimately the more reliable guide.

## Why This Matters for Demand Planning

Every seasonality-blind model tested (Moving Average, Exponential Smoothing, Holt's Method) systematically misforecasts around the December-to-January transition — because none of them have any mechanism to recognize "this calendar position behaves differently." SARIMA's explicit seasonal component corrects this. This isn't a marginal technical improvement — it's the difference between a safety stock plan built on a forecast that's off by single-digit percentages versus one that's off by 20-35%+, with direct, quantifiable cost implications for overstocking or stockouts.

## Limitations & Next Steps

- This is national, category-level data — not brand or SKU-level. The identical pipeline applies directly given brand-level data.
- A natural extension is **SKU/brand-tier segmentation** — using clustering methods (e.g., K-means on volume and volatility) to route different products to different forecasting methods and safety stock policies, matching model sophistication to each product's actual demand behavior rather than using one model for an entire portfolio.
- ARIMA/SARIMA orders were set using standard defaults for this demonstration; a production implementation would use formal grid search / AIC-based order selection.
- Companion piece: a Power BI S&OP dashboard (in progress) built on this same dataset, translating this analysis into a business-facing KPI view.

## Tools Used

Python, pandas, NumPy, statsmodels (seasonal_decompose, STL, ARIMA, SARIMAX, adfuller), Matplotlib

## Repository Structure

```
├── demand_forecasting_analysis.ipynb   # Full analysis notebook (executed, with outputs)
├── beer_wine_liquor_sales.csv          # Source data
├── outputs/                             # Saved chart images
└── README.md
```
