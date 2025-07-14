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
from enhanced_state_manager import DashboardStateManager
from config import Config

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
        
        # Trading parameters from config
        self.trading_fee_rate = Config.TRADING_FEE_RATE
        self.slippage_rate = Config.SLIPPAGE_RATE
        self.min_profit_threshold = Config.MIN_PROFIT_THRESHOLD
        self.position_size_pct = Config.POSITION_SIZE_PCT  # 1.5% risk per trade
        
        # Initialize components
        self.state_manager = TradingStateManager("live_bot_state.json")
        self.dashboard_state = DashboardStateManager()
        self.position_manager = PositionManager()
        self.strategies = [IchimokuTrend(), RsiReversal()]
        
        # Exchange connection
        self.exchange = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown (only works in main thread)
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        except ValueError:
            # Signal handlers can only be set in main thread
            # When running in Streamlit, we'll handle shutdown differently
            logger.info("Signal handlers not available (not in main thread)")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.running = False
        self.save_state()
        # Only exit if running as standalone script
        if __name__ == "__main__":
            sys.exit(0)
    
    def stop(self):
        """Stop the bot gracefully (for Streamlit interface)"""
        logger.info("Stopping bot via Streamlit interface...")
        self.running = False
        self.save_state()
    
    def initialize(self):
        """Initialize exchange and restore state"""
        logger.info("Initializing Live Trading Bot...")
        
        # Initialize exchange
        try:
            self.exchange, balance = initialize_exchange(
                exchange_name=self.exchange_name,
                paper_mode=True
            )
            
            if not self.exchange:
                logger.error("Failed to initialize exchange - running in simulation mode")
                # Continue with simulation mode
                self.exchange = None
                balance = 4000.0  # Mock balance
            else:
                logger.info(f"Exchange initialized. Balance: {balance:.2f} USDT")
                
        except Exception as e:
            from exchange_handler import ExchangeError
            if isinstance(e, ExchangeError):
                # Non-retryable error (geographic blocking, invalid credentials, etc.)
                logger.warning(f"Exchange not available: {e}")
                logger.info("Continuing in simulation mode with mock data")
            else:
                # Other errors
                logger.error(f"Exchange initialization failed: {e}")
                logger.info("Continuing in simulation mode with mock data")
            
            self.exchange = None
            balance = 4000.0  # Mock balance
        
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
            # If exchange is not available, generate mock data
            if self.exchange is None:
                logger.info("Exchange not available, generating mock data")
                return self._generate_mock_data(lookback_hours)
            
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
                logger.warning("No data fetched from exchange, falling back to mock data")
                return self._generate_mock_data(lookback_hours)
                
        except Exception as e:
            logger.error(f"Error fetching data: {e}, falling back to mock data")
            return self._generate_mock_data(lookback_hours)
    
    def _generate_mock_data(self, lookback_hours: int = 200) -> pd.DataFrame:
        """Generate mock market data for testing"""
        import numpy as np
        
        # Generate timestamps
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=lookback_hours)
        
        # Create 4-hour intervals
        periods = int(lookback_hours / 4)
        timestamps = pd.date_range(start=start_time, end=end_time, periods=periods)
        
        # Generate realistic price data starting from ~$95,000
        np.random.seed(42)  # For reproducible results
        base_price = 95000.0
        
        # Generate price movements
        returns = np.random.normal(0.001, 0.02, len(timestamps))  # Small positive drift with volatility
        prices = [base_price]
        
        for i in range(1, len(timestamps)):
            new_price = prices[-1] * (1 + returns[i])
            prices.append(new_price)
        
        # Create OHLCV data
        data = []
        for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
            # Generate realistic OHLC from close price
            volatility = close * 0.01  # 1% volatility
            high = close + np.random.uniform(0, volatility)
            low = close - np.random.uniform(0, volatility)
            open_price = close + np.random.uniform(-volatility/2, volatility/2)
            volume = np.random.uniform(100, 1000)
            
            data.append({
                'open': open_price,
                'high': max(open_price, high, close),
                'low': min(open_price, low, close),
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data, index=timestamps)
        
        # Precompute indicators
        for strategy in self.strategies:
            strategy.precompute_indicators(df)
        
        logger.info(f"Generated {len(df)} mock candles. Latest price: ${df['close'].iloc[-1]:.2f}")
        return df
    
    def check_signals_and_trade(self, df: pd.DataFrame):
        """Check for trading signals and execute trades"""
        if df is None or df.empty:
            return
        
        latest_row = df.iloc[-1]
        current_price = latest_row['close']
        current_time = latest_row.name.isoformat()
        
        logger.info(f"Checking signals at {current_time}, Price: ${current_price:.2f}")
        
        # Update unrealized P&L for open positions
        self.position_manager.update_unrealized_pnl({self.symbol: float(current_price)})
        
        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__
            
            try:
                # Check if we already have a position for this strategy
                has_position = self.position_manager.has_position(self.symbol, strategy_name)
                
                if not has_position:
                    # Check for entry signal
                    signal = strategy.entry_signal(latest_row.name, df)
                    
                    if signal:  # Buy signal
                        self.execute_entry_trade(strategy_name, current_price, current_time, latest_row)
                
                else:
                    # Check for exit signal
                    open_positions = self.position_manager.get_open_positions(self.symbol, strategy_name)
                    
                    for pos_id, position in open_positions.items():
                        should_exit = strategy.exit_signal(latest_row.name, df, position['entry_price'])
                        
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
                
                # Execute trade on exchange or simulate if not available
                trade_result = None
                if self.exchange is not None:
                    trade_result = execute_trade(
                        exchange_obj=self.exchange,
                        symbol=self.symbol,
                        side="buy",
                        quantity=quantity,
                        order_type="market"
                    )
                else:
                    # Simulate successful trade when exchange is not available
                    logger.info("Simulating trade execution (exchange not available)")
                    trade_result = {
                        'symbol': self.symbol,
                        'side': 'buy',
                        'amount': quantity,
                        'price': price,
                        'timestamp': timestamp,
                        'simulated': True
                    }
                
                if trade_result:
                    # Add position to manager
                    pos_id = self.position_manager.add_position(
                        symbol=self.symbol,
                        strategy=strategy_name,
                        quantity=quantity,
                        entry_price=price,
                        entry_time=timestamp
                    )
                    
                    # Log trade to dashboard
                    trade_data = {
                        'symbol': self.symbol,
                        'strategy': strategy_name,
                        'side': 'buy',
                        'quantity': quantity,
                        'price': price,
                        'timestamp': timestamp,
                        'position_id': pos_id
                    }
                    self.dashboard_state.log_trade(trade_data)
                    
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
            
            # Execute trade on exchange or simulate if not available
            trade_result = None
            if self.exchange is not None:
                trade_result = execute_trade(
                    exchange_obj=self.exchange,
                    symbol=self.symbol,
                    side="sell",
                    quantity=quantity,
                    order_type="market"
                )
            else:
                # Simulate successful trade when exchange is not available
                logger.info("Simulating trade execution (exchange not available)")
                trade_result = {
                    'symbol': self.symbol,
                    'side': 'sell',
                    'amount': quantity,
                    'price': price,
                    'timestamp': timestamp,
                    'simulated': True
                }
            
            if trade_result:
                # Close position
                pnl = self.position_manager.close_position(pos_id, price, timestamp)
                
                # Log trade to dashboard
                trade_data = {
                    'symbol': self.symbol,
                    'strategy': strategy_name,
                    'side': 'sell',
                    'quantity': quantity,
                    'price': price,
                    'timestamp': timestamp,
                    'position_id': pos_id,
                    'pnl': pnl
                }
                self.dashboard_state.log_trade(trade_data)
                
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
                
                # Log equity snapshot for dashboard
                if len(df) > 0:
                    current_price = df.iloc[-1]['close']
                    current_positions = self.position_manager.get_open_positions()
                    self.dashboard_state.log_equity_snapshot(self.position_manager, {self.symbol: float(current_price)})
                
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