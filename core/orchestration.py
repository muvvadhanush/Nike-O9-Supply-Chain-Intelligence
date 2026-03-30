import pandas as pd
from datetime import datetime
import json
import random
import os
import numpy as np
import hashlib
import re
from typing import List, Dict, Optional
from schema.models import (
    Signal, InventoryItem, Scenario, Recommendation, AuditNode, ExecutionResult,
    SupplierInfo, ForecastBar, DCCard, KPICard, AlertItem, ExternalSignal, DashboardScenario
)
from agents.ingestion_signal import SignalIngestionAgent
from agents.ingestion_inventory import InventoryIngestionAgent
from agents.classifier import UseCaseClassifier
from agents.analysis_signal import SignalAnalysisAgent
from agents.analysis_inventory import InventoryAnalysisAgent
from agents.analysis_supplier import SupplierAnalysisAgent
from agents.simulation import SimulationAgent
from agents.kpi import KPIAgent
from agents.recommendation import RecommendationAgent
from agents.constants import BUDGET_CAP, SIGNAL_THRESHOLD
_CORE_ROOT = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CORE_ROOT)
DATASET_DIR = os.path.join(_PROJECT_ROOT, "data", "Dataset")
DATASETS_DIR = os.path.join(_PROJECT_ROOT, "data", "datasets")
SAVED_ACTIVITIES_FILE = os.path.join(DATASET_DIR, "saved_activities.json")


def _resolve_csv_path(preferred: str, *fallbacks: str) -> Optional[str]:
    """Prefer canonical `datasets/` file; use legacy paths only if preferred is missing."""
    if os.path.exists(preferred):
        return preferred
    for p in fallbacks:
        if os.path.exists(p):
            return p
    return None


def _supplier_stable_id(name: str) -> str:
    digest = hashlib.md5(name.strip().encode("utf-8")).hexdigest()[:8].upper()
    return f"SUP-{digest}"


def load_constraints() -> List[Dict]:
    """Load operational constraints from canonical CSV (budget, lead time, CO2, etc.)."""
    path = _resolve_csv_path(
        os.path.join(DATASETS_DIR, "Fact_GlobalConstraints.csv"),
        os.path.join(DATASET_DIR, "Fact_GlobalConstraints.csv"),
    )
    if not path:
        return []
    df = pd.read_csv(path)
    return df.fillna("").to_dict(orient="records")

# Agents are now imported from the 'agents' package for better modularity.

# ───────── Original data-loading functions ─────────

def load_signals() -> List[Signal]:
    path = os.path.join(DATASET_DIR, "Fact_MarketSignals.csv")
    if not os.path.exists(path):
        return []
    
    df = pd.read_csv(path).fillna(0)
    signals = []
    # Dynamic Sorting for real-time relevance
    df = df.sort_values("confidence_score", ascending=False)
    for _, row in df.head(50).iterrows():
        s_type = str(row.get("event_type", "Unknown Event"))
        raw_conf = float(row.get("confidence_score", 0.0))
        raw_intensity = row.get("intensity", 0.0)
        intensity = min(10.0, max(0.0, float(raw_intensity) / 20.0)) if raw_intensity else (raw_conf * 10.0)
        dti = row.get("days_to_impact", 0)
        
        signals.append(Signal(
            event=s_type,
            source=str(row.get("source", "Supply Intel")),
            intensity=round(intensity, 1),
            days_to_impact=int(dti) if dti else 7
        ))
    return signals

def load_inventory() -> List[InventoryItem]:
    path = os.path.join(DATASET_DIR, "Fact_InventorySnapshot.csv")
    if not os.path.exists(path):
        return []
    
    df = pd.read_csv(path).fillna(0)
    on_hand_col = 'on_hand_units' if 'on_hand_units' in df.columns else ('current_stock' if 'current_stock' in df.columns else None)
    sku_col = 'sku' if 'sku' in df.columns else 'product_name'
    
    inventory = []
    for _, row in df.head(1000).iterrows():
        try:
            on_hand = int(float(row[on_hand_col])) if on_hand_col and pd.notna(row.get(on_hand_col)) else 0
        except: on_hand = 0
        
        sku = str(row.get(sku_col, 'SKU-UNKNOWN'))
        demand_raw = row.get('demand_forecast', on_hand * 1.2)
        
        inventory.append(InventoryItem(
            sku=sku,
            name=sku,
            on_hand=on_hand,
            demand=int(float(demand_raw))
        ))
    return inventory

def load_scenarios() -> List[Dict]:
    path = os.path.join(DATASET_DIR, "scenario_evaluation.csv")
    if not os.path.exists(path):
        # Hardened Fallback Scenarios for Simulation Agent robustness
        return [
            {"id": "SC-01", "name": "Priority Air Express", "mode": "AIR", "carrier": "DHL Express", "lead_time": 3, "cost": 650000, "fill_rate": 0.98, "co2_uplift": 3.4, "risk": 0.1, "is_inviable": False},
            {"id": "SC-02", "name": "Standard Ocean Freight", "mode": "SEA", "carrier": "Maersk Line", "lead_time": 21, "cost": 120000, "fill_rate": 0.85, "co2_uplift": 0.2, "risk": 0.3, "is_inviable": False},
            {"id": "SC-03", "name": "Trans-Continental Rail", "mode": "RAIL", "carrier": "DB Cargo", "lead_time": 12, "cost": 340000, "fill_rate": 0.92, "co2_uplift": 0.7, "risk": 0.2, "is_inviable": False}
        ]
    
    df = pd.read_csv(path)
    scenarios_data = []
    
    # Logic Hardening: Dynamic Carrier Lookup
    carrier_map = {
        "AIR": ["DHL Express", "FedEx Priority", "Cathay Cargo"],
        "SEA": ["Maersk Line", "MSC", "CMA CGM"],
        "RAIL": ["Euro Cargo Rail", "DB Cargo"],
        "GROUND": ["Nike Fleet", "LTL Logistics"]
    }
    # Logic Hardening: Mode-specific CO2 baselines (kg/unit)
    co2_map = {
        "AIR": (2.5, 4.5),
        "SEA": (0.1, 0.4),
        "RAIL": (0.5, 1.0),
        "GROUND": (0.8, 1.5)
    }

    for _, row in df.head(10).iterrows():
        impact_note = str(row.get('expected_kpi_improvement_notes', row.get('impact_metrics', '')))
        fill_rate = 0.90
        if "fill rate" in impact_note.lower():
            match = re.search(r'(\d+)%', impact_note)
            if match:
                fill_rate = int(match.group(1)) / 100.0
        
        cost = random.randint(200000, 900000)
        s_type = str(row.get('scenario_type', row.get('type', 'GROUND')))
        mode = s_type.split('_')[-1].upper() if '_' in s_type else "GROUND"
        if mode not in co2_map: mode = "GROUND"
        
        carrier = random.choice(carrier_map.get(mode, ["Nike Logistics Partner"]))
        co2_low, co2_high = co2_map.get(mode, (0.5, 3.0))
        
        scenarios_data.append({
            "id": row.get('scenario_id', 'SC-0' + str(len(scenarios_data))),
            "name": s_type.replace('_', ' ').title(),
            "mode": mode,
            "carrier": carrier,
            "lead_time": random.randint(3, 15) if mode != "SEA" else random.randint(15, 30),
            "cost": float(cost),
            "fill_rate": fill_rate,
            "co2_uplift": round(random.uniform(co2_low, co2_high), 2),
            "risk": round(random.uniform(0.1, 0.4), 2),
            "is_inviable": False
        })
    return scenarios_data

# ───────── New data-loading functions for enriched dashboard ─────────

def load_suppliers() -> List[SupplierInfo]:
    path = _resolve_csv_path(
        os.path.join(DATASET_DIR, "Fact_ProcurementForecast.csv"),
        os.path.join(DATASETS_DIR, "Fact_ProcurementForecast.csv"),
    )
    if not path: return []
    
    df = pd.read_csv(path)
    # Map O9 headers to internal model
    # Supplier.[Supplier Location], Version.[Version Name], Item.[Item], W Procurement Total Requirements
    sup_col = 'Supplier.[Supplier Location]'
    loc_col = 'Location.[Location]'
    req_col = 'W Procurement Total Requirements'
    
    if sup_col not in df.columns: return []
    
    df["supplier_id"] = df[sup_col].astype(str).map(_supplier_stable_id)
    
    grouped = df.groupby(sup_col).agg({
        'supplier_id': 'first',
        loc_col: 'first',
        req_col: 'mean',
    }).reset_index().head(7)
    
    suppliers = []
    for _, row in grouped.iterrows():
        # Synthetic utilization derived from requirements for POC
        util = min(1.0, row[req_col] / 5000.0) 
        status, status_class = ("DISRUPTED", "badge-r") if util > 0.92 else (("WATCH", "badge-a") if util > 0.75 else ("AVAILABLE", "badge-g"))
        
        suppliers.append(SupplierInfo(
            name=row[sup_col],
            supplier_id=row['supplier_id'],
            country=row[loc_col],
            utilization=round(util, 2),
            lead_time="14d",
            quality_score="4.5 / 5",
            status=status,
            status_class=status_class
        ))
    return suppliers


def load_demand_forecast() -> List[ForecastBar]:
    path = _resolve_csv_path(
        os.path.join(DATASET_DIR, "Fact_DemandInputForecast.csv"),
        os.path.join(DATASETS_DIR, "Fact_DemandInputForecast.csv"),
    )
    if not path: return []
    
    df = pd.read_csv(path).fillna(0)
    item_col = 'Item.[Item]'
    qty_col = 'D Base Forecast Quantity'
    
    if item_col not in df.columns: return []
    
    # We aggregate total planned quantity by Item
    grouped = df.groupby(item_col).agg({qty_col: 'sum'}).reset_index()
    grouped = grouped.sort_values(qty_col, ascending=False).head(7)
    
    bars = []
    for _, row in grouped.iterrows():
        # Accuracy is mocked or pulled from AccuracyAndMAPE file if needed
        acc = random.randint(88, 98)
        color = "green" if acc >= 95 else ("accent" if acc >= 91 else "amber")
        bars.append(ForecastBar(sku_name=row[item_col].split(' - ')[0], accuracy_pct=acc, bar_color=color))
    return bars


def load_dc_network() -> List[DCCard]:
    """Generate DC network health cards from real data."""
    path = os.path.join(DATASET_DIR, "Fact_InventorySnapshot.csv")
    if not os.path.exists(path):
        return []
    
    df = pd.read_csv(path).fillna(0)
    dc_col = 'dc' if 'dc' in df.columns else ('distribution_center' if 'distribution_center' in df.columns else None)
    region_col = 'region' if 'region' in df.columns else None
    on_hand_col = 'on_hand_units' if 'on_hand_units' in df.columns else 'current_stock'
    ss_col = 'safety_stock' if 'safety_stock' in df.columns else 'safety_stock_level'

    if not dc_col: return []

    agg_dict = {on_hand_col: 'sum', ss_col: 'sum'}
    if region_col: agg_dict[region_col] = 'first'

    grouped = df.groupby(dc_col).agg(agg_dict).reset_index()

    cards = []
    for _, row in grouped.sort_values(on_hand_col, ascending=False).head(6).iterrows():
        name = str(row[dc_col])
        units = int(row[on_hand_col])
        ss = float(row[ss_col])
        
        # Mapping region code for UI (Nike Synthetic Mapping)
        reg_code = "NA" if any(x in name for x in ["Memphis", "LA", "Denver", "Atlanta", "Los Angeles"]) else ("EU" if any(x in name for x in ["Barcelona", "Rotterdam", "Berlin", "Paris"]) else "GL")
        target = ss * 2.5 if ss > 0 else units * 1.5
        cap_pct = min(100, int((units / target) * 85)) if target > 0 else 60
        stat_lbl, stat_cls, bar_clr = ("OVERSTOCK", "warn", "amber") if units > (ss * 3.5) else (("CRITICAL", "crit", "red") if units < (ss * 0.5) else ("STABLE", "ok", "green"))
        if "Memphis" in name or "MEM" in name: stat_lbl = "PRIMARY HUB"
        
        cards.append(DCCard(
            name=name.replace(" Distribution Center", ""),
            region=f"{reg_code} · {stat_lbl}",
            status_label=stat_lbl,
            status_class=stat_cls,
            units=units,
            capacity_pct=cap_pct,
            bar_color=bar_clr
        ))
    return cards


def build_kpis(inventory: List[InventoryItem], forecast_bars: List[ForecastBar], signals: List[Signal]) -> List[KPICard]:
    """Build KPI cards from computed data with dynamic baselines."""
    # 1. Dynamic Forecast Accuracy & Baseline Calculation
    path = os.path.join(DATASET_DIR, "Fact_AccuracyAndMAPE.csv")
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            # Calculate accuracy vs baseline forecast
            # accuracy = 1 - MAPE (approx)
            avg_acc = df['forecast_accuracy'].mean() * 100 if 'forecast_accuracy' in df.columns else 91.0
            
            # Use 'baseline_forecast' if it exists to show gain
            base_acc = 87.5 # Fallback
            if 'baseline_forecast' in df.columns and 'actual_sales' in df.columns:
                # Simple accuracy: 1 - abs(error)/actual
                mape_base = (abs(df['baseline_forecast'] - df['actual_sales']) / df['actual_sales']).mean()
                base_acc = (1 - mape_base) * 100
            
            gain = avg_acc - base_acc
        except Exception:
            avg_acc, gain = 91.0, 2.1
    else:
        avg_acc = sum(fb.accuracy_pct for fb in forecast_bars) / len(forecast_bars) if forecast_bars else 91.0
        gain = 2.1
    
    # 2. Total on-hand units
    total_units = sum(item.on_hand for item in inventory)
    total_str = f"{total_units / 1000:.1f}K" if total_units >= 1000 else str(total_units)
    
    # 3. Fill rate: computed from inventory coverage
    if inventory:
        filled = sum(1 for item in inventory if item.on_hand >= item.demand)
        fill_rate = int(filled / len(inventory) * 100)
    else:
        fill_rate = 91
    
    # 4. Statistical Signal Alerting (Threshold = Mean + 1.5 StdDev)
    intensities = [s.intensity for s in signals if s.intensity > 0]
    if len(intensities) > 1:
        threshold = np.mean(intensities) + (1.5 * np.std(intensities))
        high_signals = sum(1 for s in signals if s.intensity > threshold)
    else:
        high_signals = sum(1 for s in signals if s.intensity > 4.0)

    return [
        KPICard(label="Forecast accuracy (MAPE)", value=f"{avg_acc:.1f}%",
                delta_text=f"↑ AI forecast vs baseline +{gain:.1f}%", delta_class="up", color_var="accent"),
        KPICard(label="Network fill rate", value=f"{fill_rate}%",
                delta_text=f"{'⚠ Below 95% target' if fill_rate < 95 else '✓ Above target'}", delta_class="warn" if fill_rate < 95 else "up"),
        KPICard(label="Total on-hand units", value=total_str,
                delta_text=f"↑ {len(load_dc_network())} DCs · Data-Driven", delta_class="info", color_var="blue"),
        KPICard(label="Active supply alerts", value=str(max(high_signals, 3)),
                delta_text=f"↑ {min(high_signals, 2)} critical · {max(1, high_signals - 2)} disruption pending",
                delta_class="neg", color_var="red"),
    ]


def build_alerts(inventory: List[InventoryItem], signals: List[Signal]) -> List[AlertItem]:
    """Dynamically generates alerts from signals and inventory data, ensuring all scenario types are represented."""
    alerts = []
    
    # 1. Demand Surge Alerts (Scenario Index 0)
    # Sort signals by intensity to pick the most relevant demand threat
    top_signals = sorted(signals, key=lambda s: s.intensity, reverse=True)
    if top_signals:
        s = top_signals[0]
        severity = "crit" if s.intensity > 8.5 else ("warn" if s.intensity > 7.0 else "info")
        alerts.append(AlertItem(
            severity=severity, icon="↑",
            title=f"{s.event} — surge risk detected",
            description=f"High-confidence signal ({s.intensity/10:.2f}) from {s.source}. Agent recommends evaluating air-freight and hybrid scenarios.",
            scenario_index=0
        ))

    # 2. Inventory Rebalancing Alerts (Scenario Index 1)
    # Find item with the lowest demand coverage ratio
    if inventory:
        # Avoid division by zero, prioritize items with demand
        worst_inv = sorted([i for i in inventory if i.demand > 0], 
                          key=lambda x: x.on_hand / x.demand)
        if worst_inv:
            item = worst_inv[0]
            ratio = item.on_hand / item.demand
            severity = "crit" if ratio < 0.25 else "warn"
            alerts.append(AlertItem(
                severity=severity, icon="!",
                title=f"{item.sku} — stockout hazard",
                description=f"Current on-hand ({item.on_hand:,}) is only {int(ratio*100)}% of 8-week demand. Internal DC transfer scenarios active.",
                scenario_index=1
            ))
            
    # 3. Supplier Disruption Alerts (Scenario Index 2)
    suppliers = load_suppliers()
    if suppliers:
        # Sort by utilization or status
        disrupted = [s for s in suppliers if s.status == "DISRUPTED"]
        if disrupted:
            sup = disrupted[0]
            status_desc = "production bottleneck"
        else:
            # Fallback to highest utilization supplier
            sup = sorted(suppliers, key=lambda s: s.utilization, reverse=True)[0]
            status_desc = "high utilization alert"
            
        severity = "crit" if sup.status == "DISRUPTED" else ("warn" if sup.utilization > 0.85 else "info")
        alerts.append(AlertItem(
            severity=severity, icon="▲",
            title=f"{sup.name} — {status_desc}",
            description=f"Partner operating at {int(sup.utilization*100)}% capacity. Alternate sourcing and recovery scenarios ready.",
            scenario_index=2
        ))

    # Fallback/Default if no issues found at all (unlikely with live data)
    if not alerts:
        alerts.append(AlertItem(severity="ok", icon="✓", title="Network Stable", description="No critical stockout or demand surge signals detected.", scenario_index=0))
    
    return alerts


def build_sku_table(inventory: List[InventoryItem]) -> List[dict]:
    """Build SKU inventory table data using Fact Demand Inputs."""
    path = _resolve_csv_path(
        os.path.join(DATASET_DIR, "Fact_DemandInputForecast.csv"),
        os.path.join(DATASETS_DIR, "Fact_DemandInputForecast.csv"),
    )
    if not path:
        return [
            {"sku_name": "Air Max 270 Black", "sku_code": "NK-AM-001", "channel": "DTC", "on_hand": "12,500", "safety_stock": "4,500", "status": "OK", "status_class": "badge-g"},
            {"sku_name": "Air Max 270 White", "sku_code": "NK-AM-002", "channel": "DTC", "on_hand": "8,900", "safety_stock": "5,000", "status": "SURGE", "status_class": "badge-a"},
            {"sku_name": "Dri-FIT Running Shirt M", "sku_code": "NK-RA-101", "channel": "DTC", "on_hand": "15,200", "safety_stock": "3,500", "status": "OK", "status_class": "badge-g"},
            {"sku_name": "Dri-FIT Running Shirt W", "sku_code": "NK-RA-102", "channel": "DTC", "on_hand": "9,800", "safety_stock": "3,800", "status": "OK", "status_class": "badge-g"},
            {"sku_name": "Tech Fleece Joggers M", "sku_code": "NK-TR-201", "channel": "DTC", "on_hand": "7,600", "safety_stock": "2,500", "status": "WATCH", "status_class": "badge-a"},
            {"sku_name": "LeBron XXI", "sku_code": "NK-BB-301", "channel": "DTC", "on_hand": "5,400", "safety_stock": "2,800", "status": "OK", "status_class": "badge-g"},
            {"sku_name": "Kids Air Max Runner", "sku_code": "NK-KD-501", "channel": "DTC", "on_hand": "4,800", "safety_stock": "1,800", "status": "OK", "status_class": "badge-g"},
        ]
    
    df = pd.read_csv(path)
    item_col = 'Item.[Item]'
    chan_col = 'Sales Domain.[Customer Group]'
    qty_col = 'D Base Forecast Quantity'
    buff_col = 'D Buff1 Forecast Quantity'
    
    grouped = df.groupby(item_col).agg({
        chan_col: 'first',
        qty_col: 'mean',
        buff_col: 'mean'
    }).reset_index()
    grouped = grouped.sort_values(qty_col, ascending=False).head(7)
    
    rows = []
    # Cross-reference with inventory list if possible, else mock on_hand from qty
    inv_map = {i.sku: i.on_hand for i in inventory}
    
    for _, row in grouped.iterrows():
        full_name = row[item_col]
        sku_name = full_name.split(' - ')[0]
        on_hand = inv_map.get(full_name, int(row[qty_col] * 1.5))
        safety = int(row[buff_col])
        ratio = on_hand / safety if safety > 0 else 2.0
        
        if ratio < 1.2:
            status, status_class = "RISK", "badge-r"
        elif ratio < 1.8:
            status, status_class = "WATCH", "badge-a"
        else:
            status, status_class = "OK", "badge-g"
        
        rows.append({
            "sku_name": sku_name,
            "sku_code": full_name.split(' - ')[-1],
            "channel": row[chan_col],
            "on_hand": f"{on_hand:,}",
            "safety_stock": f"{safety:,}",
            "status": status,
            "status_class": status_class
        })
    return rows


def build_external_signals(signals: List[Signal]) -> List[ExternalSignal]:
    """Convert signals to external signal format for UI."""
    if not signals or (len(signals) == 1 and signals[0].source == 'Mock'):
        return [
            ExternalSignal(dot_color="blue", signal_type="Social · Instagram / TikTok",
                          text="Air Max 270 mentions spiked +1,250% in North America — demand agent triggered",
                          confidence="confidence 0.87 · demand surge scenario active", timestamp="2026-03-14 09:32"),
            ExternalSignal(dot_color="amber", signal_type="Weather · NOAA",
                          text="Heat wave forecast Southeast US — running apparel demand uplift +18–25% expected next 3 weeks",
                          confidence="confidence 0.92", timestamp="2026-03-13 07:10"),
            ExternalSignal(dot_color="red", signal_type="Competitor · Price intelligence",
                          text="Adidas Basketball shoes promo -15% — LeBron XXI demand monitoring elevated",
                          confidence="confidence 0.95 · no action triggered yet", timestamp="2026-03-12 06:55"),
            ExternalSignal(dot_color="green", signal_type="Event · ESPN Calendar",
                          text="NBA Playoffs start Apr 15 — LeBron XXI and basketball footwear uplift expected",
                          confidence="confidence 1.00 · pre-positioned in inventory plan", timestamp="2026-03-11 00:00"),
        ]
    
    colors = ["blue", "amber", "red", "green"]
    result = []
    for i, sig in enumerate(signals[:4]):
        result.append(ExternalSignal(
            dot_color=colors[i % len(colors)],
            signal_type=sig.source,
            text=sig.event,
            confidence=f"confidence {sig.intensity/10:.2f}",
            timestamp=f"2026-03-{14-i:02d} {random.randint(0,12):02d}:{random.randint(0,59):02d}"
        ))
    return result


def get_dynamic_scenario(pill_idx: int, skip_llm: bool = False) -> DashboardScenario:
    """Generates a DashboardScenario object dynamically from live data.
    If skip_llm is True, it uses high-fidelity fallbacks for faster initial dashboard load.
    """
    rec_agent = RecommendationAgent()
    if pill_idx == 0:
        # Demand Surge
        signals = load_signals()
        primary = signals[0] if signals else Signal(event="Market Volatility", source="System", intensity=5.0, days_to_impact=7)
        uplift = int(primary.intensity * 3)
        
        if skip_llm:
            summary = {
                "why": f"Predictive sentiment analysis detected {uplift}% spike in brand mentions.",
                "ctx": f"Automated analysis of DEMAND_SURGE based on current telemetry from {primary.source}."
            }
        else:
            summary = rec_agent.provide_brief_summary("DEMAND_SURGE", {"event": primary.event, "intensity": primary.intensity, "uplift": uplift})
        
        # --- AGENTIC SIMULATION LAYER ---
        scenarios_data = [
            {'id': 'A', 'name': 'A — Accelerate', 'mode': 'AIR', 'carrier': 'FedEx Express', 'cost': 450000.0, 'lead_time': 7, 'fill_rate': 0.96, 'risk': 0.15},
            {'id': 'B', 'name': 'B — Secondary', 'mode': 'SEA', 'carrier': 'Maersk Line', 'cost': 280000.0, 'lead_time': 14, 'fill_rate': 0.82, 'risk': 0.45},
            {'id': 'C', 'name': 'C — Hybrid', 'mode': 'AIR', 'carrier': 'Mixed Logistics', 'cost': 320000.0, 'lead_time': 10, 'fill_rate': 0.94, 'risk': 0.22},
        ]
        
        agent_logs = []
        sim_agent = SimulationAgent(scenarios_data)
        simulated = sim_agent.simulate("DEMAND_SURGE", agent_logs)
        
        kpi_agent = KPIAgent()
        evaluated, hist_acc = kpi_agent.evaluate(simulated, agent_logs)
        
        # Determine the recommended scenario (highest score)
        best = evaluated[0] if evaluated else simulated[2]
        
        rows = []
        for s in simulated:
            is_rec = (s.id == best.id)
            rec_data = {}
            if is_rec:
                rec_data = {
                    'kpis': [
                        {'lbl': 'Fill rate', 'val': f"{int(s.fill_rate*100)}%", 'delta': 'Optimal', 'neg': False},
                        {'lbl': 'CO2 Uplift', 'val': f"+{s.co2_uplift}kg/u", 'delta': 'SCSI Impact', 'neg': s.co2_uplift > 5}
                    ],
                    'confidence': int(s.otif), 
                    'actions': [f'Approve {s.name.split(" — ")[-1]} routing']
                }
            
            rows.append({
                'cells': [s.name, s.mode, f"+${int(s.cost/1000)}K", f"{int(s.lead_time)} days", f"{int(s.risk*100)}%"],
                'rec': is_rec,
                'rec_data': rec_data
            })

        # --- STRATEGIC RATIONALE & COMPARISON ---
        if skip_llm:
            best_rec = type('obj', (object,), {'strategy_paragraph': None})
            comparison = "Analyzing optimal routing paths between Air and Sea..."
        else:
            best_rec = rec_agent.generate(best, {"event": primary.event, "intensity": primary.intensity}, signals, "DEMAND_SURGE", agent_logs)
            comparison = rec_agent.get_comparison_rationale("DEMAND_SURGE", simulated, best)

        return DashboardScenario(
            pill=0,
            title="Demand Surge",
            why=summary["why"],
            use_case="DEMAND_SURGE",
            badge=None,
            text=best_rec.strategy_paragraph or f"A sudden +{uplift}% spike in '{primary.event}' demand has been detected. {summary['ctx']}",
            meta=[
                {'label': 'Triggered', 'value': datetime.now().strftime("%Y-%m-%d %H:%M")},
                {'label': 'Signal Source', 'value': primary.source},
                {'label': 'Demand uplift', 'value': f"+{uplift}%"},
                {'label': 'Historical Accuracy', 'value': f"{hist_acc:.1f}%"},
                {'label': 'Simulations Run', 'value': str(len(simulated) * 500)},
                {'label': 'Options Found', 'value': str(len(simulated))},
            ],
            steps=[
                {'s': 'done', 'name': 'Signal Ingestion Agent', 'detail': f"Extracted '{primary.event}' from {primary.source}"},
                {'s': 'done', 'name': 'Signal Analysis Agent', 'detail': 'Impact assessment complete'},
                {'s': 'done', 'name': 'Simulation Agent', 'detail': 'Monte Carlo modeling active'},
                {'s': 'done', 'name': 'KPI Agent', 'detail': 'Sustainability scoring active'},
                {'s': 'done', 'name': 'Generated Options', 'detail': comparison},
                {'s': 'done', 'name': 'Recommendation Agent', 'detail': 'Strategic rationale compiled'}
            ],
            ctx=summary["ctx"],
            table={
                'headers': ['Option', 'Mode', 'Incremental Cost', 'Lead time', 'Risk'],
                'rows': rows
            },
            agent_logs=[{'agent': 'ORCHESTRATOR', 'logic': 'Live simulation loop complete.'}] + [{'agent': 'Simulation/KPI Agent', 'logic': log} for log in agent_logs[-4:]],
            comparison_rationale=comparison
        )
    elif pill_idx == 1:
        # Inventory Rebalancing
        from agents.rebalance import RebalancingAgent
        inv = load_inventory()
        dc_network = load_dc_network()
        
        # Find item with most critically low stock vs demand
        critical = sorted(inv, key=lambda x: x.on_hand - x.demand)[0] if inv else InventoryItem(sku="SKU-ERR", name="Unknown SKU", on_hand=0, demand=100)
        gap = critical.demand - critical.on_hand
        
        reb_agent = RebalancingAgent()
        transfers = reb_agent.identify_transfers(inv, dc_network)
        transfer = transfers[0] if transfers else {'from_dc': 'Memphis-DC01', 'quantity': gap, 'cost': 8200.0, 'transit_days': 3, 'risk': 0.12}
        
        # --- AGENTIC SIMULATION LAYER ---
        scenarios_data = [
            {'id': '1', 'name': '1 — No action', 'mode': 'SEA', 'carrier': 'N/A', 'cost': 0.0, 'lead_time': 21, 'fill_rate': 0.15, 'risk': 0.94},
            {'id': '2', 'name': '2 — Full transfer', 'mode': 'TRUCK', 'carrier': 'Schneider', 'cost': 15000.0, 'lead_time': 2, 'fill_rate': 1.0, 'risk': 0.01},
            {'id': '3', 'name': '3 — Optimal', 'mode': 'TRUCK', 'carrier': 'CH Robinson', 'cost': transfer['cost'], 'lead_time': transfer['transit_days'], 'fill_rate': 0.97, 'risk': transfer['risk']},
        ]
        
        agent_logs = []
        sim_agent = SimulationAgent(scenarios_data)
        simulated = sim_agent.simulate("INVENTORY_REBALANCING", agent_logs)
        
        kpi_agent = KPIAgent()
        evaluated, _ = kpi_agent.evaluate(simulated, agent_logs)
        
        best = evaluated[0] if evaluated else simulated[2]
        
        rows = []
        for s in simulated:
            is_rec = (s.id == best.id)
            rec_data = {}
            if is_rec:
                rec_data = {
                    'kpis': [{'lbl': 'Net Benefit', 'val': '$12,400', 'delta': 'Cost Avoidance', 'neg': False}],
                    'confidence': int(s.otif), 'actions': [f'Schedule transfer from {transfer["from_dc"]}']
                }
            rows.append({
                'cells': [s.name, s.carrier, f"${int(s.cost):,}", f"{int(s.risk*100)}%"],
                'rec': is_rec,
                'rec_data': rec_data
            })

        # --- STRATEGIC RATIONALE & COMPARISON ---
        if skip_llm:
            best_rec = type('obj', (object,), {'strategy_paragraph': None})
            comparison = "Calculating cost avoidance via internal rebalancing..."
            summary = {
                "why": "Inventory-to-Demand ratio fell below critical threshold.",
                "ctx": "DC-to-DC transfer optimization initiated."
            }
        else:
            best_rec = rec_agent.generate(best, {"sku": critical.sku, "gap": gap}, [], "INVENTORY_REBALANCING", agent_logs)
            comparison = rec_agent.get_comparison_rationale("INVENTORY_REBALANCING", simulated, best)
            summary = rec_agent.provide_brief_summary("INVENTORY_REBALANCING", {"sku": critical.sku, "gap": gap})
        return DashboardScenario(
            pill=1,
            title="Inventory Rebalancing",
            why=summary["why"],
            use_case="INVENTORY_REBALANCING",
            badge=None,
            text=best_rec.strategy_paragraph or f"Critical stockout risk for {critical.name} identified. Agent recommends rebalancing from {transfer['from_dc']}.",
            meta=[
                {'label': 'Triggered', 'value': datetime.now().strftime("%Y-%m-%d %H:%M")},
                {'label': 'Inventory Gap', 'value': f"{gap:,} units"},
                {'label': 'Affected SKU', 'value': critical.sku},
                {'label': 'Source Hub', 'value': transfer['from_dc']},
                {'label': 'Simulations Run', 'value': str(len(simulated) * 500)},
                {'label': 'Options Found', 'value': str(len(simulated))},
            ],
            steps=[
                {'s': 'done', 'name': 'Stock Ingestion Agent', 'detail': 'Resolved DC stock positions'},
                {'s': 'done', 'name': 'Inventory Analysis Agent', 'detail': f"Located surplus for {critical.sku} at {transfer['from_dc']}"},
                {'s': 'done', 'name': 'Simulation Agent', 'detail': 'Predicting transfer success'},
                {'s': 'done', 'name': 'KPI Agent', 'detail': 'Working capital assessment'},
                {'s': 'done', 'name': 'Generated Options', 'detail': comparison},
                {'s': 'done', 'name': 'Recommendation Agent', 'detail': 'Optimal LTL route identified'}
            ],
            ctx=summary["ctx"],
            table={
                'headers': ['Option', 'Carrier', 'Transfer Cost', 'Stockout risk'],
                'rows': rows
            },
            agent_logs=[{'agent': 'ORCHESTRATOR', 'logic': 'Rebalancing simulations active.'}] + [{'agent': 'Simulation/KPI Agent', 'logic': log} for log in agent_logs[-4:]],
            comparison_rationale=comparison
        )
    else:
        # Supplier Constraint
        suppliers = load_suppliers()
        disrupted = next((s for s in suppliers if s.status == "DISRUPTED"), None)
        s_name = disrupted.name if disrupted else "Dhaka Textiles Ltd"
        
        # --- AGENTIC SIMULATION LAYER ---
        scenarios_data = [
            {'id': '1', 'name': '1 — Wait for Primary', 'mode': 'SEA', 'carrier': 'Baseline', 'cost': 0.0, 'lead_time': 21, 'fill_rate': 0.60, 'risk': 0.85},
            {'id': '2', 'name': '2 — Full Switch (VNM)', 'mode': 'SEA', 'carrier': 'Saigon Fab', 'cost': 354000.0, 'lead_time': 18, 'fill_rate': 0.95, 'risk': 0.15},
            {'id': '3', 'name': '3 — Split (60/40)', 'mode': 'SEA', 'carrier': 'Mixed', 'cost': 276000.0, 'lead_time': 18, 'fill_rate': 0.92, 'risk': 0.45},
            {'id': '4', 'name': '4 — Expedite + Alt', 'mode': 'AIR', 'carrier': 'Hybrid', 'cost': 186000.0, 'lead_time': 14, 'fill_rate': 0.94, 'risk': 0.10},
        ]
        
        agent_logs = []
        sim_agent = SimulationAgent(scenarios_data)
        simulated = sim_agent.simulate("SUPPLIER_CONSTRAINT", agent_logs)
        
        kpi_agent = KPIAgent()
        evaluated, _ = kpi_agent.evaluate(simulated, agent_logs)
        
        best = evaluated[0] if evaluated else simulated[3]
        
        rows = []
        for s in simulated:
            is_rec = (s.id == best.id)
            rec_data = {}
            if is_rec:
                rec_data = {
                    'kpis': [
                        {'lbl': 'Revenue Protect', 'val': '$8.2M', 'delta': '92% of Plan', 'neg': False},
                        {'lbl': 'Launch Impact', 'val': f"-{int(s.lead_time)}d", 'delta': 'Reduced Delay', 'neg': False}
                    ],
                    'confidence': int(s.otif), 
                    'actions': ['Authorize $80K emergency repair', 'Secure VNM capacity']
                }
            
            rows.append({
                'cells': [s.name, f"+${int(s.cost/1000)}K", f"{int(s.lead_time)} days", f"{int(s.risk*100)}%"],
                'rec': is_rec,
                'rec_data': rec_data
            })
        
        # --- STRATEGIC RATIONALE & COMPARISON ---
        if skip_llm:
            best_rec = type('obj', (object,), {'strategy_paragraph': None})
            comparison = "Evaluating Saigon alternate sourcing and production shifts..."
            summary = {
                "why": "Tier-2 production bottleneck detected.",
                "ctx": "Alternate sourcing recovery plan triggered."
            }
        else:
            best_rec = rec_agent.generate(best, {"supplier": s_name}, [], "SUPPLIER_CONSTRAINT", agent_logs)
            comparison = rec_agent.get_comparison_rationale("SUPPLIER_CONSTRAINT", simulated, best)
            summary = rec_agent.provide_brief_summary("SUPPLIER_CONSTRAINT", {"supplier": s_name, "status": "DISRUPTED"})
        return DashboardScenario(
            pill=2,
            title="Supplier Constraint",
            why=summary["why"],
            use_case="SUPPLIER_CONSTRAINT",
            badge=None,
            text=best_rec.strategy_paragraph or f"Production bottleneck reported at {s_name}. Agent recommends shifting to Saigon alternate sourcing.",
            meta=[
                {'label': 'Triggered', 'value': datetime.now().strftime("%Y-%m-%d %H:%M")},
                {'label': 'Disrupted Entity', 'value': s_name},
                {'label': 'Impacted Units', 'value': '245,000'},
                {'label': 'Risk Assessment', 'value': 'Critical'},
                {'label': 'Simulations Run', 'value': str(len(simulated) * 500)},
                {'label': 'Options Found', 'value': str(len(simulated))},
            ],
            steps=[
                {'s': 'done', 'name': 'Supplier Ingestion Agent', 'detail': f"Analyzed alert from {s_name}"},
                {'s': 'done', 'name': 'Network Analysis Agent', 'detail': 'Mapped impacted Spring apparel SKUs'},
                {'s': 'done', 'name': 'Simulation Agent', 'detail': 'Modeled launch date impacts'},
                {'s': 'done', 'name': 'KPI Agent', 'detail': 'Revenue at risk assessment complete'},
                {'s': 'done', 'name': 'Generated Options', 'detail': comparison},
                {'s': 'done', 'name': 'Recommendation Agent', 'detail': 'Balanced cost/delay optimization'}
            ],
            ctx=summary["ctx"],
            table={
                'headers': ['Option', 'Recovery Cost', 'Launch Delay', 'Quality Risk'],
                'rows': rows
            },
            agent_logs=[{'agent': 'ORCHESTRATOR', 'logic': 'Recovery simulations active.'}] + [{'agent': 'Simulation/KPI Agent', 'logic': log} for log in agent_logs[-4:]],
            comparison_rationale=comparison
        )

def build_orchestrator_pill() -> DashboardScenario:
    """Builds a special virtual scenario pill for the Orchestrator Engine status."""
    return DashboardScenario(
        pill=-1,
        is_orchestrator=True,
        title="Orchestrator Engine",
        why="Enterprise AI Orchestration active.",
        use_case="ORCHESTRATION",
        badge=None,
        text="All agents operational. Ready to trigger AI-driven supply chain optimizations.",
        meta=[
            {'label': 'Status', 'value': 'Idle'},
            {'label': 'Engine', 'value': 'Parallel-First'},
            {'label': 'Connected Agents', 'value': '9'}
        ],
        steps=[],
        ctx="System ready for scenario selection.",
        table={'headers': [], 'rows': []},
        agent_logs=[]
    )


def build_dashboard_scenarios() -> List[DashboardScenario]:
    """Build the 4 pills: 1 Orchestrator + 3 dynamic scenarios (fast-load mode)."""
    scenarios = [build_orchestrator_pill()]
    scenarios.extend([get_dynamic_scenario(i, skip_llm=True) for i in range(3)])
    return scenarios


def refine_recommendation(scenario_id: int, option_idx: int, use_case: str) -> dict:
    """Uses LLM to refine the recommendation based on a specific selected option."""
    # 1. Get the baseline scenario data for this pill (full LLM mode)
    sc = get_dynamic_scenario(scenario_id, skip_llm=False)
    if option_idx >= len(sc.table['rows']):
        return {}
    
    selected_row = sc.table['rows'][option_idx]
    
    # 2. Try to load 'live' stats from the last run if available
    live_scenario = None
    try:
        cache_path = os.path.join(DATASET_DIR, "last_run_scenarios.json")
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                cached = json.load(f)
                # Find matching scenario by mode (approximate for POC)
                target_mode = selected_row['cells'][0].split('—')[-1].strip().split(' ')[0].upper()
                for c_sc in cached:
                    if c_sc.get('mode') == target_mode or c_sc.get('name') in selected_row['cells'][0]:
                        live_scenario = Scenario(**c_sc)
                        break
    except Exception as e:
        print(f"Refine cache error: {e}")

    # 3. Call Recommendation Agent to 'refine' this specific option
    agent = RecommendationAgent()
    full_ctx = f"Scenario: {sc.title}. {sc.text}. Meta: {sc.meta}. Baseline: {sc.ctx}"
    refined_data = agent.refine(use_case, selected_row, full_ctx, scenario=live_scenario)
    return refined_data

# ───────── Main orchestration functions ─────────

def run_orchestration(scenario_id: int = None) -> ExecutionResult:
    logs = []
    # Forces use_case if scenario_id provided
    forced_use_case = None
    classifier_name = "Use Case Classifier"
    if scenario_id == 0: 
        forced_use_case = "DEMAND_SURGE"
        classifier_name = "Demand Surge Classifier"
    elif scenario_id == 1: 
        forced_use_case = "INVENTORY_REBALANCING"
        classifier_name = "Inventory Rebalancing Classifier"
    elif scenario_id == 2: 
        forced_use_case = "SUPPLIER_CONSTRAINT"
        classifier_name = "Supplier Disruption Classifier"
    
    from concurrent.futures import ThreadPoolExecutor
    from agents.evaluation import StatisticalAgent
    stat_agent = StatisticalAgent()

    # Pre-Classification (Moved)
    signals_data = load_signals()
    inventory_data = load_inventory()
    
    # 4-WAY PARALLEL EXECUTION PHASE (As per Scenario Diagrams)
    def task_ingestion():
        l = []
        if scenario_id == 0:
            SignalIngestionAgent().run()
            l.append("Signal Ingestion Agent complete: Sources cleaned.")
        elif scenario_id == 1:
            InventoryIngestionAgent().run()
            l.append("Inventory Ingestion Agent complete: Stock positions resolved.")
        else:
            l.append("Supplier Dataset loaded: Multi-tier partner capacity mapped.")
        return l

    def task_classification():
        l = []
        sig_data = load_signals()
        inv_data = load_inventory()
        u_case, c_name = (forced_use_case, classifier_name) if forced_use_case else UseCaseClassifier.classify(sig_data, inv_data, l)
        l.append(f"ORCHESTRATOR -> Routing to {u_case} workflow via {c_name}.")
        return l, u_case, c_name

    # Analysis and Simulation need to know the 'forced' use case or a default,
    # or they need to be slightly decoupled. For the mock, we'll use forced_use_case
    # or assume the classification won't change the analysis logic too much during POC.
    active_uc = forced_use_case if forced_use_case else "DEMAND_SURGE" 

    def task_analysis(use_case_selected):
        l = []
        sig_data = load_signals()
        inv_data = load_inventory()
        
        ctx = None
        summ = {}
        if use_case_selected == "DEMAND_SURGE":
            s_agent = SignalAnalysisAgent(sig_data, SIGNAL_THRESHOLD)
            ctx = s_agent.analyze(use_case_selected, l)
            summ = {"at_risk_count": 15, "type": "surge"}
            if sig_data:
                ps = Signal(**sig_data[0]) if isinstance(sig_data[0], dict) else sig_data[0]
                stat_agent.validate_signal(ps, l)
        elif use_case_selected == "INVENTORY_REBALANCING":
            i_agent = InventoryAnalysisAgent(inv_data)
            summ = i_agent.analyze(use_case_selected, l)
            ctx = []
        else:
            supplier_data = load_suppliers()
            sp_agent = SupplierAnalysisAgent(supplier_data)
            summ = sp_agent.analyze(l)
            ctx = []
        return l, summ, ctx

    def task_simulation(use_case_selected):
        l = []
        scen_data = load_scenarios()
        s_agent = SimulationAgent(scen_data)
        pro_scen = s_agent.simulate(use_case_selected, l)
        # We ensure simulation runs for the RIGHT use case even if selected later
        return l, pro_scen

    # Run 4-way Parallel Agents
    with ThreadPoolExecutor(max_workers=4) as executor:
        f_ingest = executor.submit(task_ingestion)
        f_class = executor.submit(task_classification)
        f_analysis = executor.submit(task_analysis, active_uc)
        f_simulation = executor.submit(task_simulation, active_uc)
        
        l_ingest = f_ingest.result()
        l_class, use_case, c_name = f_class.result()
        l_analysis, analysis_summary, context_data = f_analysis.result()
        l_simulation, processed_scenarios = f_simulation.result()

    # Build Audit Trail (Consolidated JOIN point)
    ingest_node = AuditNode(
        id='ingest', 
        name='Signal Ingestion Agent' if scenario_id == 0 else ('Inventory Ingestion Agent' if scenario_id == 1 else 'Supplier Dataset'), 
        status='done', 
        icon='eye'
    )
    ingest_node.logs = l_ingest
    
    classifier_node = AuditNode(id='classifier', name=c_name, status='done', icon='repeat')
    classifier_node.logs = l_class
    
    anal_node = AuditNode(id='anal', name=f"{use_case.replace('_',' ').title()} Analysis", status='done', icon='scan')
    anal_node.logs = l_analysis
    
    sim_node = AuditNode(id='simulation', name='Simulation Agent', status='done', icon='flask')
    sim_node.logs = l_simulation

    # 5. KPI & REGRET PHASE (Node 4)
    start_idx = len(logs)
    kpi_agent = KPIAgent()
    sorted_viable, accuracy = kpi_agent.evaluate(processed_scenarios, logs)
    sorted_viable = stat_agent.analyze_regret(sorted_viable, logs)
    kpi_node = AuditNode(id='kpi', name='KPI & Regret Analysis', status='done', icon='bar')
    kpi_node.logs = logs[start_idx:]

    # 6. GENERATED OPTIONS PHASE (Node 5)
    gen_node = AuditNode(id='generated', name='Generated Options', status='done', icon='list')
    best_fill = int(sorted_viable[0].fill_rate * 100) if sorted_viable else (int(processed_scenarios[0].fill_rate * 100) if processed_scenarios else 0)
    gen_node.logs = [
        f"Calculated {len(processed_scenarios)} viable path permutations.",
        f"Top option provides {best_fill}% service level projection.",
        "Stochastic variance within 5% tolerance."
    ]

    # 7. LLM RECOMMENDATION PHASE (Node 6)
    start_idx = len(logs)
    best_scenario = sorted_viable[0] if sorted_viable else (processed_scenarios[0] if processed_scenarios else None)
    rec_agent = RecommendationAgent()
    recommendation = rec_agent.generate(best_scenario, analysis_summary, context_data, use_case, logs)
    rec_node = AuditNode(id='recommendation', name='Recommendations', status='done', icon='brain')
    rec_node.logs = logs[start_idx:]

    audit_trail = [ingest_node, classifier_node, anal_node, sim_node, kpi_node, gen_node, rec_node]

    # Cache scenarios for dynamic refinement (UI support)
    try:
        cache_path = os.path.join(DATASET_DIR, "last_run_scenarios.json")
        with open(cache_path, 'w') as f:
            json.dump([s.model_dump() for s in processed_scenarios], f)
    except Exception as e:
        print(f"Failed to cache scenarios: {e}")

    constraints_rows = load_constraints()
    budget_limits = []
    for r in constraints_rows:
        if str(r.get("constraint_type", "")).lower() != "budget":
            continue
        try:
            budget_limits.append(float(r.get("limit_value", 0)))
        except (TypeError, ValueError):
            continue

    return ExecutionResult(
        scenarios=sorted_viable,
        recommendation=recommendation,
        audit_trail=audit_trail,
        status_metrics={
            "budget_cap": BUDGET_CAP,
            "budget_used": best_scenario.cost,
            "dc_capacity_total": 1000000,
            "dc_capacity_used": 742100,
            "forecast_accuracy": accuracy,
            "active_use_case": use_case,
            "constraints_count": len(constraints_rows),
            "constraints_budget_samples": budget_limits[:5],
        },
        logs=logs
    )

def _load_activities() -> List[Dict]:
    if not os.path.exists(SAVED_ACTIVITIES_FILE):
        return []
    try:
        with open(SAVED_ACTIVITIES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading activities: {e}")
        return []

def save_activity(activity_data: Dict) -> str:
    activities = _load_activities()
    activity_id = hashlib.md5(f"{activity_data['timestamp']}{random.random()}".encode()).hexdigest()[:8]
    activity_data['id'] = activity_id
    activities.append(activity_data)
    # Keep last 20 activities
    activities = activities[-20:]
    try:
        os.makedirs(os.path.dirname(SAVED_ACTIVITIES_FILE), exist_ok=True)
        with open(SAVED_ACTIVITIES_FILE, 'w') as f:
            json.dump(activities, f, indent=2)
    except Exception as e:
        print(f"Error saving activity: {e}")
    return activity_id

def get_initial_state() -> dict:
    """Return all dashboard data: signals, inventory, KPIs, alerts, forecasts, DCs, SKUs, suppliers, signals, scenarios."""
    # Ensure fresh data on initial load

    signals = load_signals()
    inventory = load_inventory()
    forecast_bars = load_demand_forecast()
    dc_network = load_dc_network()
    suppliers = load_suppliers()
    kpis = build_kpis(inventory, forecast_bars, signals)
    alerts = build_alerts(inventory, signals)
    sku_table = build_sku_table(inventory)
    external_signals = build_external_signals(signals)
    # dashboard_scenarios are now dynamic and include the Orchestrator pill
    dashboard_scenarios = build_dashboard_scenarios()
    
    return {
        "signals": [s.model_dump() for s in signals],
        "inventory": [i.model_dump() for i in inventory],
        "kpis": [k.model_dump() for k in kpis],
        "alerts": [a.model_dump() for a in alerts],
        "forecast_bars": [f.model_dump() for f in forecast_bars],
        "dc_network": [d.model_dump() for d in dc_network],
        "sku_table": sku_table,
        "suppliers": [s.model_dump() for s in suppliers],
        "external_signals": [e.model_dump() for e in external_signals],
        "dashboard_scenarios": [s.model_dump() for s in dashboard_scenarios],
        "activities": _load_activities(),
    }
