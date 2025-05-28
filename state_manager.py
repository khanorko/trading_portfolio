"""
State Manager for Trading Bot
Saves and restores bot state to prevent data loss on restart
"""
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

class TradingStateManager:
    def __init__(self, state_file: str = "bot_state.json"):
        self.state_file = Path(state_file)
        self.logger = logging.getLogger(__name__)
        
    def save_state(self, 
                   positions: Dict[str, Any],
                   strategy_states: Dict[str, Any],
                   last_processed_timestamp: str,
                   equity_history: Dict[str, float],
                   trade_history: list,
                   **kwargs) -> bool:
        """Save complete bot state to file"""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "positions": positions,
                "strategy_states": strategy_states,
                "last_processed_timestamp": last_processed_timestamp,
                "equity_history": equity_history,
                "trade_history": trade_history,
                "metadata": kwargs
            }
            
            # Create backup of existing state
            if self.state_file.exists():
                backup_file = self.state_file.with_suffix('.backup.json')
                self.state_file.rename(backup_file)
            
            # Save new state
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            self.logger.info(f"State saved successfully to {self.state_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False
    
    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load bot state from file"""
        try:
            if not self.state_file.exists():
                self.logger.info("No existing state file found. Starting fresh.")
                return None
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.logger.info(f"State loaded successfully from {self.state_file}")
            self.logger.info(f"Last saved: {state.get('timestamp', 'Unknown')}")
            
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            # Try backup file
            backup_file = self.state_file.with_suffix('.backup.json')
            if backup_file.exists():
                try:
                    with open(backup_file, 'r') as f:
                        state = json.load(f)
                    self.logger.info("Loaded from backup file")
                    return state
                except Exception as backup_e:
                    self.logger.error(f"Backup file also corrupted: {backup_e}")
            
            return None
    
    def get_positions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract positions from state"""
        return state.get("positions", {}) if state else {}
    
    def get_strategy_states(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract strategy states from state"""
        return state.get("strategy_states", {}) if state else {}
    
    def get_last_timestamp(self, state: Dict[str, Any]) -> Optional[str]:
        """Extract last processed timestamp"""
        return state.get("last_processed_timestamp") if state else None
    
    def get_equity_history(self, state: Dict[str, Any]) -> Dict[str, float]:
        """Extract equity history"""
        return state.get("equity_history", {}) if state else {}
    
    def get_trade_history(self, state: Dict[str, Any]) -> list:
        """Extract trade history"""
        return state.get("trade_history", []) if state else []

class PositionManager:
    """Manages current trading positions"""
    
    def __init__(self):
        self.positions = {}
    
    def add_position(self, symbol: str, strategy: str, 
                    quantity: float, entry_price: float, 
                    entry_time: str, stop_loss: float = None):
        """Add a new position"""
        position_id = f"{symbol}_{strategy}_{entry_time}"
        self.positions[position_id] = {
            "symbol": symbol,
            "strategy": strategy,
            "quantity": quantity,
            "entry_price": entry_price,
            "entry_time": entry_time,
            "stop_loss": stop_loss,
            "unrealized_pnl": 0.0,
            "status": "open"
        }
        return position_id
    
    def close_position(self, position_id: str, exit_price: float, exit_time: str):
        """Close an existing position"""
        if position_id in self.positions:
            pos = self.positions[position_id]
            pos["exit_price"] = exit_price
            pos["exit_time"] = exit_time
            pos["realized_pnl"] = (exit_price - pos["entry_price"]) * pos["quantity"]
            pos["status"] = "closed"
            return pos["realized_pnl"]
        return 0.0
    
    def update_unrealized_pnl(self, current_prices: Dict[str, float]):
        """Update unrealized P&L for all open positions"""
        for pos_id, pos in self.positions.items():
            if pos["status"] == "open" and pos["symbol"] in current_prices:
                current_price = current_prices[pos["symbol"]]
                pos["unrealized_pnl"] = (current_price - pos["entry_price"]) * pos["quantity"]
    
    def get_open_positions(self, symbol: str = None, strategy: str = None) -> Dict:
        """Get open positions, optionally filtered by symbol/strategy"""
        open_pos = {k: v for k, v in self.positions.items() if v["status"] == "open"}
        
        if symbol:
            open_pos = {k: v for k, v in open_pos.items() if v["symbol"] == symbol}
        if strategy:
            open_pos = {k: v for k, v in open_pos.items() if v["strategy"] == strategy}
            
        return open_pos
    
    def has_position(self, symbol: str, strategy: str) -> bool:
        """Check if we have an open position for symbol/strategy"""
        open_pos = self.get_open_positions(symbol, strategy)
        return len(open_pos) > 0
    
    def get_total_exposure(self, symbol: str) -> float:
        """Get total exposure (quantity) for a symbol"""
        open_pos = self.get_open_positions(symbol)
        return sum(pos["quantity"] for pos in open_pos.values())

# Example usage functions
def create_persistent_bot_state():
    """Example of how to integrate state management"""
    state_manager = TradingStateManager()
    position_manager = PositionManager()
    
    # Load previous state on startup
    saved_state = state_manager.load_state()
    if saved_state:
        # Restore positions
        position_manager.positions = state_manager.get_positions(saved_state)
        print(f"Restored {len(position_manager.positions)} positions")
        
        # Restore strategy states
        strategy_states = state_manager.get_strategy_states(saved_state)
        print(f"Restored strategy states: {list(strategy_states.keys())}")
        
        # Get last processed timestamp to resume from
        last_timestamp = state_manager.get_last_timestamp(saved_state)
        print(f"Last processed: {last_timestamp}")
    
    return state_manager, position_manager

if __name__ == "__main__":
    # Test the state manager
    state_mgr, pos_mgr = create_persistent_bot_state()
    
    # Example: Add a position
    pos_mgr.add_position("BTC/USDT", "Ichimoku", 0.1, 45000, "2024-01-01T10:00:00")
    
    # Save state
    state_mgr.save_state(
        positions=pos_mgr.positions,
        strategy_states={"ichimoku": {"last_signal": "buy"}},
        last_processed_timestamp="2024-01-01T10:00:00",
        equity_history={"2024-01-01": 4000.0},
        trade_history=[{"symbol": "BTC/USDT", "action": "buy", "price": 45000}]
    )
    
    print("State management test completed!") 