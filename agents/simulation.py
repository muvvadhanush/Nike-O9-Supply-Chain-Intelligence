import pandas as pd
import numpy as np
from typing import List, Dict
from sklearn.ensemble import RandomForestRegressor
from schema.models import Scenario
from agents.constants import BUDGET_CAP

class SimulationAgent:
    """
    Simulates multi-modal logistics scenarios using a Random Forest ML model.
    Predicts the ROI/Score of a scenario based on cost, lead time, and risk.
    """
    def __init__(self, scenarios_data: List[Dict], iterations: int = 500):
        self.scenarios_data = scenarios_data
        self.iterations = iterations
        self.total_simulations_run = 0
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self._train_model()

    def _train_model(self):
        """
        Trains the Random Forest on historical Fact data if available, 
        otherwise falls back to a synthetic baseline.
        """
        import os
        from core.orchestration import DATASET_DIR
        
        path = os.path.join(DATASET_DIR, "Fact_DemandInputForecast.csv")
        
        if os.path.exists(path):
            df = pd.read_csv(path).fillna(0)
            # Use real quantities and buffer levels as features
            # qty_col = 'D Base Forecast Quantity'
            # buff_col = 'D Buff1 Forecast Quantity'
            # For simplicity in this POC integration, we'll map them to cost/lt proxies
            costs = df['D Base Forecast Quantity'].values * 150 # Proxy for cost
            lead_times = np.random.randint(5, 25, len(df)) # Placeholder for real LT if not in fact
            risks = (df['D Buff1 Forecast Quantity'] / df['D Base Forecast Quantity']).fillna(0.1).values
            
            fill_rates = 1.0 - (risks * 0.3)
            scores = (fill_rates * 100) / (costs / BUDGET_CAP)
            
            X = np.column_stack([costs, lead_times, risks])
            y = scores
        else:
            # Synthetic Training Data Fallback
            np.random.seed(42)
            costs = np.random.uniform(100000, 900000, 200)
            lead_times = np.random.randint(1, 30, 200)
            risks = np.random.uniform(0.0, 0.5, 200)
            fill_rates = 1.0 - (risks * 0.5) - (lead_times * 0.005)
            scores = (fill_rates * 100) / (costs / BUDGET_CAP)
            X = np.column_stack([costs, lead_times, risks])
            y = scores
        
        self.model.fit(X, y)

    def simulate(self, use_case: str, logs: list) -> List[Scenario]:
        logs.append(f"Running Simulation Agent for {use_case}...")
        scenarios = []
        self.total_simulations_run = 0
        
        for s_data in self.scenarios_data:
            cost = float(s_data.get('cost', 500000))
            lt = float(s_data.get('lead_time', 10))
            risk = float(s_data.get('risk', 0.2))
            mode = s_data.get('mode', 'SEA')
            
            # 1. Baseline RF Prediction
            features = np.array([[cost, lt, risk]])
            baseline_score = self.model.predict(features)[0]
            
            # 2. Monte Carlo Stochastic Stress-Test (Dynamic Iterations)
            iteration_scores = []
            
            for i in range(self.iterations):
                # Add stochastic noise (Jitters)
                j_cost = cost * (1 + np.random.normal(0, 0.04)) # 4% cost variance
                j_lt = max(1, lt + np.random.normal(0, 1.2))    # 1.2d lead-time jitter
                j_risk = max(0, min(1, risk + np.random.normal(0, 0.03))) # 3% risk jitter
                
                # ADVERSARIAL: "Black Swan" Event (5% Probability)
                if np.random.random() < 0.05:
                    j_lt *= 3.0   # Extreme port congestion / strike
                    j_cost *= 2.0  # Emergency air-charter premiums
                    j_risk = 0.9   # Near-certain failure
                
                j_features = np.array([[j_cost, j_lt, j_risk]])
                j_score = self.model.predict(j_features)[0]
                
                # Apply Scenario multipliers to each iteration
                if use_case == "DEMAND_SURGE" and mode == "AIR":
                    j_score *= 1.2 
                elif use_case == "INVENTORY_REBALANCING" and mode == "TRUCK":
                    j_score *= 1.5
                elif use_case == "SUPPLIER_CONSTRAINT" and mode == "SEA":
                    j_score *= 0.8  
                
                iteration_scores.append(float(j_score))
                self.total_simulations_run += 1

            # 3. Sustainability (SCSI) Scoring
            # AIR: ~15.4 kg CO2/unit, SEA: ~4.0 kg CO2/unit, TRUCK: ~5.2 kg CO2/unit
            if mode == "AIR":
                co2_uplift = 11.4
            elif mode == "TRUCK":
                co2_uplift = 1.2
            else:
                co2_uplift = 0.0
            
            # 4. Compile Scenario with Statistical Distribution
            scenario = Scenario(**s_data)
            scenario.co2_uplift = co2_uplift
            scenario.score = float(baseline_score)
            scenario.monte_min = min(iteration_scores)
            scenario.monte_max = max(iteration_scores)
            scenario.monte_avg = sum(iteration_scores) / len(iteration_scores)
            scenario.monte_std = float(np.std(iteration_scores))
            
            # 5. Dynamic Confidence Score (0-100)
            # Confidence is high if standard deviation is low relative to the average
            cv = (scenario.monte_std / scenario.monte_avg) if scenario.monte_avg > 0 else 1.0
            scenario.regret_index = float(cv * 100) # POC specific mapping
            
            # Heuristic: 95% confidence if CV is < 0.1, degrades as CV increases
            confidence = max(60, min(98, int(100 - (cv * 150))))
            scenario.otif = float(confidence) # Using OTIF field as proxy for confidence score in some UI parts
            
            logs.append(f"Modeling {scenario.name}: Base Score {scenario.score:.2f}, CO2 Uplift: {co2_uplift}kg/unit")
            logs.append(f"Ran {iterations} iterations. Distribution: {scenario.monte_min:.1f} to {scenario.monte_max:.1f}")
            
            if scenario.cost > BUDGET_CAP:
                logs.append(f"SCENARIO INVIABLE: Cost ${scenario.cost:,.0f} exceeds Cap ${BUDGET_CAP:,.0f}")
                scenario.is_inviable = True
                scenario.score = 0
            
            scenarios.append(scenario)
            
        logs.append(f"Analysis complete. {len(scenarios)} multi-modal scenarios modeled.")
        return scenarios
