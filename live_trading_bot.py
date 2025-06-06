"""
Live Trading Bot with State Persistence
Runs continuously and remembers state when restarted
"""
import time
import logging
import signal
import sys
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, Any

from strategies import IchimokuTrend, RsiReversal
from exchange_handler import initialize_exchange, execute_trade, fetch_historical_ohlcv
from state_manager import TradingStateManager, PositionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LiveTradingBot:
    def __init__(self):
        # Configuration
        self.exchange_name = "bybit"
        self.symbol = "BTC/USDT"
        self.timeframe = "4h"
        self.check_interval = 300  # Check every 5 minutes
        
        # Trading parameters
        self.trading_fee_rate = 0.001
        self.slippage_rate = 0.0005
        self.min_profit_threshold = 0.005
        self.position_size_pct = 0.015  # 1.5% risk per trade
        
        # Initialize components
        self.state_manager = TradingStateManager("live_bot_state.json")
        self.position_manager = PositionManager()
        self.strategies = [IchimokuTrend(), RsiReversal()]
        
        # Exchange connection
        self.exchange = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.running = False
        self.save_state()
        sys.exit(0)
    
    def initialize(self):
        """Initialize exchange and restore state"""
        logger.info("Initializing Live Trading Bot...")
        
        # Initialize exchange
        self.exchange, balance = initialize_exchange(
            exchange_name=self.exchange_name,
            paper_mode=True
        )
        
        if not self.exchange:
            logger.error("Failed to initialize exchange")
            return False
        
        logger.info(f"Exchange initialized. Balance: {balance:.2f} USDT")
        
        # Restore previous state
        self.restore_state()
        
        return True
    
    def restore_state(self):
        """Restore bot state from previous session"""
        logger.info("Restoring previous state...")
        
        saved_state = self.state_manager.load_state()
        if saved_state:
            # Restore positions
            self.position_manager.positions = self.state_manager.get_positions(saved_state)
            logger.info(f"Restored {len(self.position_manager.positions)} positions")
            
            # Log open positions
            open_positions = self.position_manager.get_open_positions()
            for pos_id, pos in open_positions.items():
                logger.info(f"Open position: {pos['symbol']} {pos['strategy']} "
                          f"Qty: {pos['quantity']:.6f} Entry: ${pos['entry_price']:.2f}")
            
            # Restore strategy states
            strategy_states = self.state_manager.get_strategy_states(saved_state)
            for strategy in self.strategies:
                strategy_name = strategy.__class__.__name__
                if strategy_name in strategy_states:
                    # Restore strategy-specific state if needed
                    logger.info(f"Restored state for {strategy_name}")
            
            last_timestamp = self.state_manager.get_last_timestamp(saved_state)
            logger.info(f"Last processed timestamp: {last_timestamp}")
        else:
            logger.info("No previous state found. Starting fresh.")
    
    def save_state(self):
        """Save current bot state"""
        try:
            # Prepare strategy states
            strategy_states = {}
            for strategy in self.strategies:
                strategy_name = strategy.__class__.__name__
                strategy_states[strategy_name] = {
                    "last_update": datetime.now().isoformat()
                    # Add more strategy-specific state as needed
                }
            
            # Save state
            self.state_manager.save_state(
                positions=self.position_manager.positions,
                strategy_states=strategy_states,
                last_processed_timestamp=datetime.now().isoformat(),
                equity_history={},  # Could track equity over time
                trade_history=[]    # Could track recent trades
            )
            logger.info("State saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def fetch_latest_data(self, lookback_hours: int = 200) -> pd.DataFrame:
        """Fetch latest market data"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=lookback_hours)
            
            df = fetch_historical_ohlcv(
                exchange_obj=self.exchange,
                symbol=self.symbol,
                timeframe=self.timeframe,
                start_date_str=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_date_str=end_time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            if df is not None and not df.empty:
                # Precompute indicators
                for strategy in self.strategies:
                    strategy.precompute_indicators(df)
                
                logger.info(f"Fetched {len(df)} candles. Latest price: ${df['close'].iloc[-1]:.2f}")
                return df
            else:
                logger.warning("No data fetched from exchange")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def check_signals_and_trade(self, df: pd.DataFrame):
        """Check for trading signals and execute trades"""
        if df is None or df.empty:
            return
        
        latest_row = df.iloc[-1]
        current_price = latest_row['close']
        current_time = latest_row.name.isoformat()
        
        logger.info(f"Checking signals at {current_time}, Price: ${current_price:.2f}")
        
        # Update unrealized P&L for open positions
        self.position_manager.update_unrealized_pnl({self.symbol: current_price})
        
        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__
            
            try:
                # Check if we already have a position for this strategy
                has_position = self.position_manager.has_position(self.symbol, strategy_name)
                
                if not has_position:
                    # Check for entry signal
                    signal = strategy.generate_signal(latest_row)
                    
                    if signal == 1:  # Buy signal
                        self.execute_entry_trade(strategy_name, current_price, current_time, latest_row)
                
                else:
                    # Check for exit signal
                    open_positions = self.position_manager.get_open_positions(self.symbol, strategy_name)
                    
                    for pos_id, position in open_positions.items():
                        should_exit = self.should_exit_position(position, latest_row, strategy)
                        
                        if should_exit:
                            self.execute_exit_trade(pos_id, position, current_price, current_time)
                            
            except Exception as e:
                logger.error(f"Error processing {strategy_name}: {e}")
    
    def execute_entry_trade(self, strategy_name: str, price: float, timestamp: str, row: pd.Series):
        """Execute entry trade"""
        try:
            # Calculate position size based on ATR risk
            if pd.notna(row.get('ATR')) and row['ATR'] > 0:
                risk = row['ATR']
                # Use a portion of available balance (simplified)
                available_balance = 4000  # This should come from actual balance
                position_value = available_balance * self.position_size_pct
                quantity = position_value / price
                
                logger.info(f"ENTRY SIGNAL: {strategy_name} BUY {quantity:.6f} {self.symbol} at ${price:.2f}")
                
                # Execute trade on exchange
                trade_result = execute_trade(
                    exchange_obj=self.exchange,
                    symbol=self.symbol,
                    side="buy",
                    quantity=quantity,
                    order_type="market"
                )
                
                if trade_result:
                    # Add position to manager
                    pos_id = self.position_manager.add_position(
                        symbol=self.symbol,
                        strategy=strategy_name,
                        quantity=quantity,
                        entry_price=price,
                        entry_time=timestamp
                    )
                    
                    logger.info(f"✅ Position opened: {pos_id}")
                    self.save_state()  # Save state after trade
                else:
                    logger.error("Failed to execute entry trade")
                    
        except Exception as e:
            logger.error(f"Error executing entry trade: {e}")
    
    def execute_exit_trade(self, pos_id: str, position: Dict, price: float, timestamp: str):
        """Execute exit trade"""
        try:
            quantity = position['quantity']
            strategy_name = position['strategy']
            
            logger.info(f"EXIT SIGNAL: {strategy_name} SELL {quantity:.6f} {self.symbol} at ${price:.2f}")
            
            # Execute trade on exchange
            trade_result = execute_trade(
                exchange_obj=self.exchange,
                symbol=self.symbol,
                side="sell",
                quantity=quantity,
                order_type="market"
            )
            
            if trade_result:
                # Close position
                pnl = self.position_manager.close_position(pos_id, price, timestamp)
                
                logger.info(f"✅ Position closed: {pos_id}, P&L: ${pnl:.2f}")
                self.save_state()  # Save state after trade
            else:
                logger.error("Failed to execute exit trade")
                
        except Exception as e:
            logger.error(f"Error executing exit trade: {e}")
    
    def should_exit_position(self, position: Dict, row: pd.Series, strategy) -> bool:
        """Determine if position should be exited"""
        try:
            # Check strategy exit signal
            signal = strategy.generate_signal(row)
            if signal == -1:  # Sell signal
                return True
            
            # Check profit threshold
            current_price = row['close']
            entry_price = position['entry_price']
            profit_pct = (current_price - entry_price) / entry_price
            
            if profit_pct >= self.min_profit_threshold:
                logger.info(f"Profit threshold reached: {profit_pct:.2%}")
                return True
            
            # Add stop loss logic here if needed
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return False
    
    def run(self):
        """Main trading loop"""
        if not self.initialize():
            logger.error("Failed to initialize bot")
            return
        
        logger.info("🚀 Live Trading Bot Started!")
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Timeframe: {self.timeframe}")
        logger.info(f"Check interval: {self.check_interval} seconds")
        
        self.running = True
        
        while self.running:
            try:
                # Fetch latest data
                df = self.fetch_latest_data()
                
                # Check signals and trade
                self.check_signals_and_trade(df)
                
                # Save state periodically
                self.save_state()
                
                # Wait before next check
                logger.info(f"Waiting {self.check_interval} seconds until next check...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
        
        logger.info("Bot stopped")

if __name__ == "__main__":
    bot = LiveTradingBot()
    bot.run() 