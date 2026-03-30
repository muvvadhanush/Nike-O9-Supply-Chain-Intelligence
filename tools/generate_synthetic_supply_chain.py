import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, timedelta

# Configuration
TARGET_SKUS = 12000
REGIONS = ["North America", "EMEA", "Greater China", "APLA"]
CHANNELS = ["Direct-to-Consumer", "Wholesale", "Digital"]
LIFECYCLE_STAGES = ["Growth", "Mature", "Decline", "New Launch"]
DCS = ["Memphis Distribution Center", "Rotterdam Distribution Center", "Barcelona Distribution Center", "Los Angeles Distribution Center", "Denver Distribution Center"]

CATEGORIES = {
    "Footwear": ["Air Max 270", "Air Max 90", "Air Max Plus", "Air Zoom Pegasus 40", "Vaporfly 3", "Invincible 3", "React Phantom Run 3", "Metcon 9 Amp", "SB Dunk Low Pro", "Blazer Mid '77", "Court Vision Low", "Jordan Stay Loyal 3", "LeBron XXI", "KD16", "Ja 1"],
    "Apparel": ["Dri-FIT Running Shirt M", "Dri-FIT Running Shirt W", "Tech Fleece Joggers M", "Sportswear Icon Clash", "Element Crew Top", "ACG Mountain Fly", "Pro Dri-FIT Tight", "Storm-FIT Jacket", "Yoga Luxe Leggings"]
}

SKU_PREFIXES = {
    "Air Max 270": "NK-AM-270-", "Air Max 90": "NK-AM-90-", "Air Max Plus": "NK-AM-PLS-",
    "Air Zoom Pegasus 40": "NK-ZP-40-", "Vaporfly 3": "NK-VF-3-", "Invincible 3": "NK-IV-3-",
    "React Phantom Run 3": "NK-RT-3-", "Metcon 9 Amp": "NK-MT-9-", "SB Dunk Low Pro": "NK-SB-DLP-",
    "Blazer Mid '77": "NK-BZ-77-", "Court Vision Low": "NK-CV-L-", "Jordan Stay Loyal 3": "NK-JD-SL3-",
    "LeBron XXI": "NK-BK-L21-", "KD16": "NK-BK-KD16-", "Ja 1": "NK-BK-JA1-",
    "Dri-FIT Running Shirt M": "NK-RA-RM-", "Dri-FIT Running Shirt W": "NK-RA-RW-",
    "Tech Fleece Joggers M": "NK-AP-TJ-", "Sportswear Icon Clash": "NK-AP-IC-",
    "Element Crew Top": "NK-AP-ECT-", "ACG Mountain Fly": "NK-AP-ACG-",
    "Pro Dri-FIT Tight": "NK-AP-PDF-", "Storm-FIT Jacket": "NK-AP-SFJ-", "Yoga Luxe Leggings": "NK-AP-YLL-"
}

def generate_demand_data(num_records):
    print(f"Generating {num_records} demand planning records (Fact_DemandInputForecast.csv)...")
    data = []
    
    # Generate base SKUs
    base_skus = []
    for _ in range(2000): # 2000 unique SKU IDs
        cat_type = random.choice(list(CATEGORIES.keys()))
        prod_name = random.choice(CATEGORIES[cat_type])
        prefix = SKU_PREFIXES[prod_name]
        sku_id = f"{prefix}{random.randint(1000, 9999)}"
        base_skus.append((sku_id, prod_name, cat_type))

    start_date = datetime(2026, 3, 1)
    
    for i in range(num_records):
        sku_id, prod_name, cat_type = random.choice(base_skus)
        region = random.choice(REGIONS)
        channel = random.choice(CHANNELS)
        lifecycle = random.choice(LIFECYCLE_STAGES)
        week = start_date + timedelta(days=(i % 12) * 7) # 12 weeks of data
        
        baseline = random.uniform(500, 20000)
        ai_forecast = baseline * random.uniform(0.9, 1.1)
        actual_sales = baseline * random.uniform(0.85, 1.15)
        accuracy = 1 - (abs(ai_forecast - actual_sales) / actual_sales if actual_sales > 0 else 0)
        inventory = actual_sales * random.uniform(1.0, 3.0)
        safety_stock = actual_sales * 0.2
        on_promo = 1 if random.random() < 0.15 else 0
        
        data.append({
            "Version.[Version Name]": "Baseline FY26",
            "Location.[Location]": region,
            "Sales Domain.[Customer Group]": channel,
            "Time.[Day]": week.strftime("%Y-%m-%d"),
            "Item.[Item]": sku_id,
            "D Base Forecast LC": baseline * 1.2,
            "D Base Forecast Quantity": baseline,
            "D Base Forecast Supply Code": "NORM",
            "D Buff1 Forecast Quantity": safety_stock,
            "D Buff2 Forecast Quantity": safety_stock * 1.2,
            # Additional POC Columns
            "product_name": prod_name,
            "category": cat_type,
            "lifecycle_stage": lifecycle,
            "ai_forecast": ai_forecast,
            "actual_sales": actual_sales,
            "forecast_accuracy": accuracy,
            "inventory_on_hand": inventory,
            "safety_stock": safety_stock,
            "on_promo": on_promo
        })
        
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_DemandInputForecast.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_inventory_data(num_records):
    print(f"Generating {num_records} inventory records (Fact_InventorySnapshot.csv)...")
    demand_df = pd.read_csv("data/Dataset/Fact_DemandInputForecast.csv")
    unique_items = demand_df[['Item.[Item]', 'product_name', 'Location.[Location]']].drop_duplicates()
    
    data = []
    for i in range(num_records):
        sku_row = unique_items.sample(1).iloc[0]
        sku_id = sku_row['Item.[Item]']
        prod_name = sku_row['product_name']
        region = sku_row['Location.[Location]']
        dc = f"{region} DC - {random.choice(['01', '02', '03'])}"
        
        on_hand = random.uniform(1000, 50000)
        in_transit = on_hand * random.uniform(0.1, 0.4)
        safety_stock = on_hand * 0.15
        max_stock = on_hand * 2.5
        carrying_cost = random.uniform(1.5, 4.5)
        days_of_supply = random.randint(10, 60)
        last_rep = (datetime(2026, 3, 20) - timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d")
        
        data.append({
            "raw_product": prod_name,
            "dc": dc,
            "on_hand_units": on_hand,
            "demand_forecast": on_hand * 1.1,
            "safety_stock": safety_stock,
            "sku": sku_id,
            "utilization": random.uniform(60, 90),
            "velocity": random.uniform(0.5, 5.0),
            "inv_cluster": random.randint(1, 3),
            # Additional POC Columns
            "region": region,
            "in_transit_units": in_transit,
            "safety_stock_level": safety_stock,
            "max_stock_level": max_stock,
            "days_of_supply": days_of_supply,
            "carrying_cost_per_unit": carrying_cost,
            "last_replenishment_date": last_rep
        })
        
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_InventorySnapshot.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_procurement_forecast():
    print("Generating procurement records (Fact_ProcurementForecast.csv)...")
    demand_df = pd.read_csv("data/Dataset/Fact_DemandInputForecast.csv")
    unique_items = demand_df[['Item.[Item]', 'Location.[Location]']].drop_duplicates()
    
    suppliers = ["Saigon Premium", "Guangzhou Footwear", "Chennai Textiles", "Dhaka Garments", "Monterrey Logistics", "Jakarta Apparel"]
    
    data = []
    for i in range(1000):
        row = unique_items.sample(1).iloc[0]
        data.append({
            "Supplier.[Supplier Location]": random.choice(suppliers),
            "Version.[Version Name]": "Baseline FY26",
            "Location.[Location]": row['Location.[Location]'],
            "Item.[Item]": row['Item.[Item]'],
            "W Procurement Total Requirements": random.uniform(1000, 10000)
        })
        
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_ProcurementForecast.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_accuracy_data():
    print("Generating accuracy records (Fact_AccuracyAndMAPE.csv)...")
    demand_df = pd.read_csv("data/Dataset/Fact_DemandInputForecast.csv")
    unique_items = demand_df[['Item.[Item]', 'Location.[Location]']].drop_duplicates()
    
    data = []
    for i in range(len(unique_items)):
        row = unique_items.iloc[i]
        data.append({
            "Version.[Version Name]": "Baseline FY26",
            "Location.[Location]": row['Location.[Location]'],
            "Item.[Item]": row['Item.[Item]'],
            "forecast_accuracy": random.uniform(0.85, 0.98),
            "baseline_forecast": random.uniform(500, 20000),
            "actual_sales": random.uniform(500, 20000)
        })
        
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_AccuracyAndMAPE.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_supplier_data():
    print("Generating supplier records (Fact_SupplierCapacity.csv)...")
    suppliers = [
        ("VNM-001", "Saigon Premium", "Vietnam", "Footwear Assembly"),
        ("CHN-002", "Guangzhou Footwear", "China", "Footwear Assembly"),
        ("IND-003", "Chennai Textiles", "India", "Apparel Fabrics"),
        ("BGD-004", "Dhaka Garments", "Bangladesh", "Finished Apparel"),
        ("MEX-005", "Monterrey Logistics", "Mexico", "Footwear Assembly"),
        ("IDN-006", "Jakarta Apparel", "Indonesia", "Apparel Fabrics")
    ]
    
    data = []
    for s_id, s_name, country, cat in suppliers:
        data.append({
            "supplier_id": s_id,
            "supplier_name": s_name,
            "country": country,
            "product_category": cat,
            "weekly_capacity_units": random.randint(50000, 150000),
            "current_utilization": random.uniform(0.6, 0.9),
            "lead_time_days": random.randint(14, 35),
            "lead_time_std_days": random.randint(2, 6),
            "quality_score": round(random.uniform(4.0, 4.9), 1),
            "cost_per_unit": round(random.uniform(10.0, 25.0), 2),
            "co2_per_unit_kg": round(random.uniform(2.0, 5.0), 2),
            "compliance_rating": random.choice(["A", "A-", "B+"])
        })
        
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_SupplierCapacity.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_external_signals():
    print("Generating external signals (Fact_MarketSignals.csv)...")
    signals = ["Social Media Surge", "Weather Impact", "Competitor Promo", "Search Trend"]
    data = []
    for i in range(100):
        data.append({
            "event_type": random.choice(signals),
            "intensity": round(random.uniform(5.0, 9.5), 1),
            "days_to_impact": random.randint(3, 21),
            "confidence_score": round(random.uniform(0.7, 0.99), 2),
            "source": random.choice(["Instagram", "TikTok", "Google Trends", "NOAA", "Market Intelligence"]),
            # Additional POC Columns
            "date": (datetime(2026, 3, 14) + timedelta(days=random.randint(0, 15))).strftime("%Y-%m-%d"),
            "product_category": random.choice(["Air Max", "Running Apparel", "Basketball Shoes"]),
            "region": random.choice(REGIONS)
        })
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_MarketSignals.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_constraints_data():
    print("Generating constraints (Fact_GlobalConstraints.csv)...")
    data = [
        {"constraint_type": "budget", "entity": "GLOBAL-FY26Q4", "description": "Max freight budget", "limit_value": 750000, "unit": "USD", "start_date": "2026-03-01", "end_date": "2026-05-31", "constraint_id": "COST-001"},
        {"constraint_type": "capacity", "entity": "Memphis-DC01", "description": "Max weekly outbound", "limit_value": 250000, "unit": "units", "start_date": "2026-03-01", "end_date": "2026-12-31", "constraint_id": "CAP-001"},
        {"constraint_type": "sustainability", "entity": "ASIA-TO-NA", "description": "Max CO2 per unit", "limit_value": 4.0, "unit": "kg", "start_date": "2026-03-01", "end_date": "2026-12-31", "constraint_id": "SUS-001"}
    ]
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_GlobalConstraints.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_ground_truth():
    print("Generating ground truth (Fact_GroundTruth.csv)...")
    data = [
        {"scenario_id": "SCN-001", "scenario_type": "Demand Surge", "description": "Air Max NA spike", "preferred_action": "Scenario_C_Hybrid", "expected_outcome": "Maintain 95% service level"},
        {"scenario_id": "SCN-002", "scenario_type": "Inventory Rebalance", "description": "Denver to Atlanta transfer", "preferred_action": "Transfer_6500_Units", "expected_outcome": "Zero stockout risk"},
        {"scenario_id": "SCN-003", "scenario_type": "Supplier Disruption", "description": "Bangladesh delay", "preferred_action": "Scenario_4_Expedite", "expected_outcome": "Limit delay to 14 days"}
    ]
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_GroundTruth.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_actual_lag_forecast():
    print("Generating actual vs lag forecast records (Fact_ActualAndLagForecast.csv)...")
    demand_df = pd.read_csv("data/Dataset/Fact_DemandInputForecast.csv")
    unique_items = demand_df[['Item.[Item]', 'Location.[Location]', 'Sales Domain.[Customer Group]']].drop_duplicates()
    
    data = []
    for i in range(min(len(unique_items), 2000)):
        row = unique_items.iloc[i]
        actual = random.uniform(500, 20000)
        data.append({
            "Version.[Version Name]": "Baseline FY26",
            "Location.[Location]": row['Location.[Location]'],
            "Sales Domain.[Customer Group]": row['Sales Domain.[Customer Group]'],
            "Time.[Partial Week]": "2026-W12",
            "Item.[Item]": row['Item.[Item]'],
            "Actual 12 Weeks": actual * 3,
            "Actual 4 Weeks": actual,
            "Actual 8 Weeks": actual * 2,
            "Actual External": actual * 0.1,
            "Actual Final": actual,
            "Published Final Fcst Lag1 12weeks": actual * 1.1 * 3,
            "Published Final Fcst Lag1 4weeks": actual * 1.1,
            "Published Final Fcst Lag1 8weeks": actual * 1.1 * 2,
            "Published Final Fcst Lag1 External": actual * 0.05,
            "Published Final Fcst Lag1 Final": actual * 1.1
        })
        
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_ActualAndLagForecast.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_procurement_forecast_with_demand_type():
    print("Generating procurement with demand type (Fact_ProcurementForecastWithDemandType.csv)...")
    demand_df = pd.read_csv("data/Dataset/Fact_DemandInputForecast.csv")
    unique_items = demand_df[['Item.[Item]', 'Location.[Location]']].drop_duplicates()
    suppliers = ["Saigon Premium", "Guangzhou Footwear", "Chennai Textiles", "Dhaka Garments", "Monterrey Logistics", "Jakarta Apparel"]
    
    data = []
    for i in range(1000):
        row = unique_items.sample(1).iloc[0]
        qty = random.uniform(1000, 10000)
        data.append({
            "Activity3.[Activity3]": "PROD",
            "Demand Type.[Demand Type]": random.choice(["FIRM", "FORECAST"]),
            "Supplier.[Supplier Location]": random.choice(suppliers),
            "Version.[Version Name]": "Baseline FY26",
            "Activity1.[Activity1]": "CUT",
            "Activity2.[Activity2]": "SEW",
            "Documents.[OrderlineID]": f"PO-{random.randint(10000, 99999)}",
            "Location.[Location]": row['Location.[Location]'],
            "Time.[Week]": "2026-W14",
            "Item.[Item]": row['Item.[Item]'],
            "W Procurement Forecast Due to Forecast": qty * 0.7,
            "W Procurement Forecast Due to Orders": qty * 0.3,
            "W Procurement Forecast Intermediate with Demand Type Input To R": qty,
            "W Procurement Forecast With Demand Type": qty,
            "W Procurement Forecast With Demand Type within Lead Time": qty * 0.5
        })
        
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_ProcurementForecastWithDemandType.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_exclude_excess_forecast():
    print("Generating exclude excess forecast (Fact_ExcludeExcessForecastInPast.csv)...")
    data = [{
        "Version.[Version Name]": "Baseline FY26",
        "Location.[Location]": "GLOBAL",
        "Item.[Item]": "ALL",
        "Exclude Excess": 1
    }]
    df = pd.DataFrame(data)
    output_path = "data/Dataset/Fact_ExcludeExcessForecastInPast.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    # Ensure full randomness by resetting seed logic if any
    random.seed(None)
    np.random.seed(None)
    
    generate_demand_data(TARGET_SKUS)
    generate_inventory_data(5000)
    generate_procurement_forecast()
    generate_accuracy_data()
    generate_actual_lag_forecast()
    generate_procurement_forecast_with_demand_type()
    generate_exclude_excess_forecast()
    generate_supplier_data()
    generate_external_signals()
    generate_constraints_data()
    generate_ground_truth()
