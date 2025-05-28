from __future__ import annotations
import numpy as np
import pandas as pd
from .base import Strategy

RSI_LEN = 14
OVERSOLD = 30  # More strict oversold level
OVERBOUGHT = 70
ATR_LEN = 14
STOP_ATR_MULT = 1.5  # Wider stop loss
RR_TARGET = 2.5  # More conservative target
MIN_RSI_DIVERGENCE = 5  # Minimum RSI change for entry
TREND_FILTER_PERIOD = 50  # Period for trend filter

def compute_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = (delta.clip(lower=0)).rolling(length).mean()
    loss = (-delta.clip(upper=0)).rolling(length).mean()
    rs = gain / loss
    return 100 - 100/(1+rs)

class RsiReversal(Strategy):
    def __init__(self, allocation: float = 0.1):
        super().__init__("REVERSAL", allocation)

    def precompute_indicators(self, df: pd.DataFrame) -> None:
        df["RSI"] = compute_rsi(df.close, RSI_LEN)
        
        # ATR calculation
        tr1 = df.high - df.low
        tr2 = (df.high - df.close.shift()).abs()
        tr3 = (df.low - df.close.shift()).abs()
        tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
        df["ATR"] = tr.rolling(ATR_LEN).mean()
        
        # Trend filter - simple moving average
        df["SMA_50"] = df.close.rolling(TREND_FILTER_PERIOD).mean()
        
        # RSI momentum (rate of change)
        df["RSI_ROC"] = df["RSI"].diff(3)  # 3-period RSI change

    def entry_signal(self, idx, df):
        if df.index.get_loc(idx) < 3:  # Need at least 3 periods for RSI_ROC
            return False
            
        row = df.loc[idx]
        prev_idx = df.index[df.index.get_loc(idx) - 1] if df.index.get_loc(idx) > 0 else idx
        prev_row = df.loc[prev_idx]
        
        # Basic RSI reversal condition (more strict)
        rsi_reversal = prev_row.RSI < OVERSOLD and row.RSI >= OVERSOLD
        
        # Additional filters to reduce trade frequency:
        
        # 1. RSI momentum filter - RSI should be recovering strongly
        rsi_momentum_ok = row.RSI_ROC > MIN_RSI_DIVERGENCE
        
        # 2. Trend filter - only trade reversals in overall uptrend or neutral
        # (price above or near 50-period MA)
        trend_ok = row.close >= row.SMA_50 * 0.98  # Allow 2% below MA
        
        # 3. Volatility filter - only trade when ATR is reasonable
        atr_ok = pd.notna(row.ATR) and row.ATR > 0
        
        # 4. Price action filter - ensure we're not in a strong downtrend
        # Check that current price is not significantly below recent high
        recent_high = df.high.rolling(10).max().loc[idx]
        price_action_ok = row.close >= recent_high * 0.95  # Within 5% of recent high
        
        return (rsi_reversal and rsi_momentum_ok and trend_ok and 
                atr_ok and price_action_ok)

    def exit_signal(self, idx, df, entry_price):
        # More conservative exit with wider stops and lower targets
        price = df.loc[idx].close
        risk = STOP_ATR_MULT * df.loc[idx].ATR
        
        # Exit conditions:
        # 1. Stop loss hit
        stop_hit = price <= entry_price - risk
        
        # 2. Target hit
        target_hit = price >= entry_price + RR_TARGET * risk
        
        # 3. RSI becomes overbought (take profits)
        rsi_overbought = df.loc[idx].RSI >= OVERBOUGHT
        
        # 4. Trend turns negative (price falls below MA)
        trend_negative = price < df.loc[idx].SMA_50 * 0.95
        
        return stop_hit or target_hit or rsi_overbought or trend_negative
