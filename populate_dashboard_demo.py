#!/usr/bin/env python3
"""
Demo Data Population Script
Populates the dashboard with sample trading data for demonstration
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from enhanced_state_manager import DashboardStateManager

def populate_demo_trades():
    """Populate dashboard with demo trading data"""
    print("🎯 Populating dashboard with demo trading data...")
    
    dashboard = DashboardStateManager()
    
    # Generate demo trades over the last 7 days
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    # Create realistic trade scenarios
    trades = []
    current_time = start_time
    equity = 4000.0
    trade_id = 1
    
    strategies = ["IchimokuTrend", "RsiReversal"]
    base_price = 95000.0
    
    while current_time < end_time:
        # Generate 1-3 trades per day on average
        if random.random() < 0.3:  # 30% chance of trade each 4-hour period
            strategy = random.choice(strategies)
            
            # Generate entry trade
            entry_price = base_price + random.uniform(-2000, 2000)
            quantity = random.uniform(0.01, 0.05)  # 0.01 to 0.05 BTC
            
            entry_trade = {
                'symbol': 'BTC/USDT',
                'strategy': strategy,
                'side': 'buy',
                'quantity': quantity,
                'price': entry_price,
                'timestamp': current_time.isoformat(),
                'position_id': f'demo_pos_{trade_id}'
            }
            
            # Log entry trade
            dashboard.log_trade(entry_trade)
            trades.append(entry_trade)
            
            # Generate exit trade 4-24 hours later
            exit_time = current_time + timedelta(hours=random.uniform(4, 24))
            if exit_time < end_time:
                # Generate realistic P&L
                price_change_pct = random.uniform(-0.05, 0.08)  # -5% to +8%
                exit_price = entry_price * (1 + price_change_pct)
                pnl = (exit_price - entry_price) * quantity
                
                exit_trade = {
                    'symbol': 'BTC/USDT',
                    'strategy': strategy,
                    'side': 'sell',
                    'quantity': quantity,
                    'price': exit_price,
                    'timestamp': exit_time.isoformat(),
                    'position_id': f'demo_pos_{trade_id}',
                    'pnl': pnl
                }
                
                # Log exit trade
                dashboard.log_trade(exit_trade)
                trades.append(exit_trade)
                
                # Update equity
                equity += pnl
                
                print(f"  Trade {trade_id}: {strategy} - P&L: ${pnl:.2f}")
                trade_id += 1
        
        current_time += timedelta(hours=4)
    
    # Generate equity snapshots
    print("📊 Generating equity snapshots...")
    snapshot_time = start_time
    current_equity = 4000.0
    
    while snapshot_time < end_time:
        # Add some random equity fluctuation
        daily_change = random.uniform(-0.02, 0.03)  # -2% to +3% daily
        current_equity *= (1 + daily_change/6)  # 4-hour change
        
        # Create equity snapshot
        equity_data = {
            'timestamp': snapshot_time.isoformat(),
            'total_equity': current_equity,
            'ichimoku_equity': current_equity * 0.9,  # 90% allocation
            'reversal_equity': current_equity * 0.1,  # 10% allocation
            'open_positions': random.randint(0, 2),
            'unrealized_pnl': random.uniform(-100, 200),
            'daily_pnl': random.uniform(-50, 100)
        }
        
        dashboard.log_equity_snapshot_direct(equity_data)
        snapshot_time += timedelta(hours=4)
    
    print(f"✅ Generated {len(trades)} demo trades")
    print(f"📈 Final equity: ${current_equity:.2f}")
    print("🎯 Demo data population complete!")

def clear_demo_data():
    """Clear existing demo data"""
    print("🧹 Clearing existing demo data...")
    
    db_path = "trading_dashboard.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear trades and equity snapshots from last 7 days
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    
    cursor.execute("DELETE FROM trades WHERE timestamp > ?", (week_ago,))
    cursor.execute("DELETE FROM equity_snapshots WHERE timestamp > ?", (week_ago,))
    
    conn.commit()
    conn.close()
    
    print("✅ Demo data cleared")

if __name__ == "__main__":
    print("🎛️ Trading Dashboard Demo Data Generator")
    print("=" * 50)
    
    choice = input("Choose option:\n1. Generate demo data\n2. Clear demo data\n3. Regenerate (clear + generate)\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        populate_demo_trades()
    elif choice == "2":
        clear_demo_data()
    elif choice == "3":
        clear_demo_data()
        populate_demo_trades()
    else:
        print("Invalid choice. Exiting.")
    
    print("\n🚀 Next step: Run 'streamlit run trading_dashboard.py' to view the dashboard!") 