"""
Strategy Constants for Trading Portfolio
Centralizes strategy naming to prevent inconsistencies
"""

# Strategy identifiers - use these consistently across the codebase
class StrategyNames:
    ICHIMOKU_TREND = "IchimokuTrend"
    RSI_REVERSAL = "RsiReversal"
    
    # Database/internal identifiers (uppercase for database compatibility)
    ICHIMOKU_DB = "ICHIMOKU"
    REVERSAL_DB = "REVERSAL"
    
    # Display names for UI
    ICHIMOKU_DISPLAY = "Ichimoku Trend"
    REVERSAL_DISPLAY = "RSI Reversal"

# Strategy mappings for conversion
STRATEGY_CLASS_TO_DB = {
    StrategyNames.ICHIMOKU_TREND: StrategyNames.ICHIMOKU_DB,
    StrategyNames.RSI_REVERSAL: StrategyNames.REVERSAL_DB,
}

STRATEGY_DB_TO_CLASS = {
    StrategyNames.ICHIMOKU_DB: StrategyNames.ICHIMOKU_TREND,
    StrategyNames.REVERSAL_DB: StrategyNames.RSI_REVERSAL,
}

STRATEGY_CLASS_TO_DISPLAY = {
    StrategyNames.ICHIMOKU_TREND: StrategyNames.ICHIMOKU_DISPLAY,
    StrategyNames.RSI_REVERSAL: StrategyNames.REVERSAL_DISPLAY,
}

STRATEGY_DISPLAY_TO_CLASS = {
    StrategyNames.ICHIMOKU_DISPLAY: StrategyNames.ICHIMOKU_TREND,
    StrategyNames.REVERSAL_DISPLAY: StrategyNames.RSI_REVERSAL,
}

def get_strategy_db_name(class_name: str) -> str:
    """Convert strategy class name to database identifier"""
    return STRATEGY_CLASS_TO_DB.get(class_name, class_name)

def get_strategy_class_name(db_name: str) -> str:
    """Convert database identifier to strategy class name"""
    return STRATEGY_DB_TO_CLASS.get(db_name, db_name)

def get_strategy_display_name(class_name: str) -> str:
    """Convert strategy class name to display name"""
    return STRATEGY_CLASS_TO_DISPLAY.get(class_name, class_name)

def validate_strategy_name(name: str) -> bool:
    """Validate if strategy name is recognized"""
    return name in (
        list(STRATEGY_CLASS_TO_DB.keys()) + 
        list(STRATEGY_DB_TO_CLASS.keys()) + 
        list(STRATEGY_CLASS_TO_DISPLAY.keys()) +
        list(STRATEGY_DISPLAY_TO_CLASS.keys())
    )

# Default strategy allocations
DEFAULT_STRATEGY_ALLOCATIONS = {
    StrategyNames.ICHIMOKU_DB: 0.9,
    StrategyNames.REVERSAL_DB: 0.1
} 