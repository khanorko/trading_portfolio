"""
Simple portfolio back‑test engine that mixes any list of Strategy objects.
Assumes long‑only strategies for now.
"""
from __future__ import annotations
from typing import List, Dict, Any
import pandas as pd
import numpy as np

def run(df: pd.DataFrame, strategies: List, initial_capital: float = 100_000):
    # precompute indicators
    for s in strategies:
        s.precompute_indicators(df)

    cash   : Dict[str, float] = {s.slice: initial_capital*s.allocation for s in strategies}
    qty    : Dict[str, float] = {s.slice: 0.0 for s in strategies}
    entry  : Dict[str, float] = {s.slice: np.nan for s in strategies}
    # Store trade details
    trades_log: List[Dict[str, Any]] = []


    equity = pd.DataFrame(index=df.index, columns=[s.slice for s in strategies] + ["TOTAL"], dtype=float)

    for ts, row in df.iterrows():
        price = row.close

        for s in strategies:
            # open?
            if qty[s.slice]==0 and s.entry_signal(ts, df):
                # Ensure ATR is not NaN and is positive before calculating units
                if pd.notna(row.ATR) and row.ATR > 0:
                    risk = row.ATR
                    units = (cash[s.slice]*0.02)/risk
                    if units * price > cash[s.slice]: # Cannot afford
                        units = cash[s.slice] / price
                    
                    if units > 0:
                        qty[s.slice] = units
                        cash[s.slice]-=units*price
                        entry[s.slice]=price
                        trades_log.append({
                            "timestamp": ts, "strategy": s.slice, "action": "BUY",
                            "price": price, "quantity": units, "pnl": 0
                        })
            # close?
            elif qty[s.slice]>0 and s.exit_signal(ts, df, entry[s.slice]):
                pnl = (price - entry[s.slice]) * qty[s.slice]
                cash[s.slice]+=qty[s.slice]*price
                trades_log.append({
                    "timestamp": ts, "strategy": s.slice, "action": "SELL",
                    "price": price, "quantity": qty[s.slice], "pnl": pnl
                })
                qty[s.slice]=0
                entry[s.slice]=np.nan


        # mark to market
        for s in strategies:
            equity.at[ts, s.slice] = cash[s.slice] + qty[s.slice]*price
        current_total_equity = equity.loc[ts, [s.slice for s in strategies]].sum()
        # Check if current_total_equity is NaN (can happen at the beginning if no trades made yet)
        if pd.isna(current_total_equity) and ts == df.index[0]:
            equity.at[ts, "TOTAL"] = initial_capital
        else:
            equity.at[ts, "TOTAL"] = current_total_equity

    print("\n--- Trade Log ---")
    if not trades_log:
        print("No trades were made.")
    else:
        for trade in trades_log:
            print(f"{trade['timestamp']} - {trade['strategy']:<10} - {trade['action']:<4} - Price: {trade['price']:.2f}, Qty: {trade['quantity']:.4f}, P&L: {trade['pnl']:.2f}")

    print("\n--- Summary ---   ")
    print(f"Initial Capital: {initial_capital:.2f}")
    
    final_total_equity = equity["TOTAL"].iloc[-1]
    if pd.isna(final_total_equity): # If no trades or activity, final equity is initial capital
        final_total_equity = initial_capital
        
    print(f"Final Total Equity: {final_total_equity:.2f}")
    print(f"Total P&L: {(final_total_equity - initial_capital):.2f}")
    
    print("\n--- Strategy Breakdown ---")
    total_trades_count = 0
    for s in strategies:
        strategy_trades = [t for t in trades_log if t["strategy"] == s.slice]
        strategy_pnl = sum(t["pnl"] for t in strategy_trades if t["action"] == "SELL")
        num_strategy_trades = len([t for t in strategy_trades if t["action"] == "BUY"]) # count entries
        total_trades_count += num_strategy_trades
        
        initial_strategy_capital = initial_capital * s.allocation
        final_strategy_equity = equity[s.slice].iloc[-1]
        if pd.isna(final_strategy_equity): # If no trades for this strategy
            final_strategy_equity = initial_strategy_capital

        print(f"Strategy: {s.slice}")
        print(f"  Initial Allocation: {initial_strategy_capital:.2f}")
        print(f"  Final Equity: {final_strategy_equity:.2f}")
        print(f"  P&L: {strategy_pnl:.2f}")
        print(f"  Number of Trades: {num_strategy_trades}")
        
    print(f"\nTotal Number of Trades (entries): {total_trades_count}")

    return equity
