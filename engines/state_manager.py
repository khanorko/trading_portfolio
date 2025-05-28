"""
State Manager for Trading Bot
Handles saving and loading bot state to survive restarts
"""
import json
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional

class StateManager:
    def __init__(self, state_file: str = "bot_state.json", trades_file: str = "trade_history.csv"):
        self.state_file = state_file
        self.trades_file = trades_file
        
    def save_state(self, 
                   cash_balances: Dict[str, float],
                   positions: Dict[str, Dict],
                   last_processed_timestamp: str,
                   total_trades: int,
                   total_fees_paid: float,
                   metadata: Dict = None) -> bool:
        """Save current bot state to file"""
        try:
            # Convert any pandas Timestamps to strings in positions
            serializable_positions = {}
            for strategy, position in positions.items():
                if position:
                    serializable_position = {}
                    for key, value in position.items():
                        if hasattr(value, 'isoformat'):  # Check if it's a timestamp
                            serializable_position[key] = value.isoformat()
                        else:
                            serializable_position[key] = value
                    serializable_positions[strategy] = serializable_position
                else:
                    serializable_positions[strategy] = {}
            
            state = {
                "timestamp": datetime.now().isoformat(),
                "cash_balances": cash_balances,
                "positions": serializable_positions,
                "last_processed_timestamp": last_processed_timestamp,
                "total_trades": total_trades,
                "total_fees_paid": total_fees_paid,
                "metadata": metadata or {}
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            print(f"✅ State saved to {self.state_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving state: {e}")
            return False
    
    def load_state(self) -> Optional[Dict]:
        """Load bot state from file"""
        try:
            if not os.path.exists(self.state_file):
                print(f"📝 No existing state file found at {self.state_file}")
                return None
                
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            print(f"✅ State loaded from {self.state_file}")
            print(f"   Last saved: {state.get('timestamp', 'Unknown')}")
            print(f"   Total trades: {state.get('total_trades', 0)}")
            print(f"   Cash balances: {state.get('cash_balances', {})}")
            print(f"   Open positions: {len(state.get('positions', {}))}")
            
            return state
            
        except Exception as e:
            print(f"❌ Error loading state: {e}")
            return None
    
    def save_trade(self, trade_data: Dict) -> bool:
        """Save individual trade to CSV history"""
        try:
            # Convert trade data to DataFrame row
            trade_df = pd.DataFrame([trade_data])
            
            # Append to existing file or create new one
            if os.path.exists(self.trades_file):
                trade_df.to_csv(self.trades_file, mode='a', header=False, index=False)
            else:
                trade_df.to_csv(self.trades_file, index=False)
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving trade: {e}")
            return False
    
    def load_trade_history(self) -> Optional[pd.DataFrame]:
        """Load complete trade history"""
        try:
            if not os.path.exists(self.trades_file):
                return pd.DataFrame()
                
            return pd.read_csv(self.trades_file)
            
        except Exception as e:
            print(f"❌ Error loading trade history: {e}")
            return pd.DataFrame()
    
    def backup_state(self) -> bool:
        """Create a timestamped backup of current state"""
        try:
            if not os.path.exists(self.state_file):
                return False
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"bot_state_backup_{timestamp}.json"
            
            with open(self.state_file, 'r') as src:
                with open(backup_file, 'w') as dst:
                    dst.write(src.read())
            
            print(f"✅ State backed up to {backup_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            return False
    
    def clear_state(self) -> bool:
        """Clear all saved state (use with caution!)"""
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
            if os.path.exists(self.trades_file):
                os.remove(self.trades_file)
            
            print("✅ All state files cleared")
            return True
            
        except Exception as e:
            print(f"❌ Error clearing state: {e}")
            return False 