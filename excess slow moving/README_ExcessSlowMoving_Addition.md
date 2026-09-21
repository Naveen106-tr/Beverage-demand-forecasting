# Excess & Slow-Moving Inventory Analysis

**4th addition to the [Beverage-demand-forecasting](https://github.com/Naveen106-tr/Beverage-demand-forecasting) portfolio repo.**

## What this adds

Builds on the existing ABC-XYZ SKU segmentation by answering a different question:
*not* "how important is this SKU" (ABC) or "how unpredictable is its demand" (XYZ),
but **"is the stock I'm currently holding healthy, or is it dead cash sitting on a
shelf?"**

## Method

- **Months of Cover (MOC)** = Stock on Hand ÷ Average Monthly Sales — converts a raw
  unit count into a time duration, which is what makes it comparable across SKUs of
  wildly different price points and volumes.
- Bucketed into the industry-standard ranges: **0–3 Healthy · 3–6 Watch · 6–12
  Slow-moving · 12+ Excess**.
- **Risk-weighted by cross-referencing MOC status against the existing ABC value
  tier** — an A-tier SKU sitting in Excess is a real cash/expiry problem; a C-tier
  SKU in the same MOC bucket barely moves the needle. This turns two separate
  metrics into a single, prioritized action list.

Stock-on-hand figures are simulated for this illustrative 25-SKU dataset (built on
top of the same demand data as the ABC-XYZ segmentation, same random seed, so the
ABC/XYZ labels match exactly). The simulation deliberately gives erratic-demand (Z)
SKUs a higher stock-coverage buffer than stable (X) SKUs — reflecting a real pattern
in operations, where planners over-order against unpredictable demand as a hedge,
which is exactly what tends to push those SKUs into Excess. The formula, the
bucketing logic, and the risk cross-reference are identical to what would be applied
to a real stock ledger.

## Result

| MOC Status | SKU Count |
|---|---|
| Healthy | 10 |
| Watch | 8 |
| Slow-moving | 6 |
| Excess | 1 |

**3 High-Risk SKUs** (high value + poor inventory health) surfaced by the
cross-reference:

| SKU | ABC-XYZ | Months of Cover | Status |
|---|---|---|---|
| Premium Whiskey 700ml | AY | 6.2 | Slow-moving |
| Luxury Chocolate Box | AY | 7.1 | Slow-moving |
| Designer Sunglasses | AZ | 9.9 | Slow-moving |

These are the three SKUs a planner should act on first — not the single "Excess"
SKU (Allergen-Free Meal), which is low-value and low priority despite technically
sitting in the worst MOC bucket. That's the entire point of the risk-weighting: raw
MOC status alone would have sent attention to the wrong SKU.

## Files

- `excess_slow_moving_analysis.py` — full script (data generation → ABC-XYZ →
  stock simulation → MOC → risk-weighting), self-contained and reproducible
- `excess_slow_moving_analysis.csv` — final output, one row per SKU
- `excess_slow_moving_risk_map.png` — Months of Cover (x) vs Total Value (y),
  colored by MOC status, shaped by ABC tier
