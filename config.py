"""
Configuration settings for Trading Portfolio
Centralizes all file paths and settings to avoid hardcoded values
"""
import os
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Environment-based configuration
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
    
    # Trading parameters
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

# Initialize directories on import
Config.ensure_directories()

# Export commonly used paths as strings for backward compatibility
DATABASE_PATH = str(Config.DATABASE_PATH)
BOT_STATE_FILE = str(Config.BOT_STATE_FILE)
LIVE_BOT_STATE_FILE = str(Config.LIVE_BOT_STATE_FILE)
DEFAULT_CSV_DATA = str(Config.DEFAULT_CSV_DATA)
EQUITY_CURVE_CSV = str(Config.EQUITY_CURVE_CSV)
TRADE_HISTORY_CSV = str(Config.TRADE_HISTORY_CSV)
LOG_FILE = str(Config.LOG_FILE)
DASHBOARD_SUMMARY = str(Config.DASHBOARD_SUMMARY) 