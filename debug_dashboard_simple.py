#!/usr/bin/env python3
"""
Simple Dashboard Debug Script
Check what data the dashboard is actually loading
"""

import pandas as pd
import sqlite3
from pathlib import Path

def debug_dashboard_data():
    """Debug what data the dashboard is loading"""
    print("🔍 Debugging Dashboard Data Loading...")
    
    db_path = "trading_dashboard.db"
    
    if not Path(db_path).exists():
        print("❌ Database file does not exist!")
        return
    
    print(f"✅ Database file exists: {Path(db_path).stat().st_size / 1024:.1f} KB")
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Test the exact same queries the dashboard uses
        print("\n📊 Testing Dashboard Queries:")
        
        # Trades query
        trades_df = pd.read_sql_query(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 200", 
            conn
        )
        print(f"   - Trades: {len(trades_df)} records")
        
        # Equity query  
        equity_df = pd.read_sql_query(
            "SELECT * FROM equity_snapshots ORDER BY timestamp DESC LIMIT 1000", 
            conn
        )
        print(f"   - Equity: {len(equity_df)} records")
        
        if not equity_df.empty:
            print(f"   - Equity columns: {list(equity_df.columns)}")
            print(f"   - Latest equity: ${equity_df.iloc[0]['total_equity']:.2f}")
            print(f"   - Date range: {equity_df['timestamp'].min()} to {equity_df['timestamp'].max()}")
            
            # Check if the calculate_metrics logic would work
            if len(equity_df) > 1:
                initial_equity = equity_df['total_equity'].iloc[-1]  # Oldest record
                current_equity = equity_df['total_equity'].iloc[0]   # Latest record
                total_return = ((current_equity - initial_equity) / initial_equity * 100) if initial_equity > 0 else 0
                print(f"   - Calculated return: {total_return:.2f}%")
            else:
                print("   - Not enough equity data for return calculation")
        
        # Performance query
        performance_df = pd.read_sql_query(
            "SELECT * FROM performance_metrics ORDER BY timestamp DESC LIMIT 100", 
            conn
        )
        print(f"   - Performance: {len(performance_df)} records")
        
        # Health query
        health_df = pd.read_sql_query(
            "SELECT * FROM system_health ORDER BY timestamp DESC LIMIT 100", 
            conn
        )
        print(f"   - Health: {len(health_df)} records")
        
        conn.close()
        
        # Test the dashboard logic
        print("\n🧮 Testing Dashboard Logic:")
        
        data = {
            'trades': trades_df,
            'equity': equity_df,
            'performance': performance_df,
            'health': health_df
        }
        
        # Test the condition that was causing issues
        if data['equity'].empty:
            print("   - ❌ Equity data is empty - dashboard would show zeros")
        else:
            print("   - ✅ Equity data exists - dashboard should show data")
            
            # Test metrics calculation
            latest_equity = data['equity'].iloc[0] if not data['equity'].empty else {}
            print(f"   - Latest equity value: ${latest_equity.get('total_equity', 0):,.2f}")
            
        if data['trades'].empty and data['equity'].empty:
            print("   - ❌ Both trades and equity empty - would show setup instructions")
        else:
            print("   - ✅ At least one dataset has data - should show dashboard")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_dashboard_data() 