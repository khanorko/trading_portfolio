from __future__ import annotations
import numpy as np
import pandas as pd
from .base import Strategy

TENKAN = 9
KIJUN_const = 26
SENKOU_B = 52
ATR_LEN = 14
STOP_ATR_MULT = 2.5  # Wider stop loss
MAX_POSITION_RISK = 0.02  # Maximum 2% risk per trade
MAX_DRAWDOWN_LIMIT = 0.15  # Maximum 15% drawdown before stopping

class IchimokuTrend(Strategy):
    KIJUN = KIJUN_const

    def __init__(self, allocation: float = 0.9):
        super().__init__("ICHIMOKU", allocation)
        self.max_drawdown = 0.0
        self.peak_equity = 0.0

    def precompute_indicators(self, df: pd.DataFrame) -> None:
        high9 = df.high.rolling(TENKAN).max()
        low9 = df.low.rolling(TENKAN).min()
        df["tenkan"] = (high9 + low9)/2

        high26 = df.high.rolling(self.KIJUN).max()
        low26 = df.low.rolling(self.KIJUN).min()
        df["kijun"] = (high26 + low26)/2

        df["ssa"] = ((df.tenkan + df.kijun)/2).shift(self.KIJUN)
        high52 = df.high.rolling(SENKOU_B).max()
        low52 = df.low.rolling(SENKOU_B).min()
        df["ssb"] = ((high52 + low52)/2).shift(self.KIJUN)

        df["chikou"] = df.close.shift(-self.KIJUN)

        # ATR for volatility-based position sizing
        tr1 = df.high - df.low
        tr2 = (df.high - df.close.shift()).abs()
        tr3 = (df.low - df.close.shift()).abs()
        tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
        df["ATR"] = tr.rolling(ATR_LEN).mean()
        
        # Additional risk management indicators
        df["volatility_regime"] = df["ATR"].rolling(20).rank(pct=True)  # Volatility percentile
        df["trend_strength"] = abs(df.close - df.close.shift(20)) / df["ATR"]  # Trend strength

    def generate_signal(self, row: pd.Series, idx: pd.Timestamp) -> str:
        """
        Generate BUY/SELL/HOLD signals based on Ichimoku conditions.
        """
        # Check if we have all required values
        if (pd.isna(row.tenkan) or pd.isna(row.kijun) or 
            pd.isna(row.ssa) or pd.isna(row.ssb) or pd.isna(row.chikou)):
            return "HOLD"
        
        # BUY signal: Strong Ichimoku bullish alignment
        if (row.tenkan > row.kijun and
            row.close > max(row.ssa, row.ssb) and
            row.chikou > row.close and
            row.ssa > row.ssb and
            row.volatility_regime < 0.9 and  # Not in extreme volatility
            row.trend_strength > 2.0):  # Strong trend
            return "BUY"
        
        # SELL signal: Ichimoku bearish conditions
        elif (row.tenkan < row.kijun or
              row.close < min(row.ssa, row.ssb) or
              row.volatility_regime > 0.95):  # Volatility spike
            return "SELL"
        
        return "HOLD"

    def _long_entry_cond(self, r, current_equity=None, initial_capital=None):
        # Check if we have all required values
        if pd.isna(r.tenkan) or pd.isna(r.kijun) or pd.isna(r.ssa) or pd.isna(r.ssb) or pd.isna(r.chikou):
            return False
        
        # Basic Ichimoku conditions (more strict)
        basic_conditions = (
            r.tenkan > r.kijun and
            r.close > max(r.ssa, r.ssb) and
            r.chikou > r.close and
            r.ssa > r.ssb
        )
        
        if not basic_conditions:
            return False
        
        # Additional risk management filters:
        
        # 1. Volatility filter - avoid trading in extreme volatility
        volatility_ok = r.volatility_regime < 0.9  # Not in top 10% volatility
        
        # 2. Trend strength filter - ensure strong trend
        trend_strong = r.trend_strength > 2.0  # Strong trend relative to ATR
        
        # 3. Cloud thickness filter - avoid thin clouds
        cloud_thickness = abs(r.ssa - r.ssb) / r.close
        cloud_thick_enough = cloud_thickness > 0.005  # At least 0.5% thick
        
        # 4. Drawdown protection
        drawdown_ok = True
        if current_equity is not None and initial_capital is not None:
            if self.peak_equity == 0:
                self.peak_equity = initial_capital
            else:
                self.peak_equity = max(self.peak_equity, current_equity)
            
            current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
            self.max_drawdown = max(self.max_drawdown, current_drawdown)
            drawdown_ok = current_drawdown < MAX_DRAWDOWN_LIMIT
        
        return (basic_conditions and volatility_ok and trend_strong and 
                cloud_thick_enough and drawdown_ok)

    def _long_exit_cond(self, r, entry_price=None):
        if pd.isna(r.tenkan) or pd.isna(r.kijun):
            return False
        
        # Original exit condition
        tenkan_kijun_cross = r.tenkan < r.kijun
        
        # Additional exit conditions:
        
        # 1. Price falls below cloud
        below_cloud = r.close < min(r.ssa, r.ssb)
        
        # 2. ATR-based stop loss
        atr_stop = False
        if entry_price is not None and pd.notna(r.ATR):
            atr_stop = r.close <= entry_price - (STOP_ATR_MULT * r.ATR)
        
        # 3. Volatility spike (risk management)
        volatility_spike = r.volatility_regime > 0.95  # Top 5% volatility
        
        return tenkan_kijun_cross or below_cloud or atr_stop or volatility_spike

    # Interface implementations
    def entry_signal(self, idx, df):
        return self._long_entry_cond(df.loc[idx])

    def exit_signal(self, idx, df, entry_price):
        return self._long_exit_cond(df.loc[idx], entry_price)
