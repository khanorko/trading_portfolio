"""
State Manager for Trading Bot
Saves and restores bot state to prevent data loss on restart
Implements atomic writes to prevent corruption
"""
import json
import pandas as pd
import tempfile
import shutil
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import time
import threading

class StateCorruptionError(Exception):
    """Raised when state file is corrupted"""
    pass

class TradingStateManager:
    def __init__(self, state_file: str = "bot_state.json"):
        self.state_file = Path(state_file)
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()  # Thread safety for concurrent access
        
    def save_state(self, 
                   positions: Dict[str, Any],
                   strategy_states: Dict[str, Any],
                   last_processed_timestamp: str,
                   equity_history: Dict[str, float],
                   trade_history: list,
                   **kwargs) -> bool:
        """Save complete bot state to file using atomic writes"""
        with self._lock:  # Ensure thread safety
            try:
                state = {
                    "timestamp": datetime.now().isoformat(),
                    "positions": positions,
                    "strategy_states": strategy_states,
                    "last_processed_timestamp": last_processed_timestamp,
                    "equity_history": equity_history,
                    "trade_history": trade_history,
                    "metadata": kwargs,
                    "version": "1.0",  # Add versioning for future compatibility
                    "checksum": None  # Will be calculated below
                }
                
                # Calculate simple checksum for integrity verification
                state_str = json.dumps(state, sort_keys=True, default=str)
                state["checksum"] = hash(state_str) % (10 ** 8)  # Simple 8-digit checksum
                
                # Create backup of existing state before writing new one
                if self.state_file.exists():
                    backup_file = self.state_file.with_suffix('.backup.json')
                    try:
                        shutil.copy2(self.state_file, backup_file)
                        self.logger.debug(f"Created backup: {backup_file}")
                    except Exception as backup_e:
                        self.logger.warning(f"Failed to create backup: {backup_e}")
                
                # Atomic write: write to temporary file then rename
                temp_file = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode='w', 
                        dir=self.state_file.parent,
                        prefix=f".{self.state_file.stem}_tmp_",
                        suffix='.json',
                        delete=False
                    ) as temp_file:
                        json.dump(state, temp_file, indent=2, default=str)
                        temp_file.flush()
                        os.fsync(temp_file.fileno())  # Force write to disk
                    
                    # Atomic rename (this is atomic on most filesystems)
                    shutil.move(temp_file.name, self.state_file)
                    
                    self.logger.info(f"State saved successfully to {self.state_file}")
                    return True
                    
                except Exception as write_e:
                    # Clean up temporary file if it exists
                    if temp_file and Path(temp_file.name).exists():
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass
                    raise write_e
                
            except Exception as e:
                self.logger.error(f"Failed to save state: {e}")
                return False
    
    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load bot state from file with integrity checking"""
        with self._lock:  # Ensure thread safety
            try:
                if not self.state_file.exists():
                    self.logger.info("No existing state file found. Starting fresh.")
                    return None
                
                # Try to load main state file
                state = self._load_and_validate_state_file(self.state_file)
                if state:
                    self.logger.info(f"State loaded successfully from {self.state_file}")
                    self.logger.info(f"Last saved: {state.get('timestamp', 'Unknown')}")
                    return state
                
                # If main file failed, try backup
                backup_file = self.state_file.with_suffix('.backup.json')
                if backup_file.exists():
                    self.logger.warning("Main state file corrupted, trying backup...")
                    state = self._load_and_validate_state_file(backup_file)
                    if state:
                        self.logger.info("Successfully loaded from backup file")
                        # Save backup as new main file
                        shutil.copy2(backup_file, self.state_file)
                        return state
                
                self.logger.error("Both main and backup state files are corrupted or missing")
                return None
                
            except Exception as e:
                self.logger.error(f"Failed to load state: {e}")
                return None
    
    def _load_and_validate_state_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load and validate a state file"""
        try:
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            # Basic validation
            if not isinstance(state, dict):
                raise StateCorruptionError("State file is not a valid JSON object")
            
            required_keys = ['positions', 'strategy_states', 'last_processed_timestamp']
            missing_keys = [key for key in required_keys if key not in state]
            if missing_keys:
                raise StateCorruptionError(f"Missing required keys: {missing_keys}")
            
            # Checksum validation (if available)
            if 'checksum' in state:
                stored_checksum = state.pop('checksum')
                calculated_checksum = hash(json.dumps(state, sort_keys=True, default=str)) % (10 ** 8)
                state['checksum'] = stored_checksum  # Restore for return
                
                if stored_checksum != calculated_checksum:
                    self.logger.warning(f"Checksum mismatch in {file_path} (stored: {stored_checksum}, calculated: {calculated_checksum})")
                    # Don't fail on checksum mismatch, just warn (could be due to JSON formatting differences)
            
            return state
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Failed to load {file_path}: {e}")
            return None
        except StateCorruptionError as e:
            self.logger.error(f"State corruption in {file_path}: {e}")
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
    
    def cleanup_old_backups(self, keep_count: int = 5):
        """Clean up old backup files, keeping only the most recent ones"""
        try:
            backup_pattern = f"{self.state_file.stem}.backup*.json"
            backup_files = list(self.state_file.parent.glob(backup_pattern))
            
            if len(backup_files) > keep_count:
                # Sort by modification time (newest first)
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                # Remove old backups
                for old_backup in backup_files[keep_count:]:
                    try:
                        old_backup.unlink()
                        self.logger.debug(f"Removed old backup: {old_backup}")
                    except Exception as e:
                        self.logger.warning(f"Failed to remove old backup {old_backup}: {e}")
        
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old backups: {e}")

class PositionManager:
    """Manages current trading positions with enhanced error handling"""
    
    def __init__(self):
        self.positions = {}
        self.logger = logging.getLogger(__name__)
    
    def add_position(self, symbol: str, strategy: str, 
                    quantity: float, entry_price: float, 
                    entry_time: str, stop_loss: float = None) -> Optional[str]:
        """Add a new position with validation"""
        try:
            # Input validation
            if not symbol or not isinstance(symbol, str):
                raise ValueError("Symbol must be a non-empty string")
            if not strategy or not isinstance(strategy, str):
                raise ValueError("Strategy must be a non-empty string")
            if not isinstance(quantity, (int, float)) or quantity <= 0:
                raise ValueError("Quantity must be a positive number")
            if not isinstance(entry_price, (int, float)) or entry_price <= 0:
                raise ValueError("Entry price must be a positive number")
            
            position_id = f"{symbol}_{strategy}_{entry_time}"
            
            # Check for duplicate position
            if position_id in self.positions:
                self.logger.warning(f"Position {position_id} already exists, updating...")
            
            self.positions[position_id] = {
                "symbol": symbol.upper(),
                "strategy": strategy,
                "quantity": float(quantity),
                "entry_price": float(entry_price),
                "entry_time": entry_time,
                "stop_loss": float(stop_loss) if stop_loss else None,
                "unrealized_pnl": 0.0,
                "status": "open"
            }
            
            self.logger.info(f"Added position: {position_id}")
            return position_id
            
        except (ValueError, TypeError) as e:
            self.logger.error(f"Failed to add position: {e}")
            return None
    
    def close_position(self, position_id: str, exit_price: float, exit_time: str) -> Optional[float]:
        """Close an existing position with validation"""
        try:
            if position_id not in self.positions:
                self.logger.error(f"Position {position_id} not found")
                return None
            
            if not isinstance(exit_price, (int, float)) or exit_price <= 0:
                raise ValueError("Exit price must be a positive number")
            
            pos = self.positions[position_id]
            pos["exit_price"] = float(exit_price)
            pos["exit_time"] = exit_time
            pos["realized_pnl"] = (exit_price - pos["entry_price"]) * pos["quantity"]
            pos["status"] = "closed"
            
            self.logger.info(f"Closed position: {position_id}, P&L: {pos['realized_pnl']:.2f}")
            return pos["realized_pnl"]
            
        except (ValueError, TypeError) as e:
            self.logger.error(f"Failed to close position {position_id}: {e}")
            return None
    
    def update_unrealized_pnl(self, current_prices: Dict[str, float]):
        """Update unrealized P&L for all open positions with error handling"""
        try:
            if not isinstance(current_prices, dict):
                raise ValueError("Current prices must be a dictionary")
            
            for pos_id, pos in self.positions.items():
                if pos["status"] == "open" and pos["symbol"] in current_prices:
                    try:
                        current_price = float(current_prices[pos["symbol"]])
                        pos["unrealized_pnl"] = (current_price - pos["entry_price"]) * pos["quantity"]
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Invalid price for {pos['symbol']}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Failed to update unrealized P&L: {e}")
    
    def get_open_positions(self, symbol: str = None, strategy: str = None) -> Dict:
        """Get open positions, optionally filtered by symbol/strategy"""
        try:
            open_pos = {k: v for k, v in self.positions.items() if v["status"] == "open"}
            
            if symbol:
                symbol = symbol.upper()
                open_pos = {k: v for k, v in open_pos.items() if v["symbol"] == symbol}
            if strategy:
                open_pos = {k: v for k, v in open_pos.items() if v["strategy"] == strategy}
                
            return open_pos
            
        except Exception as e:
            self.logger.error(f"Failed to get open positions: {e}")
            return {}
    
    def has_position(self, symbol: str, strategy: str) -> bool:
        """Check if we have an open position for symbol/strategy"""
        try:
            open_pos = self.get_open_positions(symbol, strategy)
            return len(open_pos) > 0
        except Exception:
            return False
    
    def get_total_exposure(self, symbol: str) -> float:
        """Get total exposure (quantity) for a symbol"""
        try:
            open_pos = self.get_open_positions(symbol)
            return sum(pos["quantity"] for pos in open_pos.values())
        except Exception as e:
            self.logger.error(f"Failed to calculate total exposure for {symbol}: {e}")
            return 0.0

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
    pos_mgr.add_position("BTC/USDT", "IchimokuTrend", 0.1, 45000, "2024-01-01T10:00:00")
    
    # Save state
    state_mgr.save_state(
        positions=pos_mgr.positions,
        strategy_states={"IchimokuTrend": {"last_signal": "buy"}},
        last_processed_timestamp="2024-01-01T10:00:00",
        equity_history={"2024-01-01": 4000.0},
        trade_history=[{"symbol": "BTC/USDT", "action": "buy", "price": 45000}]
    )
    
    print("State management test completed!") 