import pandas as pd
import numpy as np
import os
from sklearn.impute import KNNImputer
from sklearn.ensemble import IsolationForest
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
TAG = "SIGNAL INGESTION"

# Path configuration relative to the 'agents' directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "Dataset", "raw")
OUT_DIR = os.path.join(PROJECT_ROOT, "data", "Dataset")

class SignalIngestionAgent:
    """
    Acts as the foundational Data Ingestion Layer for market signals.
    Replaces static thresholds with intelligent Data Quality checks using Traditional ML.
    """
    def __init__(self):
        self.raw_path = os.path.join(RAW_DIR, "raw_external_signals.log")
        self.out_path = os.path.join(OUT_DIR, "Fact_MarketSignals.csv")
        
        # 1. KNN Imputer: Fills missing numeric context intelligently based on feature neighbors
        self.imputer = KNNImputer(n_neighbors=5)
        
        # 2. Isolation Forest: Unsupervised Anomaly Detection for filtering extreme signal spikes
        self.anomaly_detector = IsolationForest(contamination=0.04, random_state=42)

    def extract(self) -> pd.DataFrame:
        import re
        if not os.path.exists(self.raw_path):
            raise FileNotFoundError(f"Raw data not found at {self.raw_path}. Ensure it exists.")
        
        logging.info(f"{TAG} - Extracting raw signal data from unstructured log {self.raw_path}")
        
        parsed_records = []
        kv_pattern = re.compile(r'(\w+)=(?:"([^"]+)"|([^\s|]+))')
        
        with open(self.raw_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or 'signal_type=' not in line:
                    continue
                
                record = {}
                matches = kv_pattern.findall(line)
                for key, val_quoted, val_unquoted in matches:
                    val = val_quoted if val_quoted else val_unquoted
                    record[key] = val
                
                if record:
                    parsed_records.append(record)
                    
        df = pd.DataFrame(parsed_records)
        logging.info(f"{TAG} - Parsed {len(df)} records from log file.")
        
        if 'signal_type' in df.columns:
            df.rename(columns={'signal_type': 'event_type'}, inplace=True)
            
        if 'signal_value' in df.columns:
            df['intensity'] = pd.to_numeric(df['signal_value'], errors='coerce')
        else:
            df['intensity'] = np.nan
            
        if 'confidence' in df.columns:
            df['confidence_score'] = pd.to_numeric(df['confidence'], errors='coerce')
        else:
            df['confidence_score'] = np.nan
            
        df['days_to_impact'] = np.nan
        return df

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        logging.info(f"{TAG} - Starting ML Data Quality Pipeline. Incoming records: {len(df)}")
        
        numeric_cols = ['intensity', 'days_to_impact', 'confidence_score']
        
        for col in numeric_cols:
            if col not in df.columns:
                df[col] = np.nan
        
        partial_cols = [c for c in numeric_cols if df[c].notna().any()]
        full_nan_cols = [c for c in numeric_cols if df[c].isna().all()]
        
        if full_nan_cols:
            logging.info(f"{TAG} - Columns {full_nan_cols} are entirely absent from source. Filling with default 0.")
            for c in full_nan_cols:
                df[c] = 0.0
        
        if partial_cols:
            missing_count = df[partial_cols].isna().sum().sum()
            if missing_count > 0:
                logging.info(f"{TAG} - Detected {missing_count} missing continuous values in {partial_cols}. Applying KNN Imputation...")
                df[partial_cols] = self.imputer.fit_transform(df[partial_cols])
                logging.info(f"{TAG} - Imputation complete. No missing values remain in essential traits.")
            
        logging.info(f"{TAG} - Executing Isolation Forest to detect extreme signal intensity outliers...")
        preds = self.anomaly_detector.fit_predict(df[['intensity']])
        
        outliers_mask = (preds == -1)
        outliers_count = outliers_mask.sum()
        
        if outliers_count > 0:
            logging.info(f"{TAG} - Found {outliers_count} anomalous signals (e.g., intensity data entry errors). Scrubbing from output.")
            df_clean = df[~outliers_mask].copy()
        else:
            df_clean = df.copy()
            
        logging.info(f"{TAG} - Transformation complete. Clean records: {len(df_clean)} / {len(df)}")
        return df_clean

    def load(self, df: pd.DataFrame):
        logging.info(f"{TAG} - Loading {len(df)} model validated signals to {self.out_path} for Multi-Agent Orchestration.")
        
        expected_cols = ['event_type', 'intensity', 'days_to_impact', 'confidence_score', 'source']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        df_final = df[expected_cols]
        df_final.to_csv(self.out_path, index=False)
        logging.info(f"{TAG} - Load phase complete.")

    def run(self):
        df_raw = self.extract()
        df_clean = self.process(df_raw)
        self.load(df_clean)

if __name__ == "__main__":
    agent = SignalIngestionAgent()
    agent.run()
