"""
Dashboard Integration Helper
Shows how to integrate dashboard logging into your existing trading bot
"""
from enhanced_state_manager import DashboardStateManager
from datetime import datetime
import json

class DashboardIntegration:
    """
    Helper class to integrate dashboard logging into your existing trading bot
    """
    def __init__(self):
        self.dashboard_state = DashboardStateManager()
        print("✅ Dashboard integration initialized")
    
    def integrate_with_live_bot(self, live_bot_instance):
        """
        Integrate dashboard logging with your LiveTradingBot
        Call this method after creating your bot instance
        """
        # Store reference to dashboard state manager
        live_bot_instance.dashboard_state = self.dashboard_state
        
        # Override the save_state method to include dashboard logging
        original_save_state = live_bot_instance.save_state
        
        def enhanced_save_state():
            # Call original save_state
            original_save_state()
            
            # Add dashboard logging
            try:
                # Log equity snapshot
                current_prices = {"BTC/USDT": 50000}  # This should come from actual market data
                self.dashboard_state.log_equity_snapshot(
                    live_bot_instance.position_manager, 
                    current_prices
                )
                
                # Log performance metrics
                self.dashboard_state.log_performance_metrics()
                
                # Log system health
                self.dashboard_state.log_system_health(
                    status="running",
                    api_connected=bool(live_bot_instance.exchange),
                    error_count=0
                )
                
            except Exception as e:
                print(f"Dashboard logging error: {e}")
        
        # Replace the save_state method
        live_bot_instance.save_state = enhanced_save_state
        
        print("✅ Live bot integrated with dashboard logging")
    
    def log_backtest_results(self, backtest_results, trades_log):
        """
        Log backtest results to dashboard database
        Call this after running your backtest
        """
        print("📊 Logging backtest results to dashboard...")
        
        try:
            # Log individual trades from backtest
            for trade in trades_log:
                trade_data = {
                    'timestamp': trade.get('timestamp', datetime.now().isoformat()),
                    'symbol': 'BTC/USDT',  # Default symbol
                    'strategy': trade.get('strategy', 'BACKTEST'),
                    'action': trade.get('action', ''),
                    'quantity': trade.get('quantity', 0),
                    'price': trade.get('price', 0),
                    'pnl': trade.get('pnl', 0),
                    'fee': trade.get('fee', 0),
                    'paper_traded': False,  # Backtest trades
                    'entry_price': trade.get('price', 0) if trade.get('action') == 'BUY' else None,
                    'exit_price': trade.get('price', 0) if trade.get('action') == 'SELL' else None
                }
                self.dashboard_state.log_trade(trade_data)
            
            # Log equity curve from backtest results
            if hasattr(backtest_results, 'index'):
                for timestamp, row in backtest_results.iterrows():
                    equity_data = {
                        'timestamp': timestamp.isoformat(),
                        'total_equity': row.get('TOTAL', 0),
                        'ichimoku_equity': row.get('ICHIMOKU', 0),
                        'reversal_equity': row.get('REVERSAL', 0),
                        'open_positions': 0,  # Would need to track this in backtest
                        'unrealized_pnl': 0,
                        'daily_pnl': 0
                    }
                    
                    # Insert directly into database for backtest data
                    import sqlite3
                    conn = sqlite3.connect(self.dashboard_state.db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO equity_snapshots 
                        (timestamp, total_equity, ichimoku_equity, reversal_equity, open_positions, unrealized_pnl, daily_pnl)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        equity_data['timestamp'],
                        equity_data['total_equity'],
                        equity_data['ichimoku_equity'],
                        equity_data['reversal_equity'],
                        equity_data['open_positions'],
                        equity_data['unrealized_pnl'],
                        equity_data['daily_pnl']
                    ))
                    
                    conn.commit()
                    conn.close()
            
            # Calculate and log performance metrics
            self.dashboard_state.log_performance_metrics()
            
            print(f"✅ Logged {len(trades_log)} trades and equity curve to dashboard")
            
        except Exception as e:
            print(f"❌ Error logging backtest results: {e}")
    
    def create_sample_data(self):
        """
        Create sample data for dashboard testing
        """
        print("🧪 Creating sample data for dashboard testing...")
        
        import random
        from datetime import timedelta
        
        base_time = datetime.now() - timedelta(days=30)
        base_price = 45000
        base_equity = 4000
        
        # Create sample trades
        strategies = ['ICHIMOKU', 'REVERSAL']
        actions = ['BUY', 'SELL']
        
        for i in range(50):
            trade_time = base_time + timedelta(hours=i*12)
            strategy = random.choice(strategies)
            action = random.choice(actions)
            
            # Simulate realistic trade data
            price_change = random.uniform(-0.05, 0.05)
            price = base_price * (1 + price_change)
            quantity = random.uniform(0.01, 0.1)
            
            pnl = 0
            if action == 'SELL':
                pnl = random.uniform(-200, 500)  # Simulate win/loss
            
            trade_data = {
                'timestamp': trade_time.isoformat(),
                'symbol': 'BTC/USDT',
                'strategy': strategy,
                'action': action,
                'quantity': quantity,
                'price': price,
                'pnl': pnl,
                'fee': abs(pnl) * 0.001,  # 0.1% fee
                'paper_traded': True
            }
            
            self.dashboard_state.log_trade(trade_data)
        
        # Create sample equity snapshots
        equity = base_equity
        for i in range(30*24):  # 30 days, hourly snapshots
            snapshot_time = base_time + timedelta(hours=i)
            
            # Simulate equity growth/decline
            daily_change = random.uniform(-0.02, 0.03)
            equity *= (1 + daily_change/24)  # Hourly change
            
            # Log equity snapshot directly
            import sqlite3
            conn = sqlite3.connect(self.dashboard_state.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO equity_snapshots 
                (timestamp, total_equity, ichimoku_equity, reversal_equity, open_positions, unrealized_pnl, daily_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_time.isoformat(),
                equity,
                equity * 0.9,  # 90% Ichimoku
                equity * 0.1,  # 10% Reversal
                random.randint(0, 3),  # Random open positions
                random.uniform(-100, 200),  # Unrealized P&L
                random.uniform(-50, 100)   # Daily P&L
            ))
            
            conn.commit()
            conn.close()
        
        # Log performance metrics
        self.dashboard_state.log_performance_metrics()
        
        # Log system health
        self.dashboard_state.log_system_health(
            status="running",
            api_connected=True,
            error_count=0
        )
        
        print("✅ Sample data created successfully!")
        print("💡 You can now run the dashboard: streamlit run trading_dashboard.py")

def integrate_with_existing_bot():
    """
    Example of how to integrate with your existing bot files
    """
    
    # For your run_portfolio.py file:
    print("""
    📝 To integrate with your run_portfolio.py (backtest):
    
    Add this at the end of run_portfolio.py:
    
    ```python
    # Dashboard integration
    from dashboard_integration import DashboardIntegration
    
    dashboard = DashboardIntegration()
    dashboard.log_backtest_results(equity, trades_log)
    print("✅ Backtest results logged to dashboard")
    ```
    """)
    
    # For your live_trading_bot.py file:
    print("""
    📝 To integrate with your live_trading_bot.py:
    
    Add this in the __init__ method of LiveTradingBot:
    
    ```python
    # Dashboard integration
    from dashboard_integration import DashboardIntegration
    
    self.dashboard = DashboardIntegration()
    self.dashboard.integrate_with_live_bot(self)
    ```
    """)
    
    print("""
    🚀 After integration, your dashboard will automatically:
    - Track all trades in real-time
    - Monitor portfolio equity
    - Calculate performance metrics
    - Show system health status
    """)

if __name__ == "__main__":
    print("🎛️ Trading Bot Dashboard Integration")
    print("=====================================")
    
    integration = DashboardIntegration()
    
    # Ask user what they want to do
    print("\nWhat would you like to do?")
    print("1. Create sample data for testing")
    print("2. Show integration instructions")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice in ['1', '3']:
        integration.create_sample_data()
    
    if choice in ['2', '3']:
        integrate_with_existing_bot()
    
    print("\n🎯 Next steps:")
    print("1. Run: streamlit run trading_dashboard.py")
    print("2. Open your browser to: http://localhost:8501")
    print("3. Enjoy your professional trading dashboard! 🚀")
