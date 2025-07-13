"""
Configuration settings for Trading Portfolio
Centralizes all file paths and settings to avoid hardcoded values
"""
import os
import logging
from pathlib import Path
from typing import Union, Any

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors"""
    pass

class Config:
    # Database settings
    DATABASE_PATH = os.getenv('DATABASE_PATH', PROJECT_ROOT / "trading_dashboard.db")
    
    # State management
    BOT_STATE_FILE = os.getenv('BOT_STATE_FILE', PROJECT_ROOT / "bot_state.json")
    LIVE_BOT_STATE_FILE = os.getenv('LIVE_BOT_STATE_FILE', PROJECT_ROOT / "live_bot_state.json")
    
    # CSV data files
    DEFAULT_CSV_DATA = os.getenv('DEFAULT_CSV_DATA', PROJECT_ROOT / "btc_4h_2022_2025_clean.csv")
    EQUITY_CURVE_CSV = os.getenv('EQUITY_CURVE_CSV', PROJECT_ROOT / "equity_curve.csv")
    TRADE_HISTORY_CSV = os.getenv('TRADE_HISTORY_CSV', PROJECT_ROOT / "trade_history.csv")
    
    # Log files
    LOG_FILE = os.getenv('LOG_FILE', PROJECT_ROOT / "trading_bot.log")
    
    # Summary files
    DASHBOARD_SUMMARY = os.getenv('DASHBOARD_SUMMARY', PROJECT_ROOT / "dashboard_summary.json")
    
    # Trading parameters with validation
    INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', 4000))
    POSITION_SIZE_PCT = float(os.getenv('POSITION_SIZE_PCT', 0.015))
    TRADING_FEE_RATE = float(os.getenv('TRADING_FEE_RATE', 0.001))
    SLIPPAGE_RATE = float(os.getenv('SLIPPAGE_RATE', 0.0005))
    MIN_PROFIT_THRESHOLD = float(os.getenv('MIN_PROFIT_THRESHOLD', 0.005))
    
    # Exchange settings
    BYBIT_TESTNET = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'
    
    # Streamlit settings
    STREAMLIT_PORT = int(os.getenv('PORT', 8501))
    STREAMLIT_HOST = os.getenv('STREAMLIT_HOST', '0.0.0.0')
    
    # Risk management limits
    MAX_POSITION_SIZE_PCT = 0.5  # Maximum 50% position size
    MIN_POSITION_SIZE_PCT = 0.001  # Minimum 0.1% position size
    MAX_INITIAL_CAPITAL = 1000000  # Maximum $1M initial capital
    MIN_INITIAL_CAPITAL = 100  # Minimum $100 initial capital
    MAX_TRADING_FEE_RATE = 0.01  # Maximum 1% fee rate
    MAX_SLIPPAGE_RATE = 0.01  # Maximum 1% slippage
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate all configuration parameters"""
        logger = logging.getLogger(__name__)
        errors = []
        
        try:
            # Validate API keys
            api_key = os.getenv('BYBIT_API_KEY')
            api_secret = os.getenv('BYBIT_API_SECRET')
            
            if not api_key or len(api_key) < 10:
                errors.append("BYBIT_API_KEY is missing or too short")
            
            if not api_secret or len(api_secret) < 10:
                errors.append("BYBIT_API_SECRET is missing or too short")
            
            # Validate trading parameters
            if not (cls.MIN_INITIAL_CAPITAL <= cls.INITIAL_CAPITAL <= cls.MAX_INITIAL_CAPITAL):
                errors.append(f"INITIAL_CAPITAL must be between ${cls.MIN_INITIAL_CAPITAL} and ${cls.MAX_INITIAL_CAPITAL:,}")
            
            if not (cls.MIN_POSITION_SIZE_PCT <= cls.POSITION_SIZE_PCT <= cls.MAX_POSITION_SIZE_PCT):
                errors.append(f"POSITION_SIZE_PCT must be between {cls.MIN_POSITION_SIZE_PCT*100}% and {cls.MAX_POSITION_SIZE_PCT*100}%")
            
            if not (0 <= cls.TRADING_FEE_RATE <= cls.MAX_TRADING_FEE_RATE):
                errors.append(f"TRADING_FEE_RATE must be between 0% and {cls.MAX_TRADING_FEE_RATE*100}%")
            
            if not (0 <= cls.SLIPPAGE_RATE <= cls.MAX_SLIPPAGE_RATE):
                errors.append(f"SLIPPAGE_RATE must be between 0% and {cls.MAX_SLIPPAGE_RATE*100}%")
            
            if cls.MIN_PROFIT_THRESHOLD < 0 or cls.MIN_PROFIT_THRESHOLD > 0.1:
                errors.append("MIN_PROFIT_THRESHOLD must be between 0% and 10%")
            
            # Validate port
            if not (1024 <= cls.STREAMLIT_PORT <= 65535):
                errors.append("STREAMLIT_PORT must be between 1024 and 65535")
            
            # Validate file paths
            if not PROJECT_ROOT.exists():
                errors.append(f"Project root directory does not exist: {PROJECT_ROOT}")
            
            if errors:
                error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
                logger.error(error_msg)
                raise ConfigValidationError(error_msg)
            
            logger.info("✅ Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            raise ConfigValidationError(f"Configuration validation failed: {e}")
    
    @classmethod
    def sanitize_symbol(cls, symbol: str) -> str:
        """Sanitize trading symbol"""
        if not symbol or not isinstance(symbol, str):
            raise ConfigValidationError("Trading symbol must be a non-empty string")
        
        # Remove whitespace and convert to uppercase
        symbol = symbol.strip().upper()
        
        # Validate format (e.g., BTC/USDT, ETH/USD)
        if '/' not in symbol or len(symbol.split('/')) != 2:
            raise ConfigValidationError("Trading symbol must be in format 'BASE/QUOTE' (e.g., 'BTC/USDT')")
        
        base, quote = symbol.split('/')
        if not base or not quote or len(base) < 2 or len(quote) < 2:
            raise ConfigValidationError("Base and quote currencies must be at least 2 characters")
        
        return symbol
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        # Ensure parent directories exist for all file paths
        for attr_name in dir(cls):
            if attr_name.endswith('_FILE') or attr_name.endswith('_CSV') or attr_name.endswith('_PATH'):
                file_path = getattr(cls, attr_name)
                if isinstance(file_path, (str, Path)):
                    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_relative_path(cls, file_path):
        """Convert absolute path to relative path from project root"""
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        try:
            return file_path.relative_to(PROJECT_ROOT)
        except ValueError:
            # If path is not relative to project root, return as is
            return file_path

# Initialize directories and validate configuration on import
Config.ensure_directories()

# Only validate in production, not during testing
if os.getenv('TRADING_ENV') != 'test':
    try:
        Config.validate_config()
    except ConfigValidationError as e:
        logging.warning(f"Configuration validation failed: {e}")
        # Don't raise in import to allow partial functionality

# Export commonly used paths as strings for backward compatibility
DATABASE_PATH = str(Config.DATABASE_PATH)
BOT_STATE_FILE = str(Config.BOT_STATE_FILE)
LIVE_BOT_STATE_FILE = str(Config.LIVE_BOT_STATE_FILE)
DEFAULT_CSV_DATA = str(Config.DEFAULT_CSV_DATA)
EQUITY_CURVE_CSV = str(Config.EQUITY_CURVE_CSV)
TRADE_HISTORY_CSV = str(Config.TRADE_HISTORY_CSV)
LOG_FILE = str(Config.LOG_FILE)
DASHBOARD_SUMMARY = str(Config.DASHBOARD_SUMMARY) 