import ccxt
import pandas as pd
import decimal
import time
import traceback
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Optional, Tuple, Dict, Any
from config import Config, ConfigValidationError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- API Configuration from Environment Variables ---
# Alpaca Configuration
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_API_SECRET = os.getenv('ALPACA_API_SECRET')

# Bybit Configuration
BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET')
BYBIT_TESTNET = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'

# Validate that required keys are loaded
if not BYBIT_API_KEY or not BYBIT_API_SECRET:
    logger.warning("WARNING: BYBIT_API_KEY and BYBIT_API_SECRET not found in environment variables.")
    logger.warning("Please create a .env file with your API keys or set them as environment variables.")

class ExchangeError(Exception):
    """Custom exception for exchange-related errors"""
    pass

class RetryableExchangeError(ExchangeError):
    """Exception for errors that should be retried"""
    pass

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying failed exchange operations"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RetryableExchangeError as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                except ExchangeError as e:
                    # Non-retryable errors
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
                except Exception as e:
                    # Unexpected errors
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"Retrying unexpected error in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        last_exception = e
                    else:
                        raise
            
            raise last_exception
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=1.0)
def initialize_exchange(exchange_name="bybit", api_key=None, secret_key=None, paper_mode=True) -> Tuple[Optional[Any], float]:
    """
    Initialize exchange connection with comprehensive error handling and retry logic
    
    Returns:
        Tuple of (exchange_object, balance) or (None, 0.0) on failure
    """
    try:
        # Validate exchange name
        if exchange_name not in ['bybit', 'alpaca']:
            raise ExchangeError(f"Unsupported exchange: {exchange_name}")
        
        # Validate inputs
        if not exchange_name or not isinstance(exchange_name, str):
            raise ExchangeError("Exchange name must be a non-empty string")
        
        logger.info(f"Initializing {exchange_name.upper()} exchange connection...")
        
        if exchange_name.lower() == "bybit":
            return _initialize_bybit(api_key, secret_key, paper_mode)
        elif exchange_name.lower() == "alpaca":
            return _initialize_alpaca(api_key, secret_key, paper_mode)
        else:
            raise ExchangeError(f"Exchange {exchange_name} not implemented")
            
    except (ExchangeError, RetryableExchangeError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing {exchange_name}: {e}")
        raise RetryableExchangeError(f"Failed to initialize {exchange_name}: {e}")

def _initialize_bybit(api_key=None, secret_key=None, paper_mode=True) -> Tuple[Optional[Any], float]:
    """Initialize Bybit exchange with error handling"""
    try:
        # Use provided keys or fall back to environment variables
        api_key = api_key or BYBIT_API_KEY
        secret_key = secret_key or BYBIT_API_SECRET
        
        if not api_key or not secret_key:
            raise ExchangeError("Bybit API key and secret are required")
        
        # Validate API key format (basic check)
        if len(api_key) < 10 or len(secret_key) < 10:
            raise ExchangeError("Invalid API key or secret format")
        
        # Configure exchange
        exchange_config = {
            'apiKey': api_key,
            'secret': secret_key,
            'sandbox': BYBIT_TESTNET,  # Use testnet/sandbox mode
            'enableRateLimit': True,
            'timeout': 30000,  # 30 second timeout
            'options': {
                'defaultType': 'spot'  # Use spot trading
            }
        }
        
        logger.info(f"Using Bybit {'Testnet' if BYBIT_TESTNET else 'Mainnet'}")
        
        # Initialize exchange
        exchange = ccxt.bybit(exchange_config)
        
        # Test connection
        try:
            exchange.load_markets()
            logger.info("✅ Bybit markets loaded successfully")
        except Exception as e:
            raise RetryableExchangeError(f"Failed to load Bybit markets: {e}")
        
        # Fetch account balance
        balance = 0.0
        try:
            balance_info = exchange.fetch_balance()
            balance = balance_info.get('USDT', {}).get('total', 0.0)
            logger.info(f"💰 Current USDT balance: {balance:.2f}")
        except Exception as e:
            logger.warning(f"Could not fetch balance (proceeding anyway): {e}")
        
        return exchange, balance
        
    except (ExchangeError, RetryableExchangeError):
        raise
    except ccxt.NetworkError as e:
        raise RetryableExchangeError(f"Network error connecting to Bybit: {e}")
    except ccxt.ExchangeError as e:
        raise ExchangeError(f"Bybit exchange error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in Bybit initialization: {e}")
        raise RetryableExchangeError(f"Unexpected Bybit error: {e}")

def _initialize_alpaca(api_key=None, secret_key=None, paper_mode=True) -> Tuple[Optional[Any], float]:
    """Initialize Alpaca exchange (placeholder implementation)"""
    try:
        logger.warning("Alpaca integration not fully implemented")
        # Placeholder for Alpaca implementation
        return None, 0.0
        
    except Exception as e:
        logger.error(f"Alpaca initialization error: {e}")
        raise ExchangeError(f"Alpaca initialization failed: {e}")

@retry_on_failure(max_retries=2, delay=0.5)
def execute_trade(exchange, symbol: str, side: str, amount: float, price: float = None, order_type: str = "market") -> Optional[Dict[str, Any]]:
    """
    Execute a trade with comprehensive error handling
    
    Returns:
        Order information dict or None on failure
    """
    try:
        # Input validation
        if not exchange:
            raise ExchangeError("Exchange object is None")
        
        # Validate symbol format
        try:
            symbol = Config.sanitize_symbol(symbol)
        except ConfigValidationError as e:
            raise ExchangeError(f"Invalid symbol: {e}")
        
        if side not in ['buy', 'sell']:
            raise ExchangeError(f"Invalid side: {side}. Must be 'buy' or 'sell'")
        
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ExchangeError("Amount must be a positive number")
        
        if price is not None and (not isinstance(price, (int, float)) or price <= 0):
            raise ExchangeError("Price must be a positive number if specified")
        
        if order_type not in ['market', 'limit']:
            raise ExchangeError(f"Invalid order type: {order_type}. Must be 'market' or 'limit'")
        
        logger.info(f"🔄 Executing {side.upper()} order: {amount} {symbol} @ {price or 'market'}")
        
        # Prepare order parameters
        order_params = {
            'symbol': symbol,
            'type': order_type,
            'side': side,
            'amount': amount,
        }
        
        if order_type == 'limit' and price is not None:
            order_params['price'] = price
        
        # Execute order
        try:
            order = exchange.create_order(**order_params)
            logger.info(f"✅ Order executed successfully: {order.get('id', 'N/A')}")
            return order
            
        except ccxt.InsufficientFunds as e:
            raise ExchangeError(f"Insufficient funds for {side} order: {e}")
        except ccxt.InvalidOrder as e:
            raise ExchangeError(f"Invalid order parameters: {e}")
        except ccxt.NetworkError as e:
            raise RetryableExchangeError(f"Network error during order execution: {e}")
        except ccxt.ExchangeNotAvailable as e:
            raise RetryableExchangeError(f"Exchange not available: {e}")
        except ccxt.ExchangeError as e:
            raise ExchangeError(f"Exchange error during order execution: {e}")
            
    except (ExchangeError, RetryableExchangeError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error executing trade: {e}")
        raise RetryableExchangeError(f"Unexpected trade execution error: {e}")

@retry_on_failure(max_retries=2, delay=1.0)
def fetch_historical_ohlcv(exchange_obj, symbol: str, timeframe: str = '4h', 
                          start_date_str: str = None, end_date_str: str = None, 
                          limit: int = 1000) -> Optional[pd.DataFrame]:
    """
    Fetch historical OHLCV data with comprehensive error handling
    
    Returns:
        DataFrame with OHLCV data or None on failure
    """
    try:
        if not exchange_obj:
            raise ExchangeError("Exchange object is None")
        
        # Validate and sanitize symbol
        try:
            symbol = Config.sanitize_symbol(symbol)
        except ConfigValidationError as e:
            raise ExchangeError(f"Invalid symbol: {e}")
        
        # Validate timeframe
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        if timeframe not in valid_timeframes:
            raise ExchangeError(f"Invalid timeframe: {timeframe}. Valid options: {valid_timeframes}")
        
        logger.info(f"📊 Fetching {timeframe} data for {symbol}")
        
        # Parse date range
        since = None
        until = None
        
        if start_date_str:
            try:
                since = exchange_obj.parse8601(f"{start_date_str}T00:00:00Z")
            except Exception as e:
                raise ExchangeError(f"Invalid start date format: {start_date_str}. Use YYYY-MM-DD")
        
        if end_date_str:
            try:
                until = exchange_obj.parse8601(f"{end_date_str}T23:59:59Z")
            except Exception as e:
                raise ExchangeError(f"Invalid end date format: {end_date_str}. Use YYYY-MM-DD")
        
        # Fetch data
        try:
            ohlcv = exchange_obj.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )
            
            if not ohlcv:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            df.drop('timestamp', axis=1, inplace=True)
            
            # Filter by end date if specified
            if until:
                end_datetime = pd.to_datetime(until, unit='ms')
                df = df[df.index <= end_datetime]
            
            logger.info(f"✅ Fetched {len(df)} data points from {df.index[0]} to {df.index[-1]}")
            return df
            
        except ccxt.NetworkError as e:
            raise RetryableExchangeError(f"Network error fetching data: {e}")
        except ccxt.ExchangeNotAvailable as e:
            raise RetryableExchangeError(f"Exchange not available: {e}")
        except ccxt.ExchangeError as e:
            raise ExchangeError(f"Exchange error fetching data: {e}")
            
    except (ExchangeError, RetryableExchangeError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching historical data: {e}")
        raise RetryableExchangeError(f"Unexpected data fetch error: {e}")

@retry_on_failure(max_retries=2, delay=0.5)
def fetch_and_print_recent_trades(exchange, symbol: str, limit: int = 10):
    """
    Fetch and display recent trades with error handling
    """
    try:
        if not exchange:
            logger.warning("Exchange object is None, cannot fetch trades")
            return
        
        # Validate and sanitize symbol
        try:
            symbol = Config.sanitize_symbol(symbol)
        except ConfigValidationError as e:
            raise ExchangeError(f"Invalid symbol: {e}")
        
        logger.info(f"📈 Fetching last {limit} trades for {symbol}")
        
        try:
            trades = exchange.fetch_my_trades(symbol=symbol, limit=limit)
            
            if not trades:
                logger.info("No recent trades found")
                return
            
            logger.info(f"Recent {len(trades)} trades:")
            for trade in trades[-limit:]:  # Show most recent
                logger.info(
                    f"  {trade['datetime']} - {trade['side'].upper()} "
                    f"{trade['amount']} @ {trade['price']} (Fee: {trade.get('fee', {}).get('cost', 0)})"
                )
                
        except ccxt.NetworkError as e:
            raise RetryableExchangeError(f"Network error fetching trades: {e}")
        except ccxt.ExchangeNotAvailable as e:
            raise RetryableExchangeError(f"Exchange not available: {e}")
        except ccxt.ExchangeError as e:
            logger.warning(f"Could not fetch trades: {e}")
            
    except (ExchangeError, RetryableExchangeError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching trades: {e}")
        raise RetryableExchangeError(f"Unexpected trade fetch error: {e}")

def safe_exchange_operation(func, *args, **kwargs):
    """
    Wrapper for safe exchange operations with fallback
    """
    try:
        return func(*args, **kwargs)
    except ExchangeError as e:
        logger.error(f"Exchange operation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in exchange operation: {e}")
        return None

# Health check function
def check_exchange_health(exchange) -> Dict[str, Any]:
    """
    Perform health check on exchange connection
    
    Returns:
        Dict with health status information
    """
    health_status = {
        'connected': False,
        'markets_loaded': False,
        'balance_accessible': False,
        'last_check': datetime.now().isoformat(),
        'errors': []
    }
    
    try:
        if not exchange:
            health_status['errors'].append("Exchange object is None")
            return health_status
        
        health_status['connected'] = True
        
        # Test market loading
        try:
            exchange.load_markets()
            health_status['markets_loaded'] = True
        except Exception as e:
            health_status['errors'].append(f"Markets not accessible: {e}")
        
        # Test balance access
        try:
            balance = exchange.fetch_balance()
            health_status['balance_accessible'] = True
        except Exception as e:
            health_status['errors'].append(f"Balance not accessible: {e}")
        
    except Exception as e:
        health_status['errors'].append(f"Health check error: {e}")
    
    return health_status 