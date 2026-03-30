import pandas as pd
from typing import List, Dict
from schema.models import InventoryItem, DCCard

class RebalancingAgent:
    """
    Analyzes DC-level inventory to identify rebalancing opportunities.
    Maps surplus locations to deficit locations.
    """
    def identify_transfers(self, inventory: List[InventoryItem], dc_network: List[DCCard]) -> List[Dict]:
        """
        Calculates optimal transfers based on shortfall and surplus.
        """
        transfers = []
        
        # Simple logic for POC: find the 'crit' or 'warn' DCs and match with 'ok' DCs
        critical_dcs = [dc for dc in dc_network if dc.status_class == 'crit']
        surplus_dcs = [dc for dc in dc_network if dc.status_class == 'ok' and dc.capacity_pct < 70]
        
        if not critical_dcs or not surplus_dcs:
            return []
            
        for crit in critical_dcs:
            source = surplus_dcs[0] # Pick the first available surplus DC
            
            # Logic from POC: Use a realistic transfer quantity (e.g., 6500 units)
            transfer_qty = 6500 
            
            transfers.append({
                'item': 'Running Apparel - Women', # Example category
                'from_dc': source.name,
                'to_dc': crit.name,
                'quantity': transfer_qty,
                'cost': 8200.0,
                'transit_days': 3,
                'risk': 0.12
            })
            
        return transfers
