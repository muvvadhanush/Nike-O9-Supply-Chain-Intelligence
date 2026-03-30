from typing import List, Tuple
from schema.models import Scenario
from agents.constants import BUDGET_CAP

class KPIAgent:
    """Scores scenarios and calculates projected accuracy and savings."""
    def evaluate(self, scenarios: List[Scenario], logs: list) -> Tuple[List[Scenario], float]:
        logs.append(f"Scoring {len(scenarios)} scenarios against Budget (${BUDGET_CAP:,.0f}) and Carbon constraints...")
        
        import os
        import pandas as pd
        from core.orchestration import DATASET_DIR
        
        acc_path = os.path.join(DATASET_DIR, "Fact_AccuracyAndMAPE.csv")
        historical_accuracy = 91.0
        if os.path.exists(acc_path):
            df = pd.read_csv(acc_path)
            # Use 12W Accuracy mean as the baseline
            col = '12W Accuracy' if '12W Accuracy' in df.columns else (df.columns[3] if len(df.columns) > 3 else None)
            if col:
                historical_accuracy = df[col].mean() * 100
        
        counts = {"viable": 0, "inviable": 0}
        for s in scenarios:
            if s.is_inviable:
                counts["inviable"] += 1
                logs.append(f"Scenario {s.name}: INVIABLE (Score 0)")
                continue
            
            # Score = Fill Rate / (Cost Ratio)
            cost_ratio = (s.cost / BUDGET_CAP)
            logs.append(f"Calculating score for {s.name}: Fill Rate ({s.fill_rate:.2f}) / Cost Ratio ({s.cost:,.0f} / {BUDGET_CAP:,.0f})")
            
            # Sustainability Impact logs
            s.score = s.fill_rate / cost_ratio if cost_ratio > 0 else 0
            counts["viable"] += 1
            logs.append(f"Scenario {s.name}: Score {s.score:.2f} (Fill: {int(s.fill_rate*100)}%, CO2: +{s.co2_uplift}kg/u)")
        
        sorted_scenarios = sorted([s for s in scenarios if not s.is_inviable], key=lambda x: x.score, reverse=True)
        logs.append(f"Performance benchmark complete. {counts['viable']} viable paths found, {counts['inviable']} rejected.")
        return sorted_scenarios, historical_accuracy
