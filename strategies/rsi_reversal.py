from __future__ import annotations
import numpy as np
import pandas as pd
from .base import Strategy

RSI_LEN = 14
OVERSOLD = 35
OVERBOUGHT = 70
ATR_LEN = 14
STOP_ATR_MULT = 1.0
RR_TARGET = 3.0

def compute_rsi(close: pd.Series, length:int=14) -> pd.Series:
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
        tr1 = df.high - df.low
        tr2 = (df.high - df.close.shift()).abs()
        tr3 = (df.low - df.close.shift()).abs()
        tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
        df["ATR"] = tr.rolling(ATR_LEN).mean()

    def entry_signal(self, idx, df):
        row = df.loc[idx]
        prev_idx = df.index[df.index.get_loc(idx) - 1] if df.index.get_loc(idx) > 0 else idx
        prev_row = df.loc[prev_idx]
        
        return prev_row.RSI < OVERSOLD and row.RSI >= OVERSOLD

    def exit_signal(self, idx, df, entry_price):
        # price reaches either 3R target or 1 ATR stop
        price = df.loc[idx].close
        risk  = STOP_ATR_MULT * df.loc[idx].ATR
        return price <= entry_price - risk or price >= entry_price + RR_TARGET*risk
