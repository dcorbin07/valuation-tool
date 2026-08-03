"""Bot #4: short-horizon mean-reversion — buy oversold, short overbought (reversal)."""
from .signals import (
    Direction,
    MeanReversionConfig,
    MeanReversionSignalGenerator,
    RankedSelection,
    ReversionScore,
    compute_score_from_closes,
    rank_and_select,
)
from .strategy import MeanReversionStrategy, StrategyConfig, TargetPortfolio, TargetWeight
from .orchestrator import JobResult, ReversionBotConfig, ReversionOrchestrator

__all__ = [
    "Direction", "MeanReversionConfig", "MeanReversionSignalGenerator",
    "RankedSelection", "ReversionScore", "compute_score_from_closes", "rank_and_select",
    "MeanReversionStrategy", "StrategyConfig", "TargetPortfolio", "TargetWeight",
    "JobResult", "ReversionBotConfig", "ReversionOrchestrator",
]
