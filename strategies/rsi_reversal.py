from __future__ import annotations
import pandas as pd
import numpy as np
from .base import Strategy

class RsiReversal(Strategy):
    """
    Enhanced RSI reversal strategy with stricter entry criteria.
    - Buy when RSI < 35 (oversold) AND price is above 20-period MA (trend filter)
    - Sell when RSI > 70 (overbought) OR 3% profit target OR 2% stop loss
    """
    
    def __init__(self):
        super().__init__()
        self.rsi_period = 14
        self.oversold_threshold = 35  # More conservative than 30
        self.overbought_threshold = 70
        self.ma_period = 20  # Trend filter
        self.profit_target = 0.03  # 3% profit target
        self.stop_loss = 0.02  # 2% stop loss
        self.current_position = None  # Track current position for signal generation

    def precompute_indicators(self, df: pd.DataFrame) -> None:
        """Compute RSI, ATR, and moving average indicators."""
        # RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # ATR for position sizing
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = np.abs(df['high'] - df['close'].shift())
        df['low_close'] = np.abs(df['low'] - df['close'].shift())
        df['true_range'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        df['ATR'] = df['true_range'].rolling(window=14).mean()
        
        # Moving average for trend filter
        df['MA20'] = df['close'].rolling(window=self.ma_period).mean()
        
        # Clean up temporary columns
        df.drop(['high_low', 'high_close', 'low_close', 'true_range'], axis=1, inplace=True)

    def generate_signal(self, row: pd.Series, idx: pd.Timestamp) -> str:
        """
        Generate BUY/SELL/HOLD signals based on RSI and trend conditions.
        """
        # Check if we have valid data
        if pd.isna(row.RSI) or pd.isna(row.MA20):
            return "HOLD"
        
        # BUY signal: RSI oversold AND price above MA (trend filter)
        if (row.RSI < self.oversold_threshold and 
            row.close > row.MA20):
            return "BUY"
        
        # SELL signal: RSI overbought
        elif row.RSI > self.overbought_threshold:
            return "SELL"
        
        return "HOLD"

    # Keep old methods for backward compatibility
    def entry_signal(self, idx: pd.Timestamp, df: pd.DataFrame) -> bool:
        """Legacy method - use generate_signal instead."""
        row = df.loc[idx]
        return self.generate_signal(row, idx) == "BUY"

    def exit_signal(self, idx: pd.Timestamp, df: pd.DataFrame, entry_price: float) -> bool:
        """Legacy method - use generate_signal instead."""
        row = df.loc[idx]
        signal = self.generate_signal(row, idx)
        
        # Also check profit target and stop loss
        if entry_price > 0:
            current_price = row.close
            profit_pct = (current_price - entry_price) / entry_price
            
            if profit_pct >= self.profit_target or profit_pct <= -self.stop_loss:
                return True
        
        return signal == "SELL"
