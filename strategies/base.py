
"""
Base classes and shared helpers for strategy modules.
"""

from abc import ABC, abstractmethod
import pandas as pd

class Strategy(ABC):
    """
    Abstract base class every strategy must inherit from.
    Each strategy works on its own capital slice.
    """
    def __init__(self, slice_name: str, allocation: float):
        self.slice = slice_name
        self.allocation = allocation    # 0–1 fraction of total equity

    # ------------------------------------------------------------------
    # lifecycle hooks
    # ------------------------------------------------------------------
    def precompute_indicators(self, df: pd.DataFrame) -> None:
        """Add any indicator columns to df *in‑place* before run."""
        pass

    @abstractmethod
    def entry_signal(self, idx: pd.Timestamp, df: pd.DataFrame) -> bool:
        """Return True when we want to enter long. Override in subclass."""
        ...

    @abstractmethod
    def exit_signal(self, idx: pd.Timestamp, df: pd.DataFrame, entry_price: float) -> bool:
        """Return True when we want to exit the open position."""
        ...

    # ------------------------------------------------------------------
    # sizing helpers
    # ------------------------------------------------------------------
    def position_size(self, cash_slice: float, risk_per_unit: float, risk_pct: float = 0.02):
        """
        Volatility‑scaled sizing: risk_pct of slice equity divided by risk per unit.
        """
        risk_dollars = cash_slice * risk_pct
        return risk_dollars / risk_per_unit if risk_per_unit > 0 else 0.0
