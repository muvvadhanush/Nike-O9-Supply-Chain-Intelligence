import os
import pandas as pd
import numpy as np
import json
from core.orchestration import run_orchestration, load_scenarios
from agents.simulation import SimulationAgent
from schema.models import Scenario

def test_data_corruption():
    """Adversarial Test 1: Corrupted/Empty CSV Data"""
    print("--- Red Team Test: Data Corruption ---")
    # Backup original
    path = "data/datasets/demand_planning_dataset.csv"
    backup = "data/datasets/demand_planning_dataset.csv.bak"
    if os.path.exists(path):
        os.rename(path, backup)
    
    # Create empty/corrupted file
    with open(path, "w") as f:
        f.write("sku,product_name,category\nBAD_SKU,,") # Missing columns, empty cells
    
    try:
        result = run_orchestration(scenario_id=0)
        print("SUCCESS: Orchestration handled corrupted CSV gracefully.")
    except Exception as e:
        print(f"FAILURE: Orchestration crashed on corrupted CSV: {e}")
    finally:
        # Restore
        if os.path.exists(backup):
            if os.path.exists(path): os.remove(path)
            os.rename(backup, path)

def test_concurrent_disruptions():
    """Adversarial Test 2: Double-Shock Scenario"""
    print("\n--- Red Team Test: Concurrent Disruptions ---")
    # Simulate a scenario where both cost and risk are maxed out
    stress_scenarios = [
        {
            "id": "STRESS-01", 
            "name": "Global Port Strike + Suez Blockage", 
            "mode": "SEA", 
            "carrier": "Fallback", 
            "lead_time": 60, 
            "cost": 2500000.0, 
            "fill_rate": 0.1, 
            "co2_uplift": 0.2, # Added missing field
            "risk": 0.95, 
            "is_inviable": False
        }
    ]
    
    sim_agent = SimulationAgent(stress_scenarios)
    logs = []
    results = sim_agent.simulate("SUPPLIER_CONSTRAINT", logs)
    
    for s in results:
        print(f"Scenario: {s.name}")
        print(f"Base Score: {s.score:.2f}")
        print(f"Monte Carlo Avg: {s.monte_avg:.2f} (Min: {s.monte_min:.1f}, Max: {s.monte_max:.1f})")
        if s.is_inviable:
            print("SUCCESS: Simulation correctly flagged extreme scenario as INVIABLE.")
        else:
            print("WARNING: Simulation did not flag extreme scenario as inviable.")

def test_boundary_values():
    """Adversarial Test 3: Zero/Negative Values"""
    print("\n--- Red Team Test: Boundary Values ---")
    extreme_scenarios = [
        {
            "id": "ZERO-01", 
            "name": "Zero Cost Plan", 
            "mode": "GROUND", 
            "carrier": "None", 
            "lead_time": 0, 
            "cost": 0.0, 
            "fill_rate": 0.0, 
            "co2_uplift": 0.0, # Added missing field
            "risk": 1.0, 
            "is_inviable": False
        }
    ]
    try:
        sim_agent = SimulationAgent(extreme_scenarios)
        logs = []
        results = sim_agent.simulate("DEMAND_SURGE", logs)
        print("SUCCESS: Simulation handled zero-values without ZeroDivisionError.")
    except Exception as e:
        print(f"FAILURE: Simulation crashed on zero-eval: {e}")

if __name__ == "__main__":
    test_data_corruption()
    test_concurrent_disruptions()
    test_boundary_values()
