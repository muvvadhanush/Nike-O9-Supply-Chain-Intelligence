from pydantic import BaseModel
from typing import List, Optional, Any

class Signal(BaseModel):
    event: str
    source: str
    intensity: float
    days_to_impact: int

class InventoryItem(BaseModel):
    sku: str
    name: str
    on_hand: int
    demand: int

class Scenario(BaseModel):
    id: str
    name: str
    mode: str
    carrier: str
    lead_time: int
    cost: float
    fill_rate: float
    co2_uplift: float = 0.0
    risk: float
    is_inviable: bool = False
    otif: Optional[float] = None
    score: Optional[float] = None
    # Advanced Evaluation Fields
    monte_min: Optional[float] = None
    monte_max: Optional[float] = None
    monte_avg: Optional[float] = None
    monte_std: Optional[float] = None
    regret_index: Optional[float] = None

class Recommendation(BaseModel):
    scenario_id: str
    name: str
    command: str
    confidence: int
    rationale: List[str]
    strategy_paragraph: Optional[str] = None  # NEW: For cohesive problem/solution text
    metrics: dict

class AuditNode(BaseModel):
    id: str
    name: str
    status: str  # 'pending', 'active', 'done'
    icon: str
    logs: Optional[List[str]] = []

class ExecutionResult(BaseModel):
    scenarios: List[Scenario]
    recommendation: Recommendation
    audit_trail: List[AuditNode]
    status_metrics: dict
    logs: List[str]

# ───────── New models for enriched dashboard ─────────

class SupplierInfo(BaseModel):
    name: str
    supplier_id: str
    country: str
    utilization: float       # 0-1
    lead_time: str           # e.g. "28d ±5"
    quality_score: str       # e.g. "4.5 / 5"
    status: str              # AVAILABLE, DISRUPTED, HIGH UTIL, WATCH
    status_class: str        # badge-g, badge-r, badge-a

class ForecastBar(BaseModel):
    sku_name: str
    accuracy_pct: int
    bar_color: str           # CSS var name: green, accent, amber

class DCCard(BaseModel):
    name: str
    region: str
    status_label: str        # STABLE, CRITICAL, OVERSTOCK, PRIMARY HUB
    status_class: str        # ok, warn, crit
    units: int
    capacity_pct: int
    bar_color: str           # CSS var name

class KPICard(BaseModel):
    label: str
    value: str
    delta_text: str
    delta_class: str         # up, warn, info, neg
    color_var: Optional[str] = None  # CSS var for value color

class AlertItem(BaseModel):
    severity: str            # crit, warn, info
    icon: str
    title: str
    description: str
    scenario_index: int

class ExternalSignal(BaseModel):
    dot_color: str           # CSS var name
    signal_type: str
    text: str
    confidence: str
    timestamp: str

class SavedActivity(BaseModel):
    id: str
    timestamp: str
    scenario_title: str
    use_case: str
    option_name: str
    recommendation: dict

class DashboardScenario(BaseModel):
    pill: int
    is_orchestrator: bool = False
    title: str
    why: str
    use_case: str
    badge: Optional[str] = None
    text: str
    meta: List[dict]         # [{label, value}, ...]
    steps: List[dict]        # [{s, name, detail}, ...]
    ctx: str
    table: dict              # {headers: [], rows: [{cells: [], rec: bool, rec_data: dict}]}
    agent_logs: List[dict]   # [{"agent": str, "logic": str}]
    comparison_rationale: Optional[str] = None # NEW: For "Generated Options" comparison

class RefineRequest(BaseModel):
    scenario_id: int
    option_idx: int
    use_case: str

class InitialState(BaseModel):
    signals: List[Signal]
    inventory: List[InventoryItem]
    kpis: List[KPICard]
    alerts: List[AlertItem]
    forecast_bars: List[ForecastBar]
    dc_network: List[DCCard]
    sku_table: List[dict]
    suppliers: List[SupplierInfo]
    external_signals: List[ExternalSignal]
    dashboard_scenarios: List[DashboardScenario]
    activities: List[SavedActivity]
