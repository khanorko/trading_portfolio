"""
Simple portfolio back‑test engine that mixes any list of Strategy objects.
Assumes long‑only strategies for now.
Enhanced with realistic trading costs, slippage, and state persistence.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

# Import the execute_trade function
# Assuming exchange_handler.py is in the same parent directory or PYTHONPATH
try:
    from exchange_handler import execute_trade
except ImportError:
    # Define a dummy function if exchange_handler is not available
    def execute_trade(*args, **kwargs):
        print("WARN: exchange_handler.execute_trade not found, paper trading disabled.")
        return None

# Import state manager
try:
    from engines.state_manager import StateManager
except ImportError:
    print("WARN: StateManager not found, state persistence disabled.")
    StateManager = None

def run(
    df: pd.DataFrame, 
    strategies: List, 
    initial_capital: float = 10_000,
    # --- New parameters for paper trading ---
    enable_paper_trading: bool = False,
    exchange_obj: Optional[Any] = None, # Accept CCXT exchange object
    exchange_symbol: str = "BTC/USDT",
    # --- New parameters for realistic trading costs ---
    trading_fee_rate: float = 0.001,  # 0.1% per trade
    slippage_rate: float = 0.0005,    # 0.05% slippage
    min_profit_threshold: float = 0.015,  # 1.5% minimum profit
    enable_realistic_costs: bool = True,
    # --- New parameters for state persistence ---
    enable_state_persistence: bool = True,
    resume_from_state: bool = True
) -> pd.DataFrame:
    """
    Enhanced backtest with realistic trading costs, slippage, and state persistence.
    
    Args:
        enable_state_persistence: Save state periodically for crash recovery
        resume_from_state: Try to resume from saved state on startup
    """
    
    # Initialize state manager
    state_manager = None
    if enable_state_persistence and StateManager:
        state_manager = StateManager()
        print("🔄 State persistence enabled")
    
    # Try to load previous state
    loaded_state = None
    if resume_from_state and state_manager:
        loaded_state = state_manager.load_state()
    
    # Initialize or restore state
    if loaded_state:
        print("🔄 Resuming from previous state...")
        cash = loaded_state.get('cash_balances', {})
        positions = loaded_state.get('positions', {})
        total_trades = loaded_state.get('total_trades', 0)
        total_fees_paid = loaded_state.get('total_fees_paid', 0.0)
        last_processed = loaded_state.get('last_processed_timestamp', '')
        
        # Convert last_processed to pandas timestamp for comparison
        if last_processed:
            try:
                last_processed_ts = pd.to_datetime(last_processed)
                # Filter dataframe to only process new data
                df = df[df.index > last_processed_ts]
                print(f"📅 Resuming from {last_processed}, processing {len(df)} new rows")
            except:
                print("⚠️ Could not parse last processed timestamp, processing all data")
        
        # Restore cash for each strategy
        for i, s in enumerate(strategies):
            strategy_key = f"strategy_{i}_{s.__class__.__name__}"
            if strategy_key in cash:
                print(f"💰 Restored {strategy_key}: ${cash[strategy_key]:,.2f}")
            else:
                cash[strategy_key] = initial_capital / len(strategies)
    else:
        print("🆕 Starting fresh simulation...")
        # Initialize fresh state
        cash = {}
        positions = {}
        total_trades = 0
        total_fees_paid = 0.0
        
        # Allocate initial capital equally among strategies
        for i, s in enumerate(strategies):
            strategy_key = f"strategy_{i}_{s.__class__.__name__}"
            cash[strategy_key] = initial_capital / len(strategies)
            positions[strategy_key] = {}

    # Precompute indicators for all strategies
    for s in strategies:
        s.precompute_indicators(df)
    
    # Create equity tracking
    equity_columns = ['Total'] + [f"strategy_{i}_{s.__class__.__name__}" for i, s in enumerate(strategies)]
    equity = pd.DataFrame(index=df.index, columns=equity_columns)
    
    # Track state save frequency (save every 100 rows or 1 hour of data)
    save_frequency = min(100, len(df) // 10)  # Save at least 10 times during run
    rows_processed = 0
    
    print(f"💼 Starting simulation with {len(strategies)} strategies")
    print(f"💰 Initial capital per strategy: ${initial_capital/len(strategies):,.2f}")
    if enable_realistic_costs:
        print(f"💸 Trading costs: {trading_fee_rate*100:.2f}% fee + {slippage_rate*100:.3f}% slippage")
        print(f"🎯 Min profit threshold: {min_profit_threshold*100:.1f}%")
    
    for idx, row in df.iterrows():
        rows_processed += 1
        
        for i, s in enumerate(strategies):
            strategy_key = f"strategy_{i}_{s.__class__.__name__}"
            s.slice = strategy_key  # Set slice for strategy identification
            
            # Get current position for this strategy
            current_position = positions[strategy_key]
            
            # Calculate current equity (cash + position value)
            position_value = 0
            if current_position:
                position_value = current_position.get('quantity', 0) * row.close
            
            current_equity = cash[strategy_key] + position_value
            equity.loc[idx, strategy_key] = current_equity
            
            # Check for signals
            signal = s.generate_signal(row, idx)
            
            if signal == "BUY" and not current_position:
                # Calculate position size with enhanced risk management
                if pd.notna(row.ATR) and row.ATR > 0:
                    risk = row.ATR
                    # Calculate desired units based on strategy's simulated cash
                    units = (cash[strategy_key] * 0.015) / risk  # Increased from 0.0025 to 0.015 (1.5% risk per trade)
                    
                    # Apply realistic costs
                    entry_price = row.close
                    if enable_realistic_costs:
                        # Add slippage for market orders
                        entry_price = row.close * (1 + slippage_rate)
                    
                    trade_value = units * entry_price
                    
                    # Calculate fees
                    fees = 0
                    if enable_realistic_costs:
                        fees = trade_value * trading_fee_rate
                    
                    # Check if we have enough cash
                    total_cost = trade_value + fees
                    if cash[strategy_key] >= total_cost:
                        # Execute the trade
                        cash[strategy_key] -= total_cost
                        total_fees_paid += fees
                        total_trades += 1
                        
                        # Store position
                        positions[strategy_key] = {
                            'quantity': units,
                            'entry_price': entry_price,
                            'entry_date': idx,
                            'fees_paid': fees
                        }
                        
                        print(f"🟢 {strategy_key} BUY at {idx}: Price: ${entry_price:.2f}, Qty: {units:.6f}, Cost: ${total_cost:.2f}")
                        
                        # Save trade to history
                        if state_manager:
                            trade_data = {
                                'timestamp': idx.isoformat(),
                                'strategy': strategy_key,
                                'action': 'BUY',
                                'price': entry_price,
                                'quantity': units,
                                'value': trade_value,
                                'fees': fees,
                                'cash_after': cash[strategy_key]
                            }
                            state_manager.save_trade(trade_data)
                        
                        # Execute on exchange if enabled
                        if enable_paper_trading and exchange_obj:
                            try:
                                execute_trade(
                                    exchange_obj, 
                                    exchange_symbol, 
                                    "buy", 
                                    units, 
                                    entry_price
                                )
                            except Exception as e:
                                print(f"⚠️ Paper trading failed: {e}")
            
            elif signal == "SELL" and current_position:
                # Calculate exit with realistic costs
                exit_price = row.close
                if enable_realistic_costs:
                    # Subtract slippage for market orders
                    exit_price = row.close * (1 - slippage_rate)
                
                quantity = current_position['quantity']
                trade_value = quantity * exit_price
                
                # Calculate fees
                fees = 0
                if enable_realistic_costs:
                    fees = trade_value * trading_fee_rate
                
                # Calculate profit/loss
                entry_cost = quantity * current_position['entry_price']
                total_fees_for_position = current_position['fees_paid'] + fees
                net_profit = trade_value - entry_cost - total_fees_for_position
                profit_pct = net_profit / entry_cost
                
                # Apply minimum profit threshold
                should_sell = True
                if enable_realistic_costs and profit_pct < min_profit_threshold:
                    # Only sell if profit exceeds threshold or it's a stop loss
                    if profit_pct > -0.05:  # Don't sell unless 5% loss (stop loss)
                        should_sell = False
                
                if should_sell:
                    # Execute the sale
                    cash[strategy_key] += trade_value - fees
                    total_fees_paid += fees
                    total_trades += 1
                    
                    print(f"🔴 {strategy_key} SELL at {idx}: Price: ${exit_price:.2f}, Qty: {quantity:.6f}, Profit: ${net_profit:.2f} ({profit_pct*100:.2f}%)")
                    
                    # Save trade to history
                    if state_manager:
                        trade_data = {
                            'timestamp': idx.isoformat(),
                            'strategy': strategy_key,
                            'action': 'SELL',
                            'price': exit_price,
                            'quantity': quantity,
                            'value': trade_value,
                            'fees': fees,
                            'profit': net_profit,
                            'profit_pct': profit_pct,
                            'cash_after': cash[strategy_key]
                        }
                        state_manager.save_trade(trade_data)
                    
                    # Clear position
                    positions[strategy_key] = {}
                    
                    # Execute on exchange if enabled
                    if enable_paper_trading and exchange_obj:
                        try:
                            execute_trade(
                                exchange_obj, 
                                exchange_symbol, 
                                "sell", 
                                quantity, 
                                exit_price
                            )
                        except Exception as e:
                            print(f"⚠️ Paper trading failed: {e}")
        
        # Calculate total equity
        equity.loc[idx, 'Total'] = sum(equity.loc[idx, col] for col in equity_columns[1:])
        
        # Periodic state saving
        if state_manager and rows_processed % save_frequency == 0:
            state_manager.save_state(
                cash_balances=cash,
                positions=positions,
                last_processed_timestamp=idx.isoformat(),
                total_trades=total_trades,
                total_fees_paid=total_fees_paid,
                metadata={
                    'rows_processed': rows_processed,
                    'total_rows': len(df),
                    'progress_pct': (rows_processed / len(df)) * 100
                }
            )
    
    # Final state save
    if state_manager:
        state_manager.save_state(
            cash_balances=cash,
            positions=positions,
            last_processed_timestamp=df.index[-1].isoformat(),
            total_trades=total_trades,
            total_fees_paid=total_fees_paid,
            metadata={
                'simulation_complete': True,
                'final_equity': equity.iloc[-1]['Total']
            }
        )
    
    # Print enhanced summary
    print("\n" + "="*60)
    print("📊 ENHANCED BACKTEST RESULTS")
    print("="*60)
    
    for i, s in enumerate(strategies):
        strategy_key = f"strategy_{i}_{s.__class__.__name__}"
        initial = initial_capital / len(strategies)
        final = equity.iloc[-1][strategy_key]
        returns = (final - initial) / initial * 100
        
        print(f"\n🎯 {s.__class__.__name__}:")
        print(f"   Initial: ${initial:,.2f}")
        print(f"   Final:   ${final:,.2f}")
        print(f"   Return:  {returns:.2f}%")
    
    total_initial = initial_capital
    total_final = equity.iloc[-1]['Total']
    total_returns = (total_final - total_initial) / total_initial * 100
    
    print(f"\n💰 TOTAL PORTFOLIO:")
    print(f"   Initial Capital: ${total_initial:,.2f}")
    print(f"   Final Equity:    ${total_final:,.2f}")
    print(f"   Total Return:    {total_returns:.2f}%")
    print(f"   Total Trades:    {total_trades}")
    print(f"   Total Fees:      ${total_fees_paid:.2f}")
    print(f"   Net Profit:      ${total_final - total_initial:.2f}")
    
    # Calculate annualized return
    days = (df.index[-1] - df.index[0]).days
    years = days / 365.25
    if years > 0:
        annualized_return = ((total_final / total_initial) ** (1/years) - 1) * 100
        print(f"   Annualized:      {annualized_return:.2f}%")
        print(f"   Period:          {days} days ({years:.2f} years)")
    
    print("="*60)
    
    return equity
