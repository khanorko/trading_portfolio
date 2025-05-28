"""
Simple portfolio back‑test engine that mixes any list of Strategy objects.
Assumes long‑only strategies for now.
Enhanced with realistic trading costs and slippage.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

# Import the execute_trade function
# Assuming exchange_handler.py is in the same parent directory or PYTHONPATH
try:
    from exchange_handler import execute_trade
except ImportError:
    # Define a dummy function if exchange_handler is not available
    def execute_trade(*args, **kwargs):
        print("WARN: exchange_handler.execute_trade not found, paper trading disabled.")
        return None

def run(
    df: pd.DataFrame, 
    strategies: List, 
    initial_capital: float = 10_000,
    # --- New parameters for paper trading ---
    enable_paper_trading: bool = False,
    exchange_obj: Optional[Any] = None, # Accept CCXT exchange object
    exchange_symbol: Optional[str] = None, # Renamed from binance_symbol
    # --- New parameters for realistic trading costs ---
    trading_fee_rate: float = 0.001,  # 0.1% per trade (Bybit standard)
    slippage_rate: float = 0.0005,    # 0.05% slippage
    min_profit_threshold: float = 0.01,  # Minimum 1% profit to close position
    enable_realistic_costs: bool = True
):
    """
    Enhanced backtest with realistic trading costs.
    
    Args:
        trading_fee_rate: Fee rate per trade (0.001 = 0.1%)
        slippage_rate: Slippage rate per trade (0.0005 = 0.05%)
        min_profit_threshold: Minimum profit % to close position (0.01 = 1%)
        enable_realistic_costs: Whether to apply fees and slippage
    """
    # precompute indicators
    for s in strategies:
        s.precompute_indicators(df)

    cash   : Dict[str, float] = {s.slice: initial_capital*s.allocation for s in strategies}
    qty    : Dict[str, float] = {s.slice: 0.0 for s in strategies}
    entry  : Dict[str, float] = {s.slice: np.nan for s in strategies}
    trades_log: List[Dict[str, Any]] = []
    total_fees_paid: float = 0.0

    equity = pd.DataFrame(index=df.index, columns=[s.slice for s in strategies] + ["TOTAL"], dtype=float)

    print(f"\nStarting Enhanced Backtest Run...")
    print(f"Paper Trading Enabled: {enable_paper_trading}")
    print(f"Realistic Costs Enabled: {enable_realistic_costs}")
    if enable_realistic_costs:
        print(f"Trading Fee Rate: {trading_fee_rate*100:.2f}%")
        print(f"Slippage Rate: {slippage_rate*100:.3f}%")
        print(f"Min Profit Threshold: {min_profit_threshold*100:.1f}%")
    
    if enable_paper_trading and not exchange_obj:
        print("WARN: Paper trading enabled but exchange object is invalid. Disabling paper trading for this run.")
        enable_paper_trading = False
    if enable_paper_trading and not exchange_symbol: # Use exchange_symbol
        print("WARN: Paper trading enabled but Exchange symbol is not set. Disabling paper trading for this run.") # Updated message
        enable_paper_trading = False

    for ts, row in df.iterrows():
        # Check if essential price data is available
        if pd.isna(row.close):
            # print(f"WARN: Skipping timestamp {ts} due to missing close price.")
            # Need to handle equity calculation if we skip
            # For now, just forward fill the equity for skipped rows based on the last valid value
            if ts != df.index[0]:
                equity.loc[ts] = equity.loc[df.index[df.index.get_loc(ts) - 1]]
            else:
                 # Set initial equity if the very first row has NaNs we can't process
                 for s in strategies:
                     equity.at[ts, s.slice] = cash[s.slice]
                 equity.at[ts, "TOTAL"] = initial_capital
            continue # Skip this row for trading logic
            
        price = row.close

        for s in strategies:
            # --- OPEN LOGIC --- 
            if qty[s.slice] == 0 and s.entry_signal(ts, df):
                if pd.notna(row.ATR) and row.ATR > 0:
                    risk = row.ATR
                    # Calculate desired units based on strategy's simulated cash
                    units = (cash[s.slice] * 0.015) / risk  # Increased from 0.0025 to 0.015 (1.5% risk per trade)
                    
                    # Apply slippage to buy price (buy at higher price)
                    if enable_realistic_costs:
                        execution_price = price * (1 + slippage_rate)
                    else:
                        execution_price = price
                    
                    # Check affordability including fees
                    total_cost = units * execution_price
                    if enable_realistic_costs:
                        fee = total_cost * trading_fee_rate
                        total_cost += fee
                    else:
                        fee = 0
                    
                    if total_cost > cash[s.slice]:
                        # Recalculate units to fit available cash
                        if enable_realistic_costs:
                            units = cash[s.slice] / (execution_price * (1 + trading_fee_rate))
                            fee = units * execution_price * trading_fee_rate
                        else:
                            units = cash[s.slice] / execution_price
                            fee = 0
                    
                    # Ensure units > 0 after checks
                    if units > 0:
                        # --- Attempt Paper Trade (BUY) ---
                        paper_trade_success = False
                        if enable_paper_trading:
                            print(f"--> PAPER TRADE: Attempting BUY {units:.4f} {exchange_symbol} for strategy {s.slice} at ~{execution_price:.2f}") # Use exchange_symbol
                            order_receipt = execute_trade(
                                exchange_obj=exchange_obj, 
                                symbol=exchange_symbol, # Use exchange_symbol
                                order_type='market', 
                                side='buy', 
                                amount_base_currency_to_trade=units,
                                current_price=price,
                                sim_timestamp=ts
                            )
                            if order_receipt:
                                # TODO: Potentially adjust 'units' based on actual filled amount from order_receipt if needed
                                print(f"--> PAPER TRADE: BUY Order successful: {order_receipt.get('id')}")
                                paper_trade_success = True 
                            else:
                                print(f"--> PAPER TRADE: BUY Order FAILED for strategy {s.slice}.")
                        # --------------------------------
                        
                        # Update Simulation State (only if paper trade succeeded or paper trading is disabled)
                        # If paper trading fails, maybe we shouldn't update the sim state?
                        # For now, let's update the sim state regardless, to keep the backtest consistent.
                        # A more advanced system could handle this differently (e.g., skip sim update if paper fails).
                        #if paper_trade_success or not enable_paper_trading:
                        qty[s.slice] = units
                        cash[s.slice] -= units * execution_price + fee
                        entry[s.slice] = execution_price
                        total_fees_paid += fee
                        trades_log.append({
                            "timestamp": ts, "strategy": s.slice, "action": "BUY",
                            "price": execution_price, "quantity": units, "pnl": 0, "fee": fee, "paper_traded": paper_trade_success
                        })
                        #else: 
                        #    print(f"--> SIMULATION: Did not update simulation state for {s.slice} BUY due to paper trade failure.")

            # --- CLOSE LOGIC ---            
            elif qty[s.slice] > 0 and s.exit_signal(ts, df, entry[s.slice]):
                sell_units = qty[s.slice] # Simulating closing the full position
                
                # Apply slippage to sell price (sell at lower price)
                if enable_realistic_costs:
                    execution_price = price * (1 - slippage_rate)
                else:
                    execution_price = price
                
                # Calculate profit percentage before fees
                profit_pct = (execution_price - entry[s.slice]) / entry[s.slice]
                
                # Only execute if profit exceeds minimum threshold (when realistic costs enabled)
                if enable_realistic_costs and profit_pct < min_profit_threshold:
                    continue  # Skip this exit signal
                
                # Calculate fees
                gross_proceeds = sell_units * execution_price
                if enable_realistic_costs:
                    fee = gross_proceeds * trading_fee_rate
                else:
                    fee = 0
                
                net_proceeds = gross_proceeds - fee
                pnl = net_proceeds - (sell_units * entry[s.slice])
                
                # --- Attempt Paper Trade (SELL) ---
                paper_trade_success = False
                if enable_paper_trading:
                    print(f"--> PAPER TRADE: Attempting SELL {sell_units:.4f} {exchange_symbol} for strategy {s.slice} at ~{execution_price:.2f}") # Use exchange_symbol
                    order_receipt = execute_trade(
                        exchange_obj=exchange_obj, 
                        symbol=exchange_symbol, # Use exchange_symbol
                        order_type='market', 
                        side='sell', 
                        amount_base_currency_to_trade=sell_units,
                        current_price=price,
                        sim_timestamp=ts
                    )
                    if order_receipt:
                        print(f"--> PAPER TRADE: SELL Order successful: {order_receipt.get('id')}")
                        paper_trade_success = True
                    else:
                        print(f"--> PAPER TRADE: SELL Order FAILED for strategy {s.slice}.")
                # --------------------------------
                
                # Update Simulation State (similar logic as BUY)
                #if paper_trade_success or not enable_paper_trading:
                cash[s.slice] += net_proceeds
                total_fees_paid += fee
                trades_log.append({
                    "timestamp": ts, "strategy": s.slice, "action": "SELL",
                    "price": execution_price, "quantity": sell_units, "pnl": pnl, "fee": fee, "paper_traded": paper_trade_success
                })
                qty[s.slice] = 0
                entry[s.slice] = np.nan
                #else:
                #    print(f"--> SIMULATION: Did not update simulation state for {s.slice} SELL due to paper trade failure.")

        # --- Mark to Market (Simulation) ---
        for s in strategies:
            equity.at[ts, s.slice] = cash[s.slice] + qty[s.slice]*price
        current_total_equity = equity.loc[ts, [s.slice for s in strategies]].sum()
        if pd.isna(current_total_equity) and ts == df.index[0]:
            equity.at[ts, "TOTAL"] = initial_capital
        elif pd.notna(current_total_equity):
            equity.at[ts, "TOTAL"] = current_total_equity
        else: # If still NaN after first row, forward fill from last known total
            if ts != df.index[0]:
                equity.at[ts, "TOTAL"] = equity.at[df.index[df.index.get_loc(ts) - 1], "TOTAL"]
            else: # Very first row was NaN and remains NaN
                 equity.at[ts, "TOTAL"] = initial_capital

    # --- Enhanced Reporting --- 
    print("\n--- Trade Log (Simulation with Costs) ---")
    if not trades_log:
        print("No simulated trades were made.")
    else:
        for trade in trades_log:
             paper_status = "Paper:Yes" if trade.get("paper_traded") else "Paper:No/Failed"
             fee_info = f", Fee: {trade.get('fee', 0):.2f}" if enable_realistic_costs else ""
             print(f"{trade['timestamp']} - {trade['strategy']:<10} - {trade['action']:<4} - "
                   f"Price: {trade['price']:.2f}, Qty: {trade['quantity']:.4f}, "
                   f"PnL: {trade['pnl']:.2f}{fee_info} - {paper_status}")

    print("\n--- Summary (Simulation with Realistic Costs) ---")
    print(f"Initial Capital: {initial_capital:.2f}")
    
    final_total_equity = equity["TOTAL"].iloc[-1]
    if pd.isna(final_total_equity):
        # If the last equity value is NaN, try finding the last valid one
        last_valid_idx = equity["TOTAL"].last_valid_index()
        if last_valid_idx is not None:
            final_total_equity = equity.loc[last_valid_idx, "TOTAL"]
        else: # If no valid equity value found at all, use initial capital
            final_total_equity = initial_capital
        
    print(f"Final Total Equity: {final_total_equity:.2f}")
    total_pnl = final_total_equity - initial_capital
    print(f"Total P&L: {total_pnl:.2f}")
    if enable_realistic_costs:
        print(f"Total Fees Paid: {total_fees_paid:.2f}")
        print(f"P&L After Fees: {total_pnl:.2f}")
        print(f"Return %: {(total_pnl/initial_capital)*100:.2f}%")
    
    print("\n--- Strategy Breakdown (Simulation) ---")
    total_trades_count = 0
    for s in strategies:
        strategy_trades = [t for t in trades_log if t["strategy"] == s.slice]
        strategy_pnl = sum(t["pnl"] for t in strategy_trades if t["action"] == "SELL")
        strategy_fees = sum(t.get("fee", 0) for t in strategy_trades)
        num_strategy_trades = len([t for t in strategy_trades if t["action"] == "BUY"]) # count entries
        total_trades_count += num_strategy_trades
        
        initial_strategy_capital = initial_capital * s.allocation
        # Find the last valid equity value for the strategy slice
        last_valid_strat_idx = equity[s.slice].last_valid_index()
        if last_valid_strat_idx is not None:
            final_strategy_equity = equity.loc[last_valid_strat_idx, s.slice]
        else:
             final_strategy_equity = initial_strategy_capital # Default if no valid equity found

        print(f"Strategy: {s.slice}")
        print(f"  Initial Allocation: {initial_strategy_capital:.2f}")
        print(f"  Final Equity: {final_strategy_equity:.2f}")
        print(f"  P&L: {strategy_pnl:.2f}")
        if enable_realistic_costs:
            print(f"  Fees Paid: {strategy_fees:.2f}")
            print(f"  Net P&L: {strategy_pnl:.2f}")
        print(f"  Number of Trades: {num_strategy_trades}")
        
    print(f"\nTotal Number of Trades (Simulation Entries): {total_trades_count}")

    return equity
