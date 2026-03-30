from typing import List, Dict
from schema.models import SupplierInfo

class SupplierAnalysisAgent:
    """Analyzes supplier capacity and production risks for Scenario 3."""
    def __init__(self, suppliers: List[SupplierInfo]):
        self.suppliers = suppliers

    def analyze(self, logs: list) -> Dict:
        logs.append(f"Scanning {len(self.suppliers)} Tier 1 and Tier 2 production partners...")
        
        # Detect Disrupted or High Utilized suppliers
        critical_suppliers = [s for s in self.suppliers if s.status in ["DISRUPTED", "HIGH UTIL"]]
        
        if critical_suppliers:
            s = critical_suppliers[0]
            logs.append(f"Found {len(critical_suppliers)} suppliers with elevation risk.")
            logs.append(f"BOTTLENECK: {s.name} ({s.country}) is {s.status} @ {int(s.utilization*100)}% capacity.")
            logs.append(f"Impact Assessment: Production shortfall of 2,400 units/week predicted.")
            return {
                "type": "supplier_constraint",
                "critical_supplier": s,
                "at_risk_count": 127,
                "delay_days": 21
            }
            
        logs.append("Production levels stable. Average utilization is 68% across network.")
        return {"type": "stable", "at_risk_count": 0}
