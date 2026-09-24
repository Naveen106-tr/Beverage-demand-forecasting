"""
Forecast Accuracy & Bias Analysis
==================================
5th addition to the Beverage-demand-forecasting portfolio repo.

Core idea: accuracy metrics (MAE, RMSE, MAPE) tell you HOW FAR OFF a forecast
was, using absolute error - they treat an over-forecast and an under-forecast
identically. BIAS (Mean Error, no absolute value) tells you WHICH DIRECTION
the forecast is consistently wrong in. A forecast can have a perfectly
respectable MAPE while being systematically, structurally wrong every single
December - and MAPE alone will never surface that.

Dataset: real, publicly available monthly champagne sales (Perrin Freres),
Jan 1964 - Sep 1972, sourced from a well-known open time-series dataset
mirror (originally a classic Box-Jenkins-era dataset used throughout
forecasting literature). Chosen deliberately for this analysis because it
has a huge, real, recurring December seasonal spike (New Year's Eve demand) -
exactly the kind of pattern a naive/non-seasonal forecasting method
systematically misses, which is what makes the bias story real rather than
manufactured.

Method:
  1. Split into train (first ~7 years) and test (last 24 months).
  2. Build two forecasting methods on the same train data:
       - Naive Seasonal-Blind method: 12-month trailing moving average
         (a common, real-world "quick and dirty" forecasting shortcut that
         completely ignores seasonality).
       - Proper method: Holt-Winters Triple Exponential Smoothing with
         multiplicative seasonality (correctly models the recurring
         December spike).
  3. For both methods, compute on the test set:
       - MAE, RMSE, MAPE (accuracy - direction-blind)
       - ME / Bias (Mean Error - direction-aware, no absolute value)
     both overall AND broken out by calendar month, to show WHERE the bias
     concentrates.
  4. Visualize actual vs. both forecasts, plus a bias-by-month bar chart.

This mirrors the real difference between "our forecast is off by about 12%"
(accuracy - which sounds vaguely fine) and "our forecast is ALWAYS off by
about 12% in December, in the same direction, every year" (bias - which is
an actionable, structural finding a planner should act on).
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# ------------------------------------------------------------------
# STEP 1: Load real data
# ------------------------------------------------------------------
df = pd.read_csv("champagne_sales_raw.csv")
df.columns = ["month", "sales"]
df["month"] = pd.to_datetime(df["month"], format="%Y-%m")
df = df.set_index("month").asfreq("MS")
df = df.dropna()  # source file has a couple of trailing footer rows with NaN sales

series = df["sales"]

# ------------------------------------------------------------------
# STEP 2: Train / test split - last 24 months held out for testing
# ------------------------------------------------------------------
test_periods = 24
train = series.iloc[:-test_periods]
test = series.iloc[-test_periods:]

# ------------------------------------------------------------------
# STEP 3a: Naive Seasonal-Blind forecast - 12-month trailing moving average
# held flat forward for the whole test window (a real, commonly-used
# shortcut when nobody has set up a proper seasonal model)
# ------------------------------------------------------------------
naive_level = train.iloc[-12:].mean()
naive_forecast = pd.Series([naive_level] * test_periods, index=test.index)

# ------------------------------------------------------------------
# STEP 3b: Proper method - Holt-Winters with multiplicative seasonality
# ------------------------------------------------------------------
hw_model = ExponentialSmoothing(
    train, trend="add", seasonal="mul", seasonal_periods=12
).fit()
hw_forecast = hw_model.forecast(test_periods)

# ------------------------------------------------------------------
# STEP 4: Accuracy metrics (direction-blind) + Bias (direction-aware)
# ------------------------------------------------------------------
def accuracy_metrics(actual, forecast):
    error = actual - forecast
    mae = error.abs().mean()
    rmse = np.sqrt((error ** 2).mean())
    mape = (error.abs() / actual).mean() * 100
    bias = error.mean()  # Mean Error - NO absolute value, sign preserved
    return mae, rmse, mape, bias

results = []
for name, fc in [("Naive Seasonal-Blind (12mo avg)", naive_forecast),
                  ("Holt-Winters (seasonal)", hw_forecast)]:
    mae, rmse, mape, bias = accuracy_metrics(test, fc)
    results.append({
        "method": name, "MAE": round(mae, 1), "RMSE": round(rmse, 1),
        "MAPE_%": round(mape, 1), "Bias_ME": round(bias, 1),
    })

summary = pd.DataFrame(results)
summary.to_csv("forecast_accuracy_summary.csv", index=False)

# ------------------------------------------------------------------
# STEP 5: Bias broken out by calendar month - this is where the real
# finding lives. A December-specific bias number is far more actionable
# than one blended annual bias figure.
# ------------------------------------------------------------------
monthly_bias = pd.DataFrame({
    "actual": test,
    "naive_forecast": naive_forecast,
    "hw_forecast": hw_forecast,
})
monthly_bias["naive_error"] = monthly_bias["actual"] - monthly_bias["naive_forecast"]
monthly_bias["hw_error"] = monthly_bias["actual"] - monthly_bias["hw_forecast"]
monthly_bias["calendar_month"] = monthly_bias.index.month_name().str.slice(0, 3)
monthly_bias.to_csv("forecast_bias_by_month.csv")

by_month = monthly_bias.groupby("calendar_month")[["naive_error", "hw_error"]].mean()
month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
by_month = by_month.reindex([m for m in month_order if m in by_month.index])

print("=== Overall Accuracy & Bias (test set, last 24 months) ===")
print(summary.to_string(index=False))
print("\n=== Average Bias by Calendar Month (Naive vs. Holt-Winters) ===")
print(by_month.round(0).to_string())

# ------------------------------------------------------------------
# STEP 6: Visualization
# ------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(11, 9))

ax = axes[0]
ax.plot(series.index, series.values, color="#3a3a3a", linewidth=1.2, label="Actual (full history)")
ax.plot(test.index, naive_forecast.values, color="#c0392b", linewidth=2, linestyle="--", label="Naive Seasonal-Blind forecast")
ax.plot(test.index, hw_forecast.values, color="#1e7a4c", linewidth=2, label="Holt-Winters (seasonal) forecast")
ax.axvline(train.index[-1], color="gray", linestyle=":", linewidth=1)
ax.set_title("Champagne Sales: Actual vs. Two Forecasting Methods (Test Window)")
ax.set_ylabel("Monthly Sales (units)")
ax.legend(loc="upper left")

ax2 = axes[1]
x = np.arange(len(by_month))
width = 0.35
ax2.bar(x - width/2, by_month["naive_error"], width, color="#c0392b", label="Naive Seasonal-Blind — avg. error (Actual − Forecast)")
ax2.bar(x + width/2, by_month["hw_error"], width, color="#1e7a4c", label="Holt-Winters — avg. error (Actual − Forecast)")
ax2.axhline(0, color="black", linewidth=0.8)
ax2.set_xticks(x)
ax2.set_xticklabels(by_month.index)
ax2.set_title("Forecast Bias by Calendar Month (positive = under-forecasting, negative = over-forecasting)")
ax2.set_ylabel("Average Error (units)")
ax2.legend(loc="upper left")

plt.tight_layout()
plt.savefig("forecast_bias_chart.png", dpi=150)
print("\nChart saved to forecast_bias_chart.png")
