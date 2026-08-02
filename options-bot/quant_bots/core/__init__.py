"""
Shared core library for the quant bots.

Everything in here is strategy-agnostic infrastructure, lifted and proven from
the options bot: the Tradier client (now with equity orders), the market
calendar, the trade journal, Discord notifications, and the daily account-state
snapshot. The trend-following and momentum bots build their strategy-specific
logic on top of this.
"""
from .account_state import AccountState
from .sim_portfolio import SimHolding, SimPortfolio
from .sim_execution import (
    apply_orders_to_sim, finalize_sim, load_sim, resolve_prices, sim_paths,
)
from .daily_summary import build_summaries, post_end_of_day, summarize_bot
from .regime import MarketRegime, RegimeConfig, RegimeFilter, classify_regime_from_closes
from .calendar import (
    describe_market_state,
    is_market_open,
    is_trading_day,
    now_eastern,
)
from .discord import DiscordNotifier
from .journal import TradeJournal
from .tradier import (
    EquitySide,
    OrderDuration,
    OrderType,
    TradierAPIError,
    TradierAuthError,
    TradierClient,
    TradierConfig,
    TradierError,
    TradierRateLimitError,
)
from .occ_symbol import OptionType, build_occ_symbol, parse_occ_symbol
from .universe_builder import (
    UniverseBuilder,
    UniverseConfig,
    UniverseSnapshot,
    UniverseTicker,
)
from .trading_mode import (
    BrokerEnvironmentMismatchError,
    LiveTradingNotAuthorizedError,
    TradingMode,
    is_sim,
    mode_from_env,
    places_real_orders,
    validate_mode_against_broker,
)

__all__ = [
    "AccountState",
    "SimHolding",
    "SimPortfolio",
    "apply_orders_to_sim",
    "finalize_sim",
    "load_sim",
    "resolve_prices",
    "sim_paths",
    "build_summaries",
    "post_end_of_day",
    "summarize_bot",
    "MarketRegime",
    "RegimeConfig",
    "RegimeFilter",
    "classify_regime_from_closes",
    "describe_market_state",
    "is_market_open",
    "is_trading_day",
    "now_eastern",
    "DiscordNotifier",
    "TradeJournal",
    "EquitySide",
    "OrderDuration",
    "OrderType",
    "TradierClient",
    "TradierConfig",
    "TradierError",
    "TradierAuthError",
    "TradierRateLimitError",
    "TradierAPIError",
    "OptionType",
    "build_occ_symbol",
    "parse_occ_symbol",
    "UniverseBuilder",
    "UniverseConfig",
    "UniverseSnapshot",
    "UniverseTicker",
    "TradingMode",
    "mode_from_env",
    "places_real_orders",
    "is_sim",
    "validate_mode_against_broker",
    "LiveTradingNotAuthorizedError",
    "BrokerEnvironmentMismatchError",
]
