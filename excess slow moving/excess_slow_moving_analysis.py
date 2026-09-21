"""
Excess & Slow-Moving Inventory Analysis
=========================================
Companion analysis to the ABC-XYZ SKU segmentation (same 25-SKU illustrative
dataset, regenerated here with the identical seed/logic so results match
sku_final_classification.csv exactly).

Core metric: Months of Cover (MOC) = Stock on Hand / Average Monthly Sales
  - Converts a raw stock quantity into a TIME duration ("how many months
    would this stock last at the current sales rate"), which is what makes
    it comparable across totally different SKUs (a €1 snack vs a €120 scotch).

Buckets (industry-standard):
  0-3 months   -> Healthy
  3-6 months   -> Watch
  6-12 months  -> Slow-moving
  12+ months   -> Excess

The real value-add: cross-referencing MOC against the existing ABC-XYZ
classification. "Excess" alone doesn't tell you what to act on first -
an AX item (high value, stable demand) sitting in Excess is a real cash and
expiry problem; a CZ item (low value, erratic demand) sitting in Excess is
low priority. That cross-reference produces a genuine risk-priority ranking.

Note: Stock-on-hand figures are illustrative/simulated for this portfolio
exercise (no real stock ledger is public), built to reflect a realistic
pattern seen in real operations - erratic-demand (Z) SKUs tend to carry
disproportionately more buffer stock because planners over-order against
their unpredictability, which ironically is what pushes them into Excess
most often. The methodology (the formula, the bucketing, the cross-reference)
is identical to what would be applied to a real stock ledger.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

np.random.seed(42)

# ------------------------------------------------------------------
# STEP 1: Regenerate the same 25-SKU monthly demand dataset
# (identical to abc_xyz_kmeans_analysis.py so ABC-XYZ results match exactly)
# ------------------------------------------------------------------
skus = [
    ("Bottled Water 500ml", 1.2, 8000, 'stable'),
    ("Coffee Sachets", 0.8, 6000, 'stable'),
    ("Snack Bar - Standard", 1.5, 5000, 'stable'),
    ("Soft Drink Can", 1.3, 7000, 'stable'),
    ("Tea Bags Box", 0.9, 3000, 'stable'),
    ("Premium Whiskey 700ml", 45.0, 900, 'seasonal'),
    ("Business Class Wine (Bordeaux)", 65.0, 400, 'seasonal'),
    ("Gin & Tonic Gift Set", 30.0, 700, 'seasonal'),
    ("Luxury Chocolate Box", 18.0, 1200, 'seasonal'),
    ("Perfume 50ml (Mid-tier)", 55.0, 500, 'seasonal'),
    ("Duty-Free Cigarettes Carton", 40.0, 1500, 'stable'),
    ("Standard Sandwich", 4.5, 4000, 'stable'),
    ("Premium Sandwich (Seasonal Menu)", 6.0, 800, 'seasonal'),
    ("Rare Single-Malt Scotch", 120.0, 150, 'erratic'),
    ("Limited-Edition Cologne", 85.0, 100, 'erratic'),
    ("Designer Sunglasses", 95.0, 120, 'erratic'),
    ("Novelty Travel Gadget", 25.0, 200, 'erratic'),
    ("Regional Craft Beer (rotating)", 5.5, 600, 'erratic'),
    ("Power Bank / Charger", 22.0, 350, 'stable'),
    ("Standard Headphones", 15.0, 600, 'stable'),
    ("Premium Noise-Cancelling Headphones", 110.0, 180, 'seasonal'),
    ("Kids Activity Pack", 3.0, 900, 'seasonal'),
    ("Allergen-Free Meal", 7.0, 90, 'erratic'),
    ("Vegan Meal Option", 6.5, 250, 'stable'),
    ("Business Class Amenity Kit", 12.0, 400, 'stable'),
]

rows = []
for name, price, avg_units, vtype in skus:
    months = pd.date_range('2024-01-01', periods=24, freq='MS')
    if vtype == 'stable':
        noise_pct = 0.08
        seasonal = np.zeros(24)
    elif vtype == 'seasonal':
        noise_pct = 0.15
        month_nums = months.month
        seasonal = np.array([avg_units * 0.5 if m == 12 else (avg_units * 0.2 if m in [6, 7] else 0) for m in month_nums])
    else:  # erratic
        noise_pct = 0.45
        seasonal = np.zeros(24)

    base = avg_units + seasonal
    noise = np.random.normal(0, avg_units * noise_pct, 24)
    demand = np.maximum(base + noise, 0).round().astype(int)

    for m, d in zip(months, demand):
        rows.append({'sku_name': name, 'date': m, 'unit_price': price, 'units_sold': d, 'demand_type': vtype})

df = pd.DataFrame(rows)

# ------------------------------------------------------------------
# STEP 2: ABC (value / Pareto) + XYZ (K-means on Coefficient of Variation)
# - identical methodology to the segmentation project
# ------------------------------------------------------------------
df['revenue'] = df['units_sold'] * df['unit_price']
sku_value = df.groupby('sku_name').agg(
    total_value=('revenue', 'sum'),
    avg_monthly_units=('units_sold', 'mean'),
    unit_price=('unit_price', 'first'),
    demand_type=('demand_type', 'first'),
).reset_index()

sku_value = sku_value.sort_values('total_value', ascending=False).reset_index(drop=True)
sku_value['cumulative_value'] = sku_value['total_value'].cumsum()
sku_value['cumulative_pct'] = sku_value['cumulative_value'] / sku_value['total_value'].sum() * 100

def classify_abc(pct):
    if pct <= 80:
        return 'A'
    elif pct <= 95:
        return 'B'
    else:
        return 'C'

sku_value['ABC'] = sku_value['cumulative_pct'].apply(classify_abc)

cv_data = df.groupby('sku_name')['units_sold'].agg(['mean', 'std']).reset_index()
cv_data['CV'] = cv_data['std'] / cv_data['mean']

X = cv_data['CV'].values.reshape(-1, 1)
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
cv_data['cluster'] = kmeans.fit_predict(X)
centers = kmeans.cluster_centers_.flatten()
order = np.argsort(centers)
label_map = {order[0]: 'X', order[1]: 'Y', order[2]: 'Z'}
cv_data['XYZ'] = cv_data['cluster'].map(label_map)

merged = sku_value.merge(cv_data[['sku_name', 'CV', 'XYZ']], on='sku_name')
merged['ABC_XYZ'] = merged['ABC'] + merged['XYZ']

# ------------------------------------------------------------------
# STEP 3: Simulate a realistic Stock-on-Hand figure per SKU
# ------------------------------------------------------------------
# Coverage multiplier = how many months of stock a planner would typically
# be sitting on. Stable (X) SKUs turn over predictably and get ordered
# tightly (low, controlled coverage). Erratic (Z) SKUs get over-ordered as
# a buffer against their unpredictability - which is exactly why erratic
# items are disproportionately likely to end up Excess in real operations.
coverage_base = {'X': 2.0, 'Y': 4.5, 'Z': 9.0}

np.random.seed(7)  # separate seed so stock simulation doesn't disturb ABC-XYZ reproducibility
merged['coverage_multiplier'] = merged['XYZ'].map(coverage_base) * np.random.uniform(0.6, 1.6, len(merged))
merged['stock_on_hand'] = (merged['avg_monthly_units'] * merged['coverage_multiplier']).round().astype(int)

# ------------------------------------------------------------------
# STEP 4: Months of Cover + bucketing
# ------------------------------------------------------------------
merged['months_of_cover'] = (merged['stock_on_hand'] / merged['avg_monthly_units']).round(1)

def classify_moc(moc):
    if moc <= 3:
        return 'Healthy'
    elif moc <= 6:
        return 'Watch'
    elif moc <= 12:
        return 'Slow-moving'
    else:
        return 'Excess'

merged['MOC_status'] = merged['months_of_cover'].apply(classify_moc)

# ------------------------------------------------------------------
# STEP 5: Risk-weighting - cross-reference MOC status against ABC value tier
# ------------------------------------------------------------------
moc_severity = {'Healthy': 0, 'Watch': 1, 'Slow-moving': 2, 'Excess': 3}
abc_weight = {'A': 3, 'B': 2, 'C': 1}
merged['risk_score'] = merged['MOC_status'].map(moc_severity) * merged['ABC'].map(abc_weight)

def risk_tier(score):
    if score >= 6:
        return 'High Risk - act now'
    elif score >= 3:
        return 'Medium Risk - monitor'
    elif score >= 1:
        return 'Low Risk'
    else:
        return 'No Action Needed'

merged['risk_tier'] = merged['risk_score'].apply(risk_tier)

out_cols = ['sku_name', 'ABC', 'XYZ', 'ABC_XYZ', 'total_value', 'avg_monthly_units',
            'stock_on_hand', 'months_of_cover', 'MOC_status', 'risk_score', 'risk_tier']
final = merged[out_cols].sort_values('risk_score', ascending=False).reset_index(drop=True)
final.to_csv('excess_slow_moving_analysis.csv', index=False)

print(final.to_string(index=False))

print("\nMOC status distribution:")
print(final['MOC_status'].value_counts())

print("\nHigh Risk SKUs (High-value AND poor inventory health):")
print(final[final['risk_tier'] == 'High Risk - act now'][['sku_name', 'ABC_XYZ', 'months_of_cover', 'MOC_status']].to_string(index=False))
