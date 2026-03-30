from typing import List, Dict
from schema.models import InventoryItem

class InventoryAnalysisAgent:
    """Evaluates SKU-level inventory health based on the specific use case."""
    def __init__(self, inventory: List[InventoryItem]):
        self.inventory = inventory

    def analyze(self, use_case: str, logs: list) -> Dict:
        logs.append(f"Total inventory SKUs monitored: {len(self.inventory)}")
        logs.append(f"Performing {use_case} specific analysis...")
        at_risk = [i for i in self.inventory if i.demand > i.on_hand]
        
        if use_case == "INVENTORY_REBALANCING":
            # Focus on DC delta
            sorted_inv = sorted(self.inventory, key=lambda x: x.on_hand)
            source = sorted_inv[-1] # Highest stock
            target = sorted_inv[0]  # Lowest stock
            delta = source.on_hand - target.on_hand
            logs.append(f"Found rebalance opportunity: {source.sku} ({source.on_hand}) -> {target.sku} ({target.on_hand})")
            logs.append(f"Calculated delta: {delta} units available for inter-node transfer.")
            return {"type": "rebalance", "source": source, "target": target, "at_risk_count": len(at_risk)}
            
        logs.append(f"Identified {len(at_risk)} SKUs with stockout risk (Demand > On-Hand).")
        return {"type": "stockout_risk", "at_risk": at_risk, "at_risk_count": len(at_risk)}
