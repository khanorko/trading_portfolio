from __future__ import annotations
import numpy as np
import pandas as pd
from .base import Strategy

TENKAN  = 9
KIJUN_const   = 26
SENKOU_B = 52
ATR_LEN = 14
STOP_ATR_MULT = 2.0

class IchimokuTrend(Strategy):
    KIJUN = KIJUN_const

    def __init__(self, allocation: float = 0.9):
        super().__init__("ICHIMOKU", allocation)

    def precompute_indicators(self, df: pd.DataFrame) -> None:
        high9 = df.high.rolling(TENKAN).max()
        low9  = df.low.rolling(TENKAN).min()
        df["tenkan"] = (high9 + low9)/2

        high26 = df.high.rolling(self.KIJUN).max()
        low26  = df.low.rolling(self.KIJUN).min()
        df["kijun"] = (high26 + low26)/2

        df["ssa"] = ((df.tenkan + df.kijun)/2).shift(self.KIJUN)
        high52 = df.high.rolling(SENKOU_B).max()
        low52  = df.low.rolling(SENKOU_B).min()
        df["ssb"] = ((high52 + low52)/2).shift(self.KIJUN)

        df["chikou"] = df.close.shift(-self.KIJUN)

        # ATR
        tr1 = df.high - df.low
        tr2 = (df.high - df.close.shift()).abs()
        tr3 = (df.low - df.close.shift()).abs()
        tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
        df["ATR"] = tr.rolling(ATR_LEN).mean()

    # ----- signal helpers -----
    def _long_entry_cond(self, r):
        # Check if we have all required values before evaluating
        if pd.isna(r.tenkan) or pd.isna(r.kijun) or pd.isna(r.ssa) or pd.isna(r.ssb) or pd.isna(r.chikou):
            return False
            
        return (
            r.tenkan > r.kijun and
            r.close > max(r.ssa, r.ssb) and
            r.chikou > r.close and
            r.ssa > r.ssb
        )

    def _long_exit_cond(self, r):
        if pd.isna(r.tenkan) or pd.isna(r.kijun):
            return False
            
        return r.tenkan < r.kijun

    # Interface implementations
    def entry_signal(self, idx, df):
        return self._long_entry_cond(df.loc[idx])

    def exit_signal(self, idx, df, entry_price):
        return self._long_exit_cond(df.loc[idx])
