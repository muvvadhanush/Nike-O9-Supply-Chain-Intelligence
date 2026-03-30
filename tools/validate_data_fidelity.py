import pandas as pd
import numpy as np
from scipy.stats import ks_2samp
import os

def validate_demand_data(file_path):
    print(f"--- Validating Demand Planning Data: {file_path} ---")
    df = pd.read_csv(file_path)
    
    # 1. Row Count Check
    row_count = len(df)
    print(f"Total Records: {row_count}")
    if row_count < 10000:
        print("WARNING: Row count is below 10,000 target.")
    else:
        print("SUCCESS: Row count meets target.")

    # 2. Distribution Check (KS-Test)
    # Compare baseline_forecast vs actual_sales
    ks_stat, p_value = ks_2samp(df['baseline_forecast'], df['actual_sales'])
    print(f"KS-Test (Baseline vs Actual Sales): Statistic={ks_stat:.4f}, P-Value={p_value:.4f}")
    if p_value > 0.05:
        print("SUCCESS: Distributions are statistically similar (p > 0.05).")
    else:
        print("NOTE: Significant distribution shift detected (expected for synthetic data variance).")

    # 3. Pearson Correlation
    correlation = df['ai_forecast'].corr(df['actual_sales'])
    print(f"Pearson Correlation (AI Forecast vs Actual Sales): {correlation:.4f}")
    if correlation > 0.8:
        print("SUCCESS: High correlation between AI forecast and actual sales.")
    else:
        print("WARNING: Low correlation detected.")

    # 4. Integrity Check
    null_count = df.isnull().sum().sum()
    print(f"Total Null Values: {null_count}")
    if null_count == 0:
        print("SUCCESS: No missing values found.")
    else:
        print(f"WARNING: {null_count} missing values found.")

def validate_inventory_alignment(demand_path, inventory_path):
    print(f"\n--- Validating Inventory-Demand Alignment ---")
    demand_df = pd.read_csv(demand_path)
    inventory_df = pd.read_csv(inventory_path)
    
    demand_skus = set(demand_df['sku'].unique())
    inventory_skus = set(inventory_df['sku'].unique())
    
    missing_in_demand = inventory_skus - demand_skus
    print(f"SKUs in Inventory but missing in Demand: {len(missing_in_demand)}")
    
    if len(missing_in_demand) == 0:
        print("SUCCESS: All inventory SKUs exist in the master demand dataset.")
    else:
        print(f"WARNING: Found {len(missing_in_demand)} orphanage SKUs.")

if __name__ == "__main__":
    demand_file = "data/datasets/demand_planning_dataset.csv"
    inventory_file = "data/Dataset/inventory_positions.csv"
    
    if os.path.exists(demand_file):
        validate_demand_data(demand_file)
    else:
        print(f"ERROR: {demand_file} not found.")
        
    if os.path.exists(demand_file) and os.path.exists(inventory_file):
        validate_inventory_alignment(demand_file, inventory_file)
    else:
        print(f"ERROR: One or both data files not found for alignment check.")
