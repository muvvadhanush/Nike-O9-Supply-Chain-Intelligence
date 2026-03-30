from typing import List
from schema.models import Signal

class SignalAnalysisAgent:
    """Analyzes market signals for high-intensity disruptions."""
    def __init__(self, signals: List[Signal], signal_threshold: float = 7.0):
        self.signals = signals
        self.signal_threshold = signal_threshold

    def analyze(self, use_case: str, logs: list) -> List[Signal]:
        logs.append(f"Total signals received: {len(self.signals)}")
        if use_case == "INVENTORY_REBALANCING":
            logs.append("Internal rebalancing detected. External signals are secondary.")
            return []
            
        logs.append(f"Analyzing signals for {use_case}...")
        logs.append(f"Applying intensity threshold: > {self.signal_threshold}")
        high_intensity = [s for s in self.signals if s.intensity > self.signal_threshold]
        
        filtered_count = len(self.signals) - len(high_intensity)
        logs.append(f"Filtered {filtered_count} signals below threshold.")
        logs.append(f"{len(high_intensity)} critical signals remaining for analysis.")
        
        for s in high_intensity[:2]:
            logs.append(f"⚡ HIGH PRIORITY: {s.event} (Score: {s.intensity:.1f})")
        return high_intensity
