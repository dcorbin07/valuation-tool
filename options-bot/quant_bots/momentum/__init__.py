"""Bot #3: cross-sectional momentum — rank a stock universe, hold winners, short losers."""
from .signals import (
    Direction,
    MomentumConfig,
    MomentumScore,
    MomentumSignalGenerator,
    RankedSelection,
    compute_score_from_closes,
    rank_and_select,
)
from .strategy import MomentumStrategy, StrategyConfig, TargetPortfolio, TargetWeight
from .orchestrator import JobResult, MomentumBotConfig, MomentumOrchestrator

__all__ = [
    "Direction", "MomentumConfig", "MomentumScore", "MomentumSignalGenerator",
    "RankedSelection", "compute_score_from_closes", "rank_and_select",
    "MomentumStrategy", "StrategyConfig", "TargetPortfolio", "TargetWeight",
    "JobResult", "MomentumBotConfig", "MomentumOrchestrator",
]
