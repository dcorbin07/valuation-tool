"""Trend-following bot (Bot #2): time-series momentum on a cross-asset basket."""
from .universe import (
    AssetClass,
    Instrument,
    TREND_BASKET,
    by_asset_class,
    get_basket,
    get_symbols,
    lookup,
)
from .signals import (
    Direction,
    Signal,
    SignalConfig,
    SignalGenerator,
    compute_signal_from_closes,
)
from .strategy import StrategyConfig, TargetPortfolio, TargetWeight, TrendStrategy
from .risk import RiskConfig, RiskResult, SizedTarget, TrendRiskManager
from .portfolio import (
    PortfolioConfig,
    RebalanceOrder,
    RebalancePlan,
    TrendPortfolioManager,
    orders_to_reach_target,
)
from .orchestrator import JobResult, TrendConfig, TrendOrchestrator

__all__ = [
    "AssetClass", "Instrument", "TREND_BASKET", "by_asset_class",
    "get_basket", "get_symbols", "lookup",
    "Direction", "Signal", "SignalConfig", "SignalGenerator",
    "compute_signal_from_closes",
    "StrategyConfig", "TargetPortfolio", "TargetWeight", "TrendStrategy",
    "RiskConfig", "RiskResult", "SizedTarget", "TrendRiskManager",
    "PortfolioConfig", "RebalanceOrder", "RebalancePlan",
    "TrendPortfolioManager", "orders_to_reach_target",
    "JobResult", "TrendConfig", "TrendOrchestrator",
]
