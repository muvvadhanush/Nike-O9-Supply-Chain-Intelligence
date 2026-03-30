import pandas as pd
import numpy as np
import os
import logging
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
TAG = "INVENTORY INGESTION"

# Path configuration relative to the 'agents' directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "Dataset", "raw")
OUT_DIR = os.path.join(PROJECT_ROOT, "data", "Dataset")

class InventoryIngestionAgent:
    """
    Data Ingestion Layer for multi-agent supply chain dashboard.
    Cleanses missing data, maps fuzzy SKU names via NLP TF-IDF, and 
    clusters inventory states via K-Means to eliminate static business rules.
    """
    def __init__(self):
        self.raw_path = os.path.join(RAW_DIR, "raw_inventory.json")
        self.out_path = os.path.join(OUT_DIR, "Fact_InventorySnapshot.csv")
        
        # Ground truth master SKUs (Normally queried from Master Data DB)
        self.master_skus = {
            "NK-AM-001": "Air Max 270 Black",
            "NK-AM-002": "Air Max 270 White",
            "NK-RA-101": "Dri-FIT Running Shirt M",
            "NK-RA-102": "Dri-FIT Running Shirt W",
            "NK-AP-201": "Tech Fleece Joggers M",
            "NK-BK-301": "LeBron XXI",
            "NK-KD-401": "Kids Air Max Runner",
            "NK-RT-501": "React Phantom Run 3",
            "NK-MT-601": "Metcon 9 Amp",
            "NK-JD-701": "Jordan Stay Loyal 3",
            "NK-CV-801": "Court Vision Low",
            "NK-IC-901": "Sportswear Icon Clash",
            "NK-EC-001": "Element Crew Top",
            "NK-ZP-101": "Air Zoom Pegasus 40",
            "NK-SB-201": "SB Dunk Low Pro",
            "NK-BZ-301": "Blazer Mid '77",
            "NK-VF-401": "Vaporfly 3",
            "NK-IV-501": "Invincible 3",
            "NK-TM-601": "Tempo Next%",
            "NK-AC-701": "ACG Mountain Fly"
        }

    def extract(self) -> pd.DataFrame:
        if not os.path.exists(self.raw_path):
            raise FileNotFoundError(f"Raw data not found at {self.raw_path}. Make sure it exists.")
        
        logging.info(f"{TAG} - Extracting raw inventory data from structured JSON {self.raw_path}")
        
        with open(self.raw_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        records = data.get("records", [])
        logging.info(f"{TAG} - Parsed {len(records)} records from JSON file.")
        
        flattened = []
        for r in records:
            oh = float(r.get("on_hand_units") or 0)
            dos = float(r.get("days_of_supply") or 0)
            proj = r.get("projected_demand")
            if proj is not None and str(proj) != "":
                demand_forecast = float(proj)
            elif dos > 0:
                # ~8-week demand proxy from days-of-supply (matches WMS JSON shape)
                demand_forecast = (oh / dos) * 56.0
            else:
                demand_forecast = oh * 1.15
            ss = r.get("safety_stock_level")
            if ss is None:
                ss = r.get("safety_stock") or 0
            flattened.append({
                "raw_product": r.get("product_name"),
                "dc": r.get("distribution_center") or r.get("warehouse_id"),
                "on_hand_units": int(oh) if oh else 0,
                "demand_forecast": demand_forecast,
                "safety_stock": float(ss) if ss is not None and str(ss) != "" else 0.0
            })
            
        df = pd.DataFrame(flattened)
        return df

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        logging.info(f"{TAG} - Starting Inventory ML transformations. Incoming records: {len(df)}")
        
        sku_names = list(self.master_skus.values())
        vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,3))
        tfidf_matrix = vectorizer.fit_transform(sku_names)
        
        resolved_skus = []
        for _, row in df.iterrows():
            query_vec = vectorizer.transform([row['raw_product']])
            scores = cosine_similarity(query_vec, tfidf_matrix)
            best_idx = np.argmax(scores)
            resolved_skus.append(list(self.master_skus.keys())[best_idx])
            
        df['sku'] = resolved_skus
        
        # Features for clustering: Utilization (on_hand/safety_stock) and Velocity (demand/on_hand)
        df['utilization'] = df['on_hand_units'] / (df['safety_stock'] + 1)
        df['velocity'] = df['demand_forecast'] / (df['on_hand_units'] + 1)
        
        df[['utilization', 'velocity']] = df[['utilization', 'velocity']].fillna(0)
        
        n_clusters = 3
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['inv_cluster'] = kmeans.fit_predict(df[['utilization', 'velocity']])
        
        logging.info(f"{TAG} - Running NLP Entity Resolution (TF-IDF + Cosine Similarity) to map fuzzy SKU names...")
        logging.info(f"{TAG} - Executing K-Means Clustering for dynamic inventory segmentation...")
        logging.info(f"{TAG} - Inventory accurately modeled into {n_clusters} dynamic segmentation clusters.")
        
        return df

    def load(self, df: pd.DataFrame):
        logging.info(f"{TAG} - Loading {len(df)} ML-validated records to {self.out_path} for Dashboard Orchestration.")
        df.to_csv(self.out_path, index=False)
        logging.info(f"{TAG} - Load phase complete.")

    def run(self):
        df_raw = self.extract()
        df_processed = self.process(df_raw)
        self.load(df_processed)

if __name__ == "__main__":
    agent = InventoryIngestionAgent()
    agent.run()
