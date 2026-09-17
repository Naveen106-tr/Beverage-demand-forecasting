"""
ABC-XYZ SKU Segmentation with K-Means Clustering
==================================================
Companion analysis to the main demand forecasting project.

ABC = classifies SKUs by total consumption VALUE (Pareto/cumulative % method)
XYZ = classifies SKUs by demand VARIABILITY (K-means clustering on Coefficient of Variation)

Combining both dimensions gives a 3x3 grid that tells a planner exactly how much
forecasting/inventory-control effort each product actually deserves - rather than
treating every SKU with the same method.

Note: SKU-level data below is illustrative (built to reflect realistic airline/retail
product behavior - stable, seasonal, and erratic demand patterns), since real per-SKU
data isn't publicly available. The methodology is identical to what would be applied
to real SKU-level sales data.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

np.random.seed(42)

# ------------------------------------------------------------------
# STEP 1: Generate realistic SKU-level monthly demand data
# ------------------------------------------------------------------
# Each SKU is tagged with an intended behavior type (stable/seasonal/erratic)
# so we can later verify K-means correctly recovers these patterns on its own.

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
        seasonal = np.array([avg_units*0.5 if m == 12 else (avg_units*0.2 if m in [6, 7] else 0) for m in month_nums])
    else:  # erratic
        noise_pct = 0.45
        seasonal = np.zeros(24)

    base = avg_units + seasonal
    noise = np.random.normal(0, avg_units * noise_pct, 24)
    demand = np.maximum(base + noise, 0).round().astype(int)

    for m, d in zip(months, demand):
        rows.append({'sku_name': name, 'date': m, 'unit_price': price, 'units_sold': d})

df = pd.DataFrame(rows)
df.to_csv('sku_monthly_demand.csv', index=False)


# ------------------------------------------------------------------
# STEP 2: ABC classification - total value via Pareto / cumulative %
# ------------------------------------------------------------------
df['revenue'] = df['units_sold'] * df['unit_price']
sku_value = df.groupby('sku_name').agg(
    total_value=('revenue', 'sum'),
    avg_monthly_units=('units_sold', 'mean'),
    unit_price=('unit_price', 'first')
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
sku_value.to_csv('sku_abc_classification.csv', index=False)


# ------------------------------------------------------------------
# STEP 3: XYZ classification - demand variability via K-MEANS (not fixed thresholds)
# ------------------------------------------------------------------
# Coefficient of Variation (CV) = std deviation / mean.
# CV lets us fairly compare a high-volume product against a low-volume one on
# the same relative scale, rather than raw standard deviation alone.

cv_data = df.groupby('sku_name')['units_sold'].agg(['mean', 'std']).reset_index()
cv_data['CV'] = cv_data['std'] / cv_data['mean']

# K-means with K=3 finds the natural breaks in variability, rather than us
# picking arbitrary CV thresholds in advance.
X = cv_data['CV'].values.reshape(-1, 1)
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
cv_data['cluster'] = kmeans.fit_predict(X)

# K-means assigns arbitrary cluster numbers (0,1,2) - we map them to X/Y/Z
# based on the actual cluster center values, low to high.
centers = kmeans.cluster_centers_.flatten()
order = np.argsort(centers)
label_map = {order[0]: 'X', order[1]: 'Y', order[2]: 'Z'}
cv_data['XYZ'] = cv_data['cluster'].map(label_map)
cv_data.to_csv('sku_xyz_classification.csv', index=False)


# ------------------------------------------------------------------
# STEP 4: Combine both dimensions into the final 3x3 grid
# ------------------------------------------------------------------
merged = sku_value.merge(cv_data[['sku_name', 'CV', 'XYZ']], on='sku_name')
merged['ABC_XYZ'] = merged['ABC'] + merged['XYZ']
merged.to_csv('sku_final_classification.csv', index=False)

print(merged[['sku_name', 'ABC', 'XYZ', 'ABC_XYZ', 'total_value', 'CV']].sort_values('ABC_XYZ').to_string(index=False))

grid = merged.groupby(['ABC', 'XYZ']).size().unstack(fill_value=0).reindex(index=['A', 'B', 'C'], columns=['X', 'Y', 'Z'])
print("\n3x3 Grid (SKU count per combination):")
print(grid)
