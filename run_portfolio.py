"""
Entry script: python run_portfolio.py data.csv
"""
import sys, json, pathlib, importlib
import pandas as pd  # type: ignore
import matplotlib.pyplot as plt # For plotting
from strategies import IchimokuTrend, RsiReversal
from engines.backtest import run

DATA = sys.argv[1] if len(sys.argv)>1 else "btc_4h_2022_2025_clean.csv"

df = pd.read_csv(DATA, parse_dates=[0], index_col=0)
df = df.sort_index()

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
    ax2.set_title('Portfolio Equity Curve')
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
# Precompute indicators for all strategies on the main df so plot_results can access them
# The run function also calls precompute_indicators, but we need them on df for plotting.
for strat_instance in strats:
    strat_instance.precompute_indicators(df) 
    # This makes sure df has 'tenkan', 'kijun', 'ssa', 'ssb', 'chikou', 'RSI', 'ATR' before plotting
    # Need to make KIJUN accessible for Chikou plot, or pass it. For now, let's try to get it from the IchimokuTrend instance.
    if isinstance(strat_instance, IchimokuTrend):
        KIJUN_plot = strat_instance.KIJUN # Assuming KIJUN is an attribute or class variable

equity = run(df, strats)
equity.to_csv("equity_curve.csv")
# The print statement from backtest.py will show detailed totals

# Call plotting function
plot_results(df, equity, strats)

print("Script finished. Plots should be displayed or saved. Check equity_curve.csv for detailed equity data.")
