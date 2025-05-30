#!/usr/bin/env python3
"""
Populate Dashboard with Real Trading Data
This script loads your actual backtest results and creates sample data for the dashboard.
"""

import pandas as pd
import sqlite3
import json
from datetime import datetime, timedelta
import numpy as np
from dashboard_integration import DashboardIntegration

def load_real_backtest_data():
    """Load real backtest data from CSV files"""
    try:
        # Load equity curve data
        equity_df = pd.read_csv('equity_curve.csv')
        equity_df['timestamp'] = pd.to_datetime(equity_df['datetime'])
        equity_df['total_equity'] = equity_df['TOTAL']
        equity_df['unrealized_pnl'] = 0  # Not available in this format
        equity_df['realized_pnl'] = equity_df['TOTAL'] - 4000  # Calculate from initial balance
        
        # Load trade history if it exists
        try:
            trades_df = pd.read_csv('trade_history.csv')
            trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
            if 'exit_time' in trades_df.columns:
                trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
        except FileNotFoundError:
            print("No trade_history.csv found, creating sample trades...")
            trades_df = create_sample_trades()
        
        return equity_df, trades_df
    except FileNotFoundError:
        print("No equity_curve.csv found, creating sample data...")
        return create_sample_data()

def create_sample_trades():
    """Create sample trade data based on the backtest period"""
    trades = []
    start_date = datetime(2021, 1, 1)
    
    # Sample trades for demonstration
    sample_trades = [
        {'strategy': 'Ichimoku', 'side': 'long', 'pnl': 150.25, 'days': 5},
        {'strategy': 'RSI_Reversal', 'side': 'short', 'pnl': -45.80, 'days': 2},
        {'strategy': 'Ichimoku', 'side': 'long', 'pnl': 320.15, 'days': 8},
        {'strategy': 'RSI_Reversal', 'side': 'long', 'pnl': 89.50, 'days': 3},
        {'strategy': 'Ichimoku', 'side': 'long', 'pnl': -120.30, 'days': 4},
        {'strategy': 'RSI_Reversal', 'side': 'short', 'pnl': 200.75, 'days': 6},
    ]
    
    current_date = start_date
    for i, trade in enumerate(sample_trades * 10):  # Repeat to get more trades
        entry_time = current_date + timedelta(days=i*7)
        exit_time = entry_time + timedelta(days=trade['days'])
        
        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'strategy': trade['strategy'],
            'side': trade['side'],
            'entry_price': 45000 + np.random.normal(0, 5000),
            'exit_price': 45000 + np.random.normal(0, 5000),
            'quantity': 0.1,
            'pnl': trade['pnl'] + np.random.normal(0, 50),
            'pnl_percent': (trade['pnl'] / 4000) * 100,
            'fees': 8.50,
            'status': 'closed'
        })
    
    return pd.DataFrame(trades)

def create_sample_data():
    """Create sample equity curve and trades if no real data exists"""
    # Create sample equity curve
    dates = pd.date_range(start='2021-01-01', end='2023-12-31', freq='4H')
    initial_balance = 4000
    
    # Simulate equity curve with some volatility
    returns = np.random.normal(0.0002, 0.02, len(dates))  # Small positive drift
    cumulative_returns = np.cumprod(1 + returns)
    equity_values = initial_balance * cumulative_returns
    
    equity_df = pd.DataFrame({
        'timestamp': dates,
        'total_equity': equity_values,
        'unrealized_pnl': np.random.normal(0, 50, len(dates)),
        'realized_pnl': np.cumsum(np.random.normal(5, 100, len(dates)))
    })
    
    trades_df = create_sample_trades()
    
    return equity_df, trades_df

def populate_dashboard():
    """Main function to populate the dashboard with data"""
    print("🚀 Populating Trading Dashboard...")
    
    # Load data
    equity_df, trades_df = load_real_backtest_data()
    
    print(f"📊 Loaded {len(equity_df)} equity points and {len(trades_df)} trades")
    
    # Initialize dashboard integration
    integrator = DashboardIntegration()
    
    # Create database and populate with data
    print("💾 Inserting data into database...")
    
    # Insert equity data directly into database
    conn = sqlite3.connect(integrator.dashboard_state.db_path)
    cursor = conn.cursor()
    
    for _, row in equity_df.iterrows():
        cursor.execute('''
            INSERT INTO equity_snapshots 
            (timestamp, total_equity, ichimoku_equity, reversal_equity, open_positions, unrealized_pnl, daily_pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['timestamp'].isoformat(),
            row['total_equity'],
            0,  # ichimoku_equity - not separated in our data
            0,  # reversal_equity - not separated in our data
            0,  # open_positions
            row['unrealized_pnl'],
            row['realized_pnl']
        ))
    
    # Insert trade data
    for _, trade in trades_df.iterrows():
        trade_data = {
            'timestamp': trade['entry_time'].isoformat(),
            'symbol': 'BTC/USDT',
            'strategy': trade['strategy'],
            'action': 'BUY' if trade['side'] == 'long' else 'SELL',
            'quantity': trade['quantity'],
            'price': trade['entry_price'],
            'pnl': trade['pnl'],
            'fee': trade.get('fees', 0),
            'paper_traded': False,  # Backtest data
            'entry_price': trade['entry_price'],
            'exit_price': trade.get('exit_price', trade['entry_price'])
        }
        
        integrator.dashboard_state.log_trade(trade_data)
    
    conn.commit()
    conn.close()
    
    # Add some performance metrics
    total_pnl = trades_df['pnl'].sum()
    win_rate = (trades_df['pnl'] > 0).mean() * 100
    total_trades = len(trades_df)
    
    print(f"✅ Dashboard populated successfully!")
    print(f"📈 Total PnL: ${total_pnl:.2f}")
    print(f"🎯 Win Rate: {win_rate:.1f}%")
    print(f"📊 Total Trades: {total_trades}")
    print(f"💰 Final Equity: ${equity_df['total_equity'].iloc[-1]:.2f}")
    
    # Create a summary file
    summary = {
        'last_updated': datetime.now().isoformat(),
        'total_trades': int(total_trades),
        'total_pnl': float(total_pnl),
        'win_rate': float(win_rate),
        'final_equity': float(equity_df['total_equity'].iloc[-1]),
        'initial_equity': float(equity_df['total_equity'].iloc[0]),
        'period': f"{equity_df['timestamp'].min().date()} to {equity_df['timestamp'].max().date()}"
    }
    
    with open('dashboard_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📋 Summary saved to dashboard_summary.json")
    print(f"🌐 Your dashboard should now show data at: http://localhost:8501")

if __name__ == "__main__":
    populate_dashboard() 