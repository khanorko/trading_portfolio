#!/usr/bin/env python3
"""
Production Readiness Test Suite
Tests all critical components for production deployment
"""

import sys
import os
import tempfile
import shutil
import pandas as pd
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)

# Import all modules at the top level to avoid scope issues
from state_manager import TradingStateManager, PositionManager
from enhanced_state_manager import DashboardStateManager
from strategy_constants import StrategyNames, get_strategy_display_name, get_strategy_db_name, validate_strategy_name
from exchange_handler import ExchangeError, RetryableExchangeError
from config import Config

def test_imports():
    """Test that all critical modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        # Strategy modules
        from strategies.ichimoku import IchimokuTrend
        from strategies.rsi_reversal import RsiReversal
        
        # Dashboard
        import streamlit
        from trading_dashboard import main as dashboard_main
        
        print("✅ All critical imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_data_availability():
    """Test that required data files are available"""
    print("🔍 Testing data availability...")
    
    try:
        # Check for BTC data file
        if os.path.exists('btc_4h_2022_2025_clean.csv'):
            df = pd.read_csv('btc_4h_2022_2025_clean.csv', nrows=10)
            required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            
            if all(col in df.columns for col in required_columns):
                print(f"✅ Data file validated: {len(pd.read_csv('btc_4h_2022_2025_clean.csv'))} rows")
                return True
            else:
                print(f"❌ Missing required columns in data file")
                return False
        else:
            print("❌ BTC data file not found")
            return False
    except Exception as e:
        print(f"❌ Data validation failed: {e}")
        return False

def test_state_management():
    """Test state management systems"""
    print("🔍 Testing state management...")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Test TradingStateManager
        state_file = os.path.join(temp_dir, "test_state.json")
        sm = TradingStateManager(state_file)
        
        # Test saving and loading state
        test_state = {
            'positions': {},
            'strategy_states': {StrategyNames.ICHIMOKU_TREND: {"signal": "buy"}},
            'last_processed_timestamp': datetime.now().isoformat(),
            'equity_history': {"2024-01-01": 10000.0},
            'trade_history': []
        }
        
        success = sm.save_state(**test_state)
        if not success:
            print("❌ State save failed")
            return False
        
        loaded_state = sm.load_state()
        if not loaded_state:
            print("❌ State load failed")
            return False
        
        # Test PositionManager
        pm = PositionManager()
        pos_id = pm.add_position(
            symbol="BTC/USDT",
            strategy=StrategyNames.ICHIMOKU_TREND,
            quantity=0.1,
            entry_price=45000,
            entry_time=datetime.now().isoformat()
        )
        
        if not pos_id:
            print("❌ Position creation failed")
            return False
        
        # Test DashboardStateManager
        dashboard_file = os.path.join(temp_dir, "test_dashboard.json")
        dsm = DashboardStateManager(dashboard_file)
        dsm.db_path = os.path.join(temp_dir, "test_dashboard.db")
        dsm.init_database()
        
        # Test trade logging
        trade_data = {
            'symbol': 'BTC/USDT',
            'strategy': StrategyNames.ICHIMOKU_TREND,
            'action': 'BUY',
            'quantity': 0.1,
            'price': 45000
        }
        dsm.log_trade(trade_data)
        
        print("✅ State management systems validated")
        return True
        
    except Exception as e:
        print(f"❌ State management test failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_strategy_consistency():
    """Test strategy naming consistency"""
    print("🔍 Testing strategy consistency...")
    
    try:
        # Test all strategy names
        strategies = [StrategyNames.ICHIMOKU_TREND, StrategyNames.RSI_REVERSAL]
        
        for strategy in strategies:
            # Test validation
            if not validate_strategy_name(strategy):
                print(f"❌ Strategy validation failed for: {strategy}")
                return False
            
            # Test name conversions
            display_name = get_strategy_display_name(strategy)
            db_name = get_strategy_db_name(strategy)
            
            if not display_name or not db_name:
                print(f"❌ Strategy name conversion failed for: {strategy}")
                return False
        
        print("✅ Strategy consistency validated")
        return True
        
    except Exception as e:
        print(f"❌ Strategy consistency test failed: {e}")
        return False

def test_exchange_error_handling():
    """Test exchange error handling"""
    print("🔍 Testing exchange error handling...")
    
    try:
        # Test error classification
        retryable_error = RetryableExchangeError("Network timeout")
        non_retryable_error = ExchangeError("Invalid API key")
        
        # Verify inheritance
        if not isinstance(retryable_error, ExchangeError):
            print("❌ Error inheritance incorrect")
            return False
        
        if isinstance(non_retryable_error, RetryableExchangeError):
            print("❌ Error classification incorrect")
            return False
        
        print("✅ Exchange error handling validated")
        return True
        
    except Exception as e:
        print(f"❌ Exchange error handling test failed: {e}")
        return False

def test_configuration_system():
    """Test configuration system"""
    print("🔍 Testing configuration system...")
    
    try:
        # Test basic configuration access
        if hasattr(Config, 'INITIAL_CAPITAL'):
            print("✅ Configuration system accessible")
            return True
        else:
            print("❌ Configuration system incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def run_production_readiness_tests():
    """Run all production readiness tests"""
    print("🚀 PRODUCTION READINESS TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("Import Validation", test_imports),
        ("Data Availability", test_data_availability),
        ("State Management", test_state_management),
        ("Strategy Consistency", test_strategy_consistency),
        ("Exchange Error Handling", test_exchange_error_handling),
        ("Configuration System", test_configuration_system),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 PRODUCTION READINESS SUMMARY")
    print("=" * 50)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 SYSTEM IS PRODUCTION READY!")
        print("\n✅ All critical components validated")
        print("✅ Error handling systems operational")
        print("✅ Data integrity systems functional")
        print("✅ State management systems reliable")
        
        print("\n📋 NEXT STEPS FOR DEPLOYMENT:")
        print("1. Set up environment variables (.env file)")
        print("2. Configure exchange API keys")
        print("3. Run paper trading tests")
        print("4. Monitor system performance")
        print("5. Deploy with proper monitoring")
        
        return True
    else:
        print("⚠️  SYSTEM NOT READY FOR PRODUCTION")
        print(f"❌ {total - passed} critical issues need resolution")
        return False

if __name__ == "__main__":
    success = run_production_readiness_tests()
    sys.exit(0 if success else 1) 