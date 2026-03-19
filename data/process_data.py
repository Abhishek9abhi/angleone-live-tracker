import pandas as pd

file_path = r"C:\Users\abhis\angleone_live_tracker\data\live_data_2026-03-17.csv"

df = pd.read_csv(file_path)

# Sort properly
df = df.sort_values(by=["Symbol", "Time"])

# Previous values
df["Prev_Buy_Qty"] = df.groupby("Symbol")["Buy_Qty"].shift(1)
df["Prev_Sell_Qty"] = df.groupby("Symbol")["Sell_Qty"].shift(1)

# Change
df["Buy_Qty_Change"] = df["Buy_Qty"] - df["Prev_Buy_Qty"]
df["Sell_Qty_Change"] = df["Sell_Qty"] - df["Prev_Sell_Qty"]

# Percentage change
df["Buy_%_Change"] = (df["Buy_Qty_Change"] / df["Prev_Buy_Qty"]) * 100
df["Sell_%_Change"] = (df["Sell_Qty_Change"] / df["Prev_Sell_Qty"]) * 100

df.fillna(0, inplace=True)

# Save output
output_path = r"C:\Users\abhis\angleone_live_tracker\data\processed_data.csv"
df.to_csv(output_path, index=False)

print("✅ Done! File saved at:", output_path)