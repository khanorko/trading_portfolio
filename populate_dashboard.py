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
from pathlib import Path

# Import configuration
from config import Config, DATABASE_PATH, EQUITY_CURVE_CSV, TRADE_HISTORY_CSV, DASHBOARD_SUMMARY
from enhanced_state_manager import DashboardStateManager

def load_real_backtest_data():
    """Load real backtest data from CSV files"""
    try:
        # Load equity curve data
        equity_file = Path(EQUITY_CURVE_CSV)
        if equity_file.exists():
            print(f"📈 Loading equity data from: {EQUITY_CURVE_CSV}")
            equity_df = pd.read_csv(EQUITY_CURVE_CSV)
            equity_df['timestamp'] = pd.to_datetime(equity_df.iloc[:, 0])  # First column as timestamp
            equity_df['total_equity'] = equity_df['TOTAL']
            equity_df['unrealized_pnl'] = 0  # Not available in this format
            equity_df['realized_pnl'] = equity_df['TOTAL'] - 4000  # Calculate from initial balance
            print(f"   ✅ Loaded {len(equity_df)} equity records")
        else:
            print(f"❌ No {EQUITY_CURVE_CSV} found, creating sample equity data...")
            equity_df = create_sample_equity_data()
        
        # Load trade history if it exists
        trades_file = Path(TRADE_HISTORY_CSV)
        if trades_file.exists():
            print(f"📊 Loading trades data from: {TRADE_HISTORY_CSV}")
            trades_df = pd.read_csv(TRADE_HISTORY_CSV)
            trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
            if 'exit_time' in trades_df.columns:
                trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
            print(f"   ✅ Loaded {len(trades_df)} trade records")
        else:
            print(f"❌ No {TRADE_HISTORY_CSV} found, creating sample trades...")
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

def create_sample_equity_data():
    """Create sample equity curve data for testing"""
    print("📊 Creating sample equity data...")
    
    # Generate 30 days of hourly data
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=30),
        end=datetime.now(),
        freq='1H'
    )
    
    # Generate realistic equity curve with some volatility
    np.random.seed(42)
    initial_equity = 4000
    returns = np.random.normal(0.0001, 0.02, len(dates))  # Small positive drift with volatility
    equity_values = [initial_equity]
    
    for i in range(1, len(dates)):
        new_equity = equity_values[-1] * (1 + returns[i])
        equity_values.append(new_equity)
    
    return pd.DataFrame({
        'timestamp': dates,
        'total': equity_values,
        'daily_pnl': np.random.normal(5, 50, len(dates)),
        'unrealized_pnl': np.random.normal(0, 25, len(dates)),
        'open_positions': np.random.randint(0, 5, len(dates))
    })

def populate_dashboard():
    """Main function to populate the dashboard with data"""
    print("🚀 Populating Trading Dashboard Database")
    print("=" * 50)
    
    # Load data
    equity_df, trades_df = load_real_backtest_data()
    
    print(f"📊 Loaded {len(equity_df)} equity points and {len(trades_df)} trades")
    
    # Initialize dashboard integration
    integrator = DashboardIntegration()
    
    print(f"\n🗄️ Initializing database: {DATABASE_PATH}")
    
    # Clear existing data (optional)
    clear_existing = input("🗑️ Clear existing dashboard data? (y/N): ").lower().strip()
    if clear_existing == 'y':
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Clear tables
        cursor.execute("DELETE FROM trades")
        cursor.execute("DELETE FROM equity_snapshots")
        cursor.execute("DELETE FROM performance_metrics")
        cursor.execute("DELETE FROM system_health")
        
        conn.commit()
        conn.close()
        print("   ✅ Existing data cleared")
    
    # Process and insert equity data
    print(f"\n💰 Processing {len(equity_df)} equity snapshots...")
    for idx, row in equity_df.iterrows():
        try:
            # Create equity snapshot data
            equity_data = {
                'timestamp': row['timestamp'] if 'timestamp' in row else row.iloc[0],
                'total_equity': float(row.get('total', row.iloc[1])),
                'daily_pnl': float(row.get('daily_pnl', 0)),
                'unrealized_pnl': float(row.get('unrealized_pnl', 0)),
                'open_positions': int(row.get('open_positions', 0))
            }
            
            integrator.dashboard_state.log_equity_snapshot_direct(equity_data)
        except Exception as e:
            print(f"   ⚠️ Error processing equity row {idx}: {e}")
    
    # Process and insert trade data  
    print(f"\n📈 Processing {len(trades_df)} trades...")
    for idx, row in trades_df.iterrows():
        try:
            # Create trade data
            trade_data = {
                'timestamp': pd.to_datetime(row.get('timestamp', datetime.now())),
                'symbol': row.get('symbol', 'BTC/USDT'),
                'action': row.get('action', 'BUY'),
                'quantity': float(row.get('quantity', 0)),
                'price': float(row.get('price', 0)),
                'pnl': float(row.get('pnl', 0)),
                'strategy': row.get('strategy', 'Unknown'),
                'is_paper_trade': bool(row.get('is_paper_trade', True))
            }
            
            integrator.dashboard_state.log_trade(trade_data)
        except Exception as e:
            print(f"   ⚠️ Error processing trade row {idx}: {e}")
    
    # Log performance metrics
    print(f"\n📊 Calculating performance metrics...")
    integrator.dashboard_state.log_performance_metrics()
    
    # Log system health
    print(f"🏥 Logging system health...")
    integrator.dashboard_state.log_system_health(
        status="healthy",
        cpu_usage=25.5,
        memory_usage=45.2,
        active_connections=1
    )
    
    # Generate summary report
    print(f"\n📋 Generating dashboard summary...")
    summary = integrator.dashboard_state.get_dashboard_summary()
    
    # Save summary to file
    with open(DASHBOARD_SUMMARY, 'w') as f:
        # Convert any datetime objects to strings for JSON serialization
        json_summary = {}
        for key, value in summary.items():
            if isinstance(value, datetime):
                json_summary[key] = value.isoformat()
            else:
                json_summary[key] = value
        json.dump(json_summary, f, indent=2)
    
    print(f"📋 Summary saved to {DASHBOARD_SUMMARY}")
    
    print(f"\n✅ Dashboard population complete!")
    print(f"🚀 Launch dashboard with: streamlit run trading_dashboard.py")

if __name__ == "__main__":
    populate_dashboard() 