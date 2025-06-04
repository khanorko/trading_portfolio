"""
Enhanced State Manager for Trading Bot Dashboard
Provides SQLite-based logging for portfolio tracking
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from config import Config, DATABASE_PATH, BOT_STATE_FILE
from state_manager import TradingStateManager, PositionManager

class DashboardStateManager(TradingStateManager):
    def __init__(self, state_file=None):
        self.state_file = Path(state_file) if state_file else Path(BOT_STATE_FILE)
        self.db_path = DATABASE_PATH
        
        self.logger = logging.getLogger(__name__)
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table for individual trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                pnl REAL DEFAULT 0,
                fee REAL DEFAULT 0,
                paper_traded BOOLEAN DEFAULT FALSE,
                entry_price REAL,
                exit_price REAL
            )
        ''')
        
        # Equity snapshots for portfolio tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_equity REAL NOT NULL,
                ichimoku_equity REAL DEFAULT 0,
                reversal_equity REAL DEFAULT 0,
                open_positions INTEGER DEFAULT 0,
                unrealized_pnl REAL DEFAULT 0,
                daily_pnl REAL DEFAULT 0
            )
        ''')
        
        # Performance metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                profit_factor REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                sharpe_ratio REAL DEFAULT 0,
                total_return REAL DEFAULT 0
            )
        ''')
        
        # System health
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                last_trade_time TEXT,
                api_connection BOOLEAN DEFAULT TRUE,
                error_count INTEGER DEFAULT 0,
                uptime_minutes INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info("Dashboard database initialized successfully")
    
    def log_trade(self, trade_data):
        """Log individual trade to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades 
                (timestamp, symbol, strategy, action, quantity, price, pnl, fee, paper_traded, entry_price, exit_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('timestamp', datetime.now().isoformat()),
                trade_data.get('symbol', ''),
                trade_data.get('strategy', ''),
                trade_data.get('action', ''),
                trade_data.get('quantity', 0),
                trade_data.get('price', 0),
                trade_data.get('pnl', 0),
                trade_data.get('fee', 0),
                trade_data.get('paper_traded', False),
                trade_data.get('entry_price'),
                trade_data.get('exit_price')
            ))
            
            conn.commit()
            conn.close()
            self.logger.info(f"Trade logged: {trade_data.get('action')} {trade_data.get('symbol')}")
            
        except Exception as e:
            self.logger.error(f"Failed to log trade: {e}")
    
    def log_equity_snapshot(self, position_manager, current_prices=None):
        """Log current equity snapshot"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate equity breakdown
            total_equity = 0
            ichimoku_equity = 0
            reversal_equity = 0
            unrealized_pnl = 0
            
            # Calculate equity from positions and cash
            open_positions = position_manager.get_open_positions()
            open_position_count = len(open_positions)
            
            if current_prices:
                position_manager.update_unrealized_pnl(current_prices)
                for pos_id, pos in open_positions.items():
                    unrealized_pnl += pos.get('unrealized_pnl', 0)
                    if pos.get('strategy') == 'ICHIMOKU':
                        ichimoku_equity += pos.get('quantity', 0) * current_prices.get(pos.get('symbol', ''), 0)
                    elif pos.get('strategy') == 'REVERSAL':
                        reversal_equity += pos.get('quantity', 0) * current_prices.get(pos.get('symbol', ''), 0)
            
            # Get previous day's equity for daily P&L calculation
            cursor.execute('''
                SELECT total_equity FROM equity_snapshots 
                WHERE date(timestamp) = date('now', '-1 day')
                ORDER BY timestamp DESC LIMIT 1
            ''')
            previous_day_result = cursor.fetchone()
            previous_day_equity = previous_day_result[0] if previous_day_result else 0
            
            # For demo purposes, use a base equity (this should come from actual account balance)
            base_equity = 4000  # This should be replaced with actual cash + position value
            total_equity = base_equity + unrealized_pnl
            daily_pnl = total_equity - previous_day_equity if previous_day_equity > 0 else 0
            
            cursor.execute('''
                INSERT INTO equity_snapshots 
                (timestamp, total_equity, ichimoku_equity, reversal_equity, open_positions, unrealized_pnl, daily_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                total_equity,
                ichimoku_equity,
                reversal_equity,
                open_position_count,
                unrealized_pnl,
                daily_pnl
            ))
            
            conn.commit()
            conn.close()
            self.logger.info(f"Equity snapshot logged: ${total_equity:.2f}")
            
        except Exception as e:
            self.logger.error(f"Failed to log equity snapshot: {e}")
    
    def log_performance_metrics(self):
        """Calculate and log performance metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get trade statistics
            cursor.execute('SELECT COUNT(*) FROM trades WHERE action = "SELL"')
            total_trades = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM trades WHERE action = "SELL" AND pnl > 0')
            winning_trades = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM trades WHERE action = "SELL" AND pnl <= 0')
            losing_trades = cursor.fetchone()[0]
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate profit factor
            cursor.execute('SELECT SUM(pnl) FROM trades WHERE action = "SELL" AND pnl > 0')
            gross_profit = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(ABS(pnl)) FROM trades WHERE action = "SELL" AND pnl < 0')
            gross_loss = cursor.fetchone()[0] or 0
            
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
            
            # Calculate max drawdown and total return
            cursor.execute('SELECT total_equity FROM equity_snapshots ORDER BY timestamp')
            equity_data = cursor.fetchall()
            
            max_drawdown = 0
            total_return = 0
            
            if equity_data:
                equity_values = [row[0] for row in equity_data]
                initial_equity = equity_values[0]
                current_equity = equity_values[-1]
                
                total_return = ((current_equity - initial_equity) / initial_equity * 100) if initial_equity > 0 else 0
                
                # Calculate max drawdown
                peak = initial_equity
                for equity in equity_values:
                    if equity > peak:
                        peak = equity
                    drawdown = (peak - equity) / peak
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
                
                max_drawdown *= 100  # Convert to percentage
            
            # Insert performance metrics
            cursor.execute('''
                INSERT INTO performance_metrics 
                (timestamp, total_trades, winning_trades, losing_trades, win_rate, profit_factor, max_drawdown, total_return)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                total_trades,
                winning_trades,
                losing_trades,
                win_rate,
                profit_factor,
                max_drawdown,
                total_return
            ))
            
            conn.commit()
            conn.close()
            self.logger.info("Performance metrics updated")
            
        except Exception as e:
            self.logger.error(f"Failed to log performance metrics: {e}")
    
    def log_system_health(self, status="running", api_connected=True, error_count=0):
        """Log system health status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get last trade time
            cursor.execute('SELECT timestamp FROM trades ORDER BY timestamp DESC LIMIT 1')
            last_trade_result = cursor.fetchone()
            last_trade_time = last_trade_result[0] if last_trade_result else None
            
            cursor.execute('''
                INSERT INTO system_health 
                (timestamp, status, last_trade_time, api_connection, error_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                status,
                last_trade_time,
                api_connected,
                error_count
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log system health: {e}")
    
    def get_dashboard_summary(self):
        """Get summary data for dashboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest metrics
            cursor.execute('''
                SELECT * FROM performance_metrics 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            latest_metrics = cursor.fetchone()
            
            cursor.execute('''
                SELECT * FROM equity_snapshots 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            latest_equity = cursor.fetchone()
            
            cursor.execute('''
                SELECT * FROM system_health 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            latest_health = cursor.fetchone()
            
            conn.close()
            
            return {
                'metrics': latest_metrics,
                'equity': latest_equity,
                'health': latest_health
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get dashboard summary: {e}")
            return None

# Example integration with existing bot
if __name__ == "__main__":
    # Test the enhanced state manager
    dashboard_state = DashboardStateManager()
    
    # Example trade logging
    sample_trade = {
        'timestamp': datetime.now().isoformat(),
        'symbol': 'BTC/USDT',
        'strategy': 'ICHIMOKU',
        'action': 'BUY',
        'quantity': 0.1,
        'price': 45000,
        'paper_traded': True
    }
    
    dashboard_state.log_trade(sample_trade)
    dashboard_state.log_performance_metrics()
    dashboard_state.log_system_health()
    
    print("Dashboard state manager test completed!")
