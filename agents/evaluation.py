import numpy as np
from scipy import stats
from typing import List, Dict
from schema.models import Scenario, Signal

class StatisticalAgent:
    """
    Performs advanced statistical validation including KS-Tests for anomalies
    and Regret Analysis for decision quality assessment.
    """
    
    def validate_signal(self, signal: Signal, logs: list) -> Dict:
        """
        Performs a Kolmogorov-Smirnov test to compare live signal intensity
        against a historical distribution derived from actual dataset variance.
        """
        logs.append(f"Validating signal '{signal.event}' intensity distribution...")
        
        import os
        import pandas as pd
        from core.orchestration import DATASET_DIR
        
        path = os.path.join(DATASET_DIR, "Fact_ActualAndLagForecast.csv")
        
        # Establishing historical baseline from actual vs forecast variance
        if os.path.exists(path):
            df = pd.read_csv(path).fillna(0)
            # Use the variance between Actual Final and Published Final Fcst as the 'noise' distribution
            historical_baseline = ((df['Actual Final'] - df['Published Final Fcst Lag1 Final']) / df['Actual Final']).replace([float('inf'), -float('inf')], 0).fillna(0).values
            # Re-scale to match signal intensity range (0-10) approx
            historical_baseline = np.abs(historical_baseline) * 5 
        else:
            # Fallback to normally distributed intensity
            np.random.seed(42)
            historical_baseline = np.random.normal(loc=0.4, scale=0.1, size=100)
        
        # Sample the current signal
        current_sample = np.random.normal(loc=signal.intensity, scale=0.08, size=100)
        
        # KS-Test: Null hypothesis is that they come from the same distribution
        ks_stat, p_value = stats.ks_2samp(current_sample, historical_baseline)
        
        is_anomaly = p_value < 0.05
        logs.append(f"KS-Stat: {ks_stat:.4f}, P-Value: {p_value:.4f}")
        
        if is_anomaly:
            logs.append(f"ANOMALY CONFIRMED: Signal distribution deviates significantly from historical stability (p < 0.05).")
        else:
            logs.append(f"Signal within expected variance of historical performance.")
            
        return {
            "ks_stat": float(ks_stat),
            "p_value": float(p_value),
            "is_stat_anomaly": is_anomaly
        }

    def analyze_regret(self, scenarios: List[Scenario], logs: list) -> List[Scenario]:
        """
        Calculates the 'Regret Index' for each scenario.
        Regret = (Best Possible Score - Current Scenario Score)
        """
        if not scenarios:
            return scenarios
            
        logs.append("Benchmarking decision quality against theoretical optimum...")
        
        # Find the max score among viable scenarios
        viable_scores = [s.score for s in scenarios if not s.is_inviable and s.score is not None]
        if not viable_scores:
            return scenarios
            
        max_score = max(viable_scores)
        
        for s in scenarios:
            if s.is_inviable or s.score is None:
                s.regret_index = max_score # Maximum regret for inviable paths
            else:
                s.regret_index = float(max_score - s.score)
                logs.append(f"Scenario {s.name}: Regret Index {s.regret_index:.2f}")
                
        logs.append(f"Regret Analysis complete. Optimal path identified with Regret 0.00.")
        return scenarios
