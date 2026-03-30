import json
import os
import random
import numpy as np
from datetime import datetime, timedelta

# Base directory for the workspace
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "Dataset", "raw")

# Ensure raw directory exists
os.makedirs(RAW_DIR, exist_ok=True)

def generate_mock_log_signals(num_records=200):
    """Generates synthetic market signals in a .log format with noise and anomalies."""
    output_path = os.path.join(RAW_DIR, "raw_external_signals.log")
    
    event_types = ['competitor_pricing_change', 'weather_impact', 'sports_event_trigger', 
                   'influencer_endorsement', 'social_media_trend', 'economic_indicator', 'search_trend_spike']
    categories = ['Apparel', 'Footwear', 'Equipment']
    regions = ['North America', 'Europe', 'Asia Pacific', 'South America']
    sources = ['Bloomberg', 'Reuters', 'NOAA', 'AccuWeather API', 'TikTok Trends', 'Instagram Insights', 'Google Trends', 'ESPN Analytics']
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# ============================================================\n")
        f.write("# Nike External Intelligence Hub — Signal Ingestion Log\n")
        f.write("# System  : Nike-EIH v2.1.0\n")
        f.write(f"# Export  : {datetime.now().isoformat()}\n")
        f.write("# Schema  : signals_v3 (key=value pairs embedded in log body)\n")
        f.write("# ============================================================\n\n")
        
        for i in range(num_records):
            # Operational noise lines (heartbeats, checkpoints) every 20 records
            if i % 25 == 0:
                ts = (datetime.now() - timedelta(minutes=random.randint(1, 1000))).isoformat()
                f.write(f"[{ts}Z] [DEBUG] [ingest-node-03] heartbeat=true uptime=\"{random.randint(100, 10000)}s\" memory_mb={random.randint(1000, 8000)} cpu_pct={random.uniform(1, 100):.1f}\n")
            
            if i % 40 == 0:
                ts = (datetime.now() - timedelta(minutes=random.randint(1, 1000))).isoformat()
                f.write(f"[{ts}Z] [INFO]  [ingest-node-03] batch_checkpoint seq={random.randint(1000000, 9999999)} records_flushed={random.randint(1, 200)} queue_depth={random.randint(0, 500)}\n")

            # Main signal generation
            stype = random.choice(event_types)
            cat = random.choice(categories)
            reg = random.choice(regions)
            src = random.choice(sources)
            val = round(np.random.uniform(1.0, 200.0), 2)
            conf = round(np.random.uniform(0.6, 1.0), 4)
            ts = (datetime.now() - timedelta(days=random.randint(0, 90))).isoformat()
            
            # Inject outliers (Intensity spikes)
            if random.random() < 0.05:
                val = random.choice([1000.0, 500.0, 2000.0, 1500.0])
            
            # Log format construction
            log_line = (f"[{ts}Z] [{random.choice(['INFO', 'DEBUG', 'WARN', 'ERROR'])}] [ingest-node-01] "
                        f"signal_type=\"{stype}\" product_category=\"{cat}\" region=\"{reg}\" "
                        f"event_date=\"{ts[:10]}\" signal_value={val} source=\"{src}\" confidence={conf} | "
                        f"record_id=\"SIG-{i:05d}\"\n")
            f.write(log_line)
            
        f.write("\n# EOF — total signal records produced\n")

    print(f"Generated raw signal log: {output_path}")

def generate_mock_json_inventory(num_records=300):
    """Generates synthetic inventory snapshots in a .json format with fuzzy names and clusters."""
    output_path = os.path.join(RAW_DIR, "raw_inventory.json")
    
    master_skus = [
        "Air Max 270 Black", "Air Max 270 White", "Dri-FIT Running Shirt M", 
        "Dri-FIT Running Shirt W", "Tech Fleece Joggers M", "LeBron XXI", "Kids Air Max Runner",
        "React Phantom Run 3", "Metcon 9 Amp", "Jordan Stay Loyal 3", "Court Vision Low",
        "Sportswear Icon Clash", "Element Crew Top", "Air Zoom Pegasus 40", "SB Dunk Low Pro",
        "Blazer Mid '77", "Vaporfly 3", "Invincible 3", "Tempo Next%", "ACG Mountain Fly"
    ]
    
    fuzzy_variations = {
        "Air Max 270 Black": ["AirMax 270 Blk", "Air Max 270 - Black", "Nike Air Max 270 B"],
        "Dri-FIT Running Shirt M": ["Dry Fit Run Shirt", "Dri-FIT M Running", "DF Running Shirt (M)"],
        "Tech Fleece Joggers M": ["TechFleece Jogger", "Tech Fleece M", "Joggers Tech M"]
    }
    
    dcs = ["Rotterdam Distribution Center", "Memphis Distribution Center", "Los Angeles Distribution Center", "Barcelona Distribution Center", "Denver Distribution Center"]
    regions = {"Rotterdam Distribution Center": "Europe", "Memphis Distribution Center": "North America", 
               "Los Angeles Distribution Center": "North America", "Barcelona Distribution Center": "Europe", 
               "Denver Distribution Center": "North America"}

    records = []
    for i in range(num_records):
        master_name = random.choice(master_skus)
        # 30% fuzzy naming
        if master_name in fuzzy_variations and random.random() < 0.3:
            reported_name = random.choice(fuzzy_variations[master_name])
        else:
            reported_name = master_name
            
        dc = random.choice(dcs)
        
        # Base distributions for clustering
        on_hand = int(np.random.normal(15000, 10000))
        on_hand = max(100, on_hand)
        
        # Variance to create distinct segments (K-Means)
        roll = random.random()
        if roll < 0.15: # Stagnant
            on_hand = int(on_hand * 3.0)
            dos = round(np.random.uniform(60, 120), 1)
        elif roll < 0.30: # Critical
            on_hand = int(on_hand * 0.2)
            dos = round(np.random.uniform(1, 10), 1)
        else:
            dos = round(np.random.uniform(11, 59), 1)

        records.append({
            "product_name": reported_name,
            "distribution_center": dc,
            "region": regions[dc],
            "on_hand_units": on_hand,
            "safety_stock_level": int(on_hand * 0.15),
            "days_of_supply": dos,
            "internal": {
                "record_uid": f"WH-{i:07d}",
                "dc_code": dc[:3].upper(),
                "audit": {"version": random.randint(1, 10)}
            }
        })

    data = {
        "api_version": "3.4.1",
        "source_system": "Nike WMS Warehouse API",
        "export_timestamp": datetime.now().isoformat() + "Z",
        "total_records": num_records,
        "records": records
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"Generated raw inventory JSON: {output_path}")

if __name__ == "__main__":
    print("Starting Nike Mock Data Generation Overhaul...")
    generate_mock_log_signals(500)
    generate_mock_json_inventory(1500)
    print("Complete.")

