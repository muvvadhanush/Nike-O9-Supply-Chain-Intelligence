from typing import List
from schema.models import Signal, InventoryItem

class UseCaseClassifier:
    """Classifies the current state into one of three primary use cases."""
    @staticmethod
    def classify(signals: List[Signal], inventory: List[InventoryItem], logs: list = None) -> tuple[str, str]:
        if logs is None: logs = []
        
        # Detect Surge: High intensity social media/search + demand gaps
        surge_keywords = ["trend", "social", "influencer", "search"]
        urge_signals = [s for s in signals if any(t in s.event.lower() for t in surge_keywords)]
        if urge_signals:
            if any((i.demand > i.on_hand * 1.5) for i in inventory):
                logs.append("Triggering DEMAND_SURGE Analysis via specialized classifier.")
                return "DEMAND_SURGE", "Demand Surge Classifier"
        
        # Detect Disruption: High intensity strike/weather/logistics signals
        disrupt_keywords = ["strike", "port", "weather", "typhoon", "shortage", "disruption"]
        disrupt_signals = [s for s in signals if any(t in s.event.lower() for t in disrupt_keywords)]
        if disrupt_signals:
            logs.append(f"Network disruption detected: {disrupt_signals[0].event}.")
            return "SUPPLIER_DISRUPTION", "Supplier Disruption Classifier"
        
        # Default to Rebalancing if significant stock delta exists between DCs
        on_hands = [i.on_hand for i in inventory]
        if on_hands and (max(on_hands) - min(on_hands) > 5000):
            logs.append(f"Inter-node stock variance identified ({max(on_hands)-min(on_hands):,} units).")
            return "INVENTORY_REBALANCING", "Inventory Rebalancing Classifier"
            
        logs.append("No critical triggers found. Defaulting to General Optimization.")
        return "GENERAL_OPTIMIZATION", "General Use Case Classifier"
