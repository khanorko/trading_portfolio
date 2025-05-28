"""
Entry script: python run_portfolio.py [csv_file_path]
Runs a portfolio backtest using historical data and optionally
executes trades on Alpaca Paper Trading.
"""
import sys, json, pathlib, importlib
import pandas as pd  # type: ignore
import matplotlib.pyplot as plt 
# import os # No longer needed for keys
# from dotenv import load_dotenv # No longer needed for keys
import time

from strategies import IchimokuTrend, RsiReversal
from engines.backtest import run
# Import Exchange handler functions
from exchange_handler import initialize_exchange, execute_trade, fetch_and_print_recent_trades, fetch_historical_ohlcv

# --- Configuration ---
TARGET_EXCHANGE = "bybit"  # Options: "bybit", "alpaca"
ENABLE_PAPER_TRADING = True  # Set to True to execute paper trades
FETCH_DATA_FROM_EXCHANGE = True # Set to True to fetch data from exchange, False to use CSV
DATA_TIMEFRAME = '4h' # Timeframe for data fetching (e.g., '1m', '1h', '4h', '1d')

# --- State Persistence Configuration ---
ENABLE_STATE_PERSISTENCE = True  # Save bot state for crash recovery
RESUME_FROM_STATE = True  # Try to resume from previous state on startup
CLEAR_STATE_ON_START = False  # Set to True to start fresh (clears saved state)

# Define symbols for each exchange
EXCHANGE_SYMBOLS = {
    "bybit": "BTC/USDT", # Bybit Testnet Spot BTC against USDT
    "alpaca": "BTC/USD"  # Alpaca Paper Trading BTC against USD (if you use Alpaca)
}

DEFAULT_CSV_DATA = "btc_4h_2022_2025_clean.csv"
# ---------------------

# --- Date Range for Backtesting ---
# Set these to define the period for the backtest.
# Format: "YYYY-MM-DD"
# Set to None or empty string to use all data from the start/end of the file.
start_date_str = "2022-01-01"  # Changed to test full multi-year period including bear market
end_date_str = "2025-05-27"    # Changed to test up to present day
# ---------------------------------

# Get the correct symbol for the target exchange
TRADING_SYMBOL = EXCHANGE_SYMBOLS.get(TARGET_EXCHANGE.lower())
if not TRADING_SYMBOL:
    print(f"ERROR: Symbol not configured for exchange: {TARGET_EXCHANGE}. Exiting.")
    sys.exit(1)

# --- Initialize Exchange Connection (if enabled) ---
exchange = None # Initialize exchange object to None
actual_usdt_balance = 0.0  # Initialize balance to 0.0
if ENABLE_PAPER_TRADING:
    print(f"Paper trading enabled for {TARGET_EXCHANGE.upper()}.")
    print(f"Initializing {TARGET_EXCHANGE.upper()} connection...")
    # initialize_exchange now returns a tuple (exchange_obj, usdt_balance)
    exchange, actual_usdt_balance = initialize_exchange(
        exchange_name=TARGET_EXCHANGE,
        paper_mode=True 
    )
    if not exchange:
        print(f"ERROR: Failed to initialize {TARGET_EXCHANGE.upper()} exchange. Disabling paper trading.")
        ENABLE_PAPER_TRADING = False
    else:
        print(f"{TARGET_EXCHANGE.upper()} connection initialized successfully.")
else:
    print(f"Paper trading for {TARGET_EXCHANGE.upper()} is disabled.")

# --- Load Data ---
# DATA = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV_DATA # Keep for CSV fallback
# print(f"Loading data from: {DATA}")

df = None # Initialize df

if FETCH_DATA_FROM_EXCHANGE and exchange and TRADING_SYMBOL:
    print(f"Attempting to fetch historical data for {TRADING_SYMBOL} ({DATA_TIMEFRAME}) from {TARGET_EXCHANGE.upper()}...")
    print(f"Period: {start_date_str} to {end_date_str}")
    fetched_df = fetch_historical_ohlcv(
        exchange_obj=exchange,
        symbol=TRADING_SYMBOL,
        timeframe=DATA_TIMEFRAME,
        start_date_str=start_date_str,
        end_date_str=end_date_str
    )
    if fetched_df is not None and not fetched_df.empty:
        df = fetched_df
        print(f"Successfully fetched {len(df)} records from {TARGET_EXCHANGE.upper()}.")
        # Ensure standard column names if they differ, though fetch_historical_ohlcv should handle this.
        # Example: df.rename(columns={'some_exchange_open_col': 'open'}, inplace=True)
    else:
        print(f"WARN: Failed to fetch data from {TARGET_EXCHANGE.upper()}, or no data returned.")
        df = None # Ensure df is None if fetch failed
else:
    if not FETCH_DATA_FROM_EXCHANGE:
        print("Fetching data from exchange is disabled (FETCH_DATA_FROM_EXCHANGE = False).")
    if not exchange:
        print("Exchange not initialized, cannot fetch data from exchange.")
    if not TRADING_SYMBOL:
        print("Trading symbol not defined, cannot fetch data from exchange.")
    # No specific message here, just means conditions weren't met for fetching

# Fallback to CSV if fetching was disabled or failed
if df is None:
    DATA_PATH = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV_DATA
    print(f"Falling back to loading data from CSV: {DATA_PATH}")
    try:
        df = pd.read_csv(DATA_PATH, parse_dates=[0], index_col=0)
        df = df.sort_index()
        print(f"Data loaded successfully from CSV. Shape: {df.shape}")
        # Apply date filtering to CSV data as well, if df was loaded from CSV
        # The existing date filtering logic below will handle this if df is not None
    except FileNotFoundError:
        print(f"ERROR: CSV data file not found at {DATA_PATH}. Exiting.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load or parse CSV data file {DATA_PATH}: {e}. Exiting.")
        sys.exit(1)

# Ensure df is not None before proceeding
if df is None or df.empty:
    print(f"ERROR: No data loaded (either from exchange or CSV for the period {start_date_str} to {end_date_str}). Exiting.")
    sys.exit(1)

# --- Filter Data by Date Range (if specified) ---
# This section should now primarily apply if data was loaded from CSV,
# as fetch_historical_ohlcv already filters by date more precisely during fetch.
# However, keeping it provides a consistent check and handles the CSV case for basic range filtering.
# It also ensures that df from CSV is filtered by start/end dates before any further processing.

# Only apply this broad filtering if data came from CSV or if fetch_historical_ohlcv somehow didn't filter (should not happen)
# The main purpose now is for CSV data to be filtered according to start_date_str and end_date_str
if not (FETCH_DATA_FROM_EXCHANGE and fetched_df is not None and not fetched_df.empty):
    print("Applying date range filtering to the loaded DataFrame (primarily for CSV data)...")
    original_shape_csv_filter = df.shape
    if start_date_str:
        try:
            start_date = pd.to_datetime(start_date_str)
            df = df[df.index >= start_date]
            print(f"Filtered CSV data from start_date: {start_date_str}. Shape after start_date: {df.shape}")
        except Exception as e:
            print(f"Warning: Could not parse start_date '{start_date_str}' for CSV: {e}. Using all data from the beginning of CSV.")

    if end_date_str:
        try:
            end_date = pd.to_datetime(end_date_str)
            # For end_date, ensure we include the whole day if no time is specified
            if end_date.time() == pd.Timestamp('00:00:00').time():
                end_date_filter = end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            else:
                end_date_filter = end_date
            df = df[df.index <= end_date_filter]
            print(f"Filtered CSV data up to end_date: {end_date_str}. Shape after end_date: {df.shape}")
        except Exception as e:
            print(f"Warning: Could not parse end_date '{end_date_str}' for CSV: {e}. Using all data up to the end of CSV.")
    
    if df.empty and original_shape_csv_filter[0] > 0 : # if it was not empty before filtering
        print(f"ERROR: No data remains after applying date filters ({start_date_str} to {end_date_str}) to CSV data. Original CSV shape for period: {original_shape_csv_filter}. Exiting.")
        sys.exit(1)

# Final check if df is empty after all loading and filtering attempts
if df.empty:
    print(f"ERROR: DataFrame is empty after all data loading and filtering attempts for period {start_date_str} to {end_date_str}. Exiting.")
    sys.exit(1)
# --------------------------------------------------

# Attempt to infer frequency for the DataFrame index if it's a DatetimeIndex
if isinstance(df.index, pd.DatetimeIndex):
    inferred_freq = pd.infer_freq(df.index)
    if inferred_freq:
        df = df.asfreq(inferred_freq) # Set the inferred frequency
    # else: print("Warning: Could not infer frequency for Chikou Span plotting.") # Optional: inform user

strats = [IchimokuTrend(), RsiReversal()]

# Define KIJUN for plotting, ensure it's available globally in this script context for the plot function
# Defaulting to a common value, will be overwritten if IchimokuTrend is in strats
KIJUN_plot = 26 
for strat_instance_check in strats:
    if isinstance(strat_instance_check, IchimokuTrend):
        KIJUN_plot = strat_instance_check.KIJUN
        break

# --- Plotting Function ---
def plot_results(df_full: pd.DataFrame, equity_df: pd.DataFrame, strategies_list: list):
    """Plots indicators and equity curve."""
    # Ensure DataFrame has the necessary columns from precompute_indicators
    # We make a copy to avoid SettingWithCopyWarning if df_full is a slice
    df_plot = df_full.copy()

    # Plot 1: Price and Ichimoku Cloud
    fig1, axes1 = plt.subplots(3, 1, figsize=(14, 15), sharex=True)
    
    # Subplot 1: Price, Tenkan, Kijun, Cloud
    axes1[0].plot(df_plot.index, df_plot['close'], label='Price', color='black')
    if 'tenkan' in df_plot.columns:
        axes1[0].plot(df_plot.index, df_plot['tenkan'], label='Tenkan-sen', color='red')
    if 'kijun' in df_plot.columns:
        axes1[0].plot(df_plot.index, df_plot['kijun'], label='Kijun-sen', color='blue')
    if 'ssa' in df_plot.columns and 'ssb' in df_plot.columns:
        axes1[0].fill_between(df_plot.index, df_plot['ssa'], df_plot['ssb'], 
                              where=df_plot['ssa'] >= df_plot['ssb'], color='lightgreen', alpha=0.4, label='Kumo (Bullish)')
        axes1[0].fill_between(df_plot.index, df_plot['ssa'], df_plot['ssb'], 
                              where=df_plot['ssa'] < df_plot['ssb'], color='lightcoral', alpha=0.4, label='Kumo (Bearish)')
    axes1[0].set_title('Price and Ichimoku Cloud')
    axes1[0].legend()
    axes1[0].grid(True)

    # Subplot 2: Chikou Span (current close shifted back by KIJUN_plot periods)
    # The 'chikou' column from ichimoku.py is df.close.shift(-KIJUN_plot), which is future price at current time.
    # For standard Chikou visualization (current price plotted in the past):
    chikou_to_plot = df_plot['close'].shift(KIJUN_plot) # Positive shift moves data to the right (future), effectively plotting past data at current time
    axes1[1].plot(df_plot.index, chikou_to_plot, label=f'Chikou Span (Close shifted +{KIJUN_plot})', color='purple', linestyle='--')
    axes1[1].plot(df_plot.index, df_plot['close'], label='Price (Current)', color='black', alpha=0.7)
    axes1[1].set_title('Chikou Span vs Price')
    axes1[1].legend()
    axes1[1].grid(True)

    # Subplot 3: RSI
    if 'RSI' in df_plot.columns:
        axes1[2].plot(df_plot.index, df_plot['RSI'], label='RSI', color='orange')
        axes1[2].axhline(70, linestyle='--', color='red', label='Overbought (70)')
        axes1[2].axhline(35, linestyle='--', color='green', label='Oversold (35)') # As per RsiReversal
    axes1[2].set_title('RSI')
    axes1[2].legend()
    axes1[2].grid(True)
    
    plt.xlabel('Date')
    plt.tight_layout()
    fig1.suptitle('Technical Indicators', fontsize=16)
    plt.subplots_adjust(top=0.94)

    # Plot 2: Equity Curve
    fig2, ax2 = plt.subplots(figsize=(14, 7))
    for col in equity_df.columns:
        ax2.plot(equity_df.index, equity_df[col], label=col)
    ax2.set_title('Portfolio Equity Curve (Simulation)')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Equity')
    ax2.legend()
    ax2.grid(True)
    plt.tight_layout()
    
    # Try to prevent plots from closing immediately in some environments
    if plt.get_backend() == 'agg':
        fig1.savefig('indicators_plot.png')
        fig2.savefig('equity_curve_plot.png')
        print("Plots saved as indicators_plot.png and equity_curve_plot.png as 'agg' backend is used.")
    else:
        plt.show()

# --- Main Execution ---
# df is already loaded and sorted here

# Determine initial capital for simulation
# Use actual fetched balance if paper trading is enabled and balance is positive
# Otherwise, use a default (e.g., the 4000 we set previously, or a new default)
simulation_initial_capital = 4000 # Default if not using fetched balance

if ENABLE_PAPER_TRADING and exchange and actual_usdt_balance > 0:
    print(f"Using actual fetched USDT balance from {TARGET_EXCHANGE.upper()} as initial capital: {actual_usdt_balance:.2f} USDT")
    simulation_initial_capital = actual_usdt_balance
elif ENABLE_PAPER_TRADING and exchange and actual_usdt_balance <= 0:
    print(f"WARNING: Fetched USDT balance is {actual_usdt_balance:.2f}. Paper trading might fail due to no funds.")
    print(f"         Proceeding with default simulation capital: {simulation_initial_capital:.2f} USDT for backtest logic.")
    # Potentially disable paper trading if balance is zero, or let it try and fail
    # ENABLE_PAPER_TRADING = False # Optional: force disable if no balance
else:
    print(f"Paper trading not enabled or exchange not initialized. Using default simulation capital: {simulation_initial_capital:.2f} USDT")

# Precompute indicators for all strategies on the main df so plot_results can access them
print("Precomputing indicators for plotting...")
for strat_instance in strats:
    strat_instance.precompute_indicators(df) 
    # This makes sure df has 'tenkan', 'kijun', 'ssa', 'ssb', 'chikou', 'RSI', 'ATR' before plotting
    # Need to make KIJUN accessible for Chikou plot, or pass it. For now, let's try to get it from the IchimokuTrend instance.
    if isinstance(strat_instance, IchimokuTrend):
        KIJUN_plot = strat_instance.KIJUN # Assuming KIJUN is an attribute or class variable

# Add new configuration for realistic costs
ENABLE_REALISTIC_COSTS = True  # Set to True to include fees and slippage
TRADING_FEE_RATE = 0.001      # 0.1% per trade (Bybit standard)
SLIPPAGE_RATE = 0.0005        # 0.05% slippage
MIN_PROFIT_THRESHOLD = 0.005  # 0.5% instead of 1.5%

# Handle state clearing if requested
if CLEAR_STATE_ON_START and ENABLE_STATE_PERSISTENCE:
    try:
        from engines.state_manager import StateManager
        state_manager = StateManager()
        state_manager.clear_state()
        print("🗑️ Previous state cleared - starting fresh")
    except ImportError:
        print("⚠️ StateManager not available - cannot clear state")

print("Running enhanced backtest simulation with realistic costs...")
equity = run(
    df,
    strats,
    initial_capital=simulation_initial_capital, 
    # Pass Exchange details to the run function
    enable_paper_trading=ENABLE_PAPER_TRADING,
    exchange_obj=exchange,
    exchange_symbol=TRADING_SYMBOL,
    # New parameters for realistic costs
    trading_fee_rate=TRADING_FEE_RATE,
    slippage_rate=SLIPPAGE_RATE,
    min_profit_threshold=MIN_PROFIT_THRESHOLD,
    enable_realistic_costs=ENABLE_REALISTIC_COSTS,
    # New parameters for state persistence
    enable_state_persistence=ENABLE_STATE_PERSISTENCE,
    resume_from_state=RESUME_FROM_STATE
)
equity.to_csv("equity_curve.csv")
# The print statement from backtest.py will show detailed totals

# Call plotting function
plot_results(df, equity, strats)

# Fetch and print actual recent trades from the exchange if paper trading was enabled
if ENABLE_PAPER_TRADING and exchange:
    print(f"\nFetching actual trades from {TARGET_EXCHANGE.upper()} (may include trades from previous runs)...")
    fetch_and_print_recent_trades(exchange, TRADING_SYMBOL, limit=50)

print("\nScript finished.")
