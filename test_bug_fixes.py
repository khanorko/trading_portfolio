#!/usr/bin/env python3
"""
Comprehensive Bug Fix Testing Script
Tests all the identified bugs and their fixes to ensure system reliability
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

# Set test environment
os.environ['TRADING_ENV'] = 'test'

# Import modules to test
from config import Config, ConfigValidationError
from state_manager import TradingStateManager, PositionManager, StateCorruptionError
from enhanced_state_manager import DashboardStateManager
from strategy_constants import StrategyNames, validate_strategy_name, get_strategy_db_name
from exchange_handler import ExchangeError, RetryableExchangeError

class TestConfigValidation(unittest.TestCase):
    """Test configuration validation fixes"""
    
    def setUp(self):
        """Set up test environment"""
        # Save original environment variables
        self.original_env = {}
        for key in ['INITIAL_CAPITAL', 'POSITION_SIZE_PCT', 'TRADING_FEE_RATE']:
            self.original_env[key] = os.environ.get(key)
    
    def tearDown(self):
        """Restore original environment"""
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
    
    def test_valid_configuration(self):
        """Test that valid configuration passes validation"""
        os.environ['INITIAL_CAPITAL'] = '4000'
        os.environ['POSITION_SIZE_PCT'] = '0.015'
        os.environ['TRADING_FEE_RATE'] = '0.001'
        
        # Should not raise exception
        config = Config()
        self.assertEqual(config.INITIAL_CAPITAL, 4000)
        self.assertEqual(config.POSITION_SIZE_PCT, 0.015)
    
    def test_invalid_initial_capital(self):
        """Test validation fails for invalid initial capital"""
        os.environ['INITIAL_CAPITAL'] = '50'  # Below minimum
        
        with self.assertRaises(ConfigValidationError):
            Config.validate_config()
    
    def test_invalid_position_size(self):
        """Test validation fails for invalid position size"""
        os.environ['POSITION_SIZE_PCT'] = '0.8'  # Above maximum
        
        with self.assertRaises(ConfigValidationError):
            Config.validate_config()
    
    def test_symbol_sanitization(self):
        """Test symbol sanitization works correctly"""
        # Valid symbols
        self.assertEqual(Config.sanitize_symbol('btc/usdt'), 'BTC/USDT')
        self.assertEqual(Config.sanitize_symbol(' ETH/USD '), 'ETH/USD')
        
        # Invalid symbols
        with self.assertRaises(ConfigValidationError):
            Config.sanitize_symbol('BTCUSDT')  # No separator
        
        with self.assertRaises(ConfigValidationError):
            Config.sanitize_symbol('')  # Empty string

class TestAtomicStateWrites(unittest.TestCase):
    """Test atomic state writing fixes"""
    
    def setUp(self):
        """Set up test state manager"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "test_state.json"
        self.state_manager = TradingStateManager(str(self.state_file))
        self.position_manager = PositionManager()
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_atomic_write_success(self):
        """Test successful atomic write creates file correctly"""
        result = self.state_manager.save_state(
            positions={},
            strategy_states={"test": {"signal": "buy"}},
            last_processed_timestamp="2024-01-01T00:00:00",
            equity_history={"2024-01-01": 4000.0},
            trade_history=[]
        )
        
        self.assertTrue(result)
        self.assertTrue(self.state_file.exists())
        
        # Load and verify content
        loaded_state = self.state_manager.load_state()
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state['strategy_states']['test']['signal'], 'buy')
    
    def test_backup_creation(self):
        """Test that backup files are created during updates"""
        # Create initial state
        self.state_manager.save_state(
            positions={}, strategy_states={}, last_processed_timestamp="",
            equity_history={}, trade_history=[]
        )
        
        # Update state (should create backup)
        self.state_manager.save_state(
            positions={}, strategy_states={"updated": True}, last_processed_timestamp="",
            equity_history={}, trade_history=[]
        )
        
        backup_file = self.state_file.with_suffix('.backup.json')
        self.assertTrue(backup_file.exists())
    
    def test_corrupted_state_recovery(self):
        """Test recovery from corrupted state file"""
        # Create valid backup
        backup_file = self.state_file.with_suffix('.backup.json')
        valid_state = {
            "positions": {},
            "strategy_states": {"backup": True},
            "last_processed_timestamp": "2024-01-01T00:00:00",
            "equity_history": {},
            "trade_history": []
        }
        
        with open(backup_file, 'w') as f:
            json.dump(valid_state, f)
        
        # Create corrupted main file
        with open(self.state_file, 'w') as f:
            f.write("corrupted json content {")
        
        # Should load from backup
        loaded_state = self.state_manager.load_state()
        self.assertIsNotNone(loaded_state)
        self.assertTrue(loaded_state['strategy_states']['backup'])

class TestStrategyNamingConsistency(unittest.TestCase):
    """Test strategy naming consistency fixes"""
    
    def test_strategy_name_validation(self):
        """Test strategy name validation works"""
        # Valid strategy names
        self.assertTrue(validate_strategy_name(StrategyNames.ICHIMOKU_TREND))
        self.assertTrue(validate_strategy_name(StrategyNames.ICHIMOKU_DB))
        self.assertTrue(validate_strategy_name(StrategyNames.REVERSAL_DISPLAY))
        
        # Invalid strategy names
        self.assertFalse(validate_strategy_name("UnknownStrategy"))
        self.assertFalse(validate_strategy_name(""))
    
    def test_strategy_name_conversion(self):
        """Test conversion between strategy name formats"""
        # Class name to DB name
        self.assertEqual(
            get_strategy_db_name(StrategyNames.ICHIMOKU_TREND),
            StrategyNames.ICHIMOKU_DB
        )
        
        # Should return original for unknown strategies
        self.assertEqual(
            get_strategy_db_name("UnknownStrategy"),
            "UnknownStrategy"
        )
    
    def test_dashboard_strategy_logging(self):
        """Test dashboard logs strategies with consistent names"""
        temp_dir = tempfile.mkdtemp()
        temp_db = Path(temp_dir) / "test_dashboard.db"
        
        try:
            dashboard = DashboardStateManager(state_file=temp_dir + "/test_state.json")
            dashboard.db_path = str(temp_db)
            dashboard.init_database()
            
            # Log trade with class name
            trade_data = {
                'symbol': 'BTC/USDT',
                'strategy': StrategyNames.ICHIMOKU_TREND,  # Class name
                'action': 'BUY',
                'quantity': 0.1,
                'price': 45000
            }
            
            dashboard.log_trade(trade_data)
            
            # Verify it was stored with DB name format
            import sqlite3
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT strategy FROM trades WHERE symbol = 'BTC/USDT'")
            result = cursor.fetchone()
            conn.close()
            
            self.assertEqual(result[0], StrategyNames.ICHIMOKU_DB)
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

class TestPositionManagerValidation(unittest.TestCase):
    """Test position manager input validation"""
    
    def setUp(self):
        """Set up position manager"""
        self.position_manager = PositionManager()
    
    def test_valid_position_creation(self):
        """Test creating valid positions"""
        pos_id = self.position_manager.add_position(
            symbol="BTC/USDT",
            strategy=StrategyNames.ICHIMOKU_TREND,
            quantity=0.1,
            entry_price=45000,
            entry_time="2024-01-01T00:00:00"
        )
        
        self.assertIsNotNone(pos_id)
        self.assertIn(pos_id, self.position_manager.positions)
    
    def test_invalid_position_parameters(self):
        """Test validation of invalid position parameters"""
        # Invalid symbol
        result = self.position_manager.add_position("", "strategy", 0.1, 45000, "2024-01-01T00:00:00")
        self.assertIsNone(result)
        
        # Invalid quantity
        result = self.position_manager.add_position("BTC/USDT", "strategy", -0.1, 45000, "2024-01-01T00:00:00")
        self.assertIsNone(result)
        
        # Invalid price
        result = self.position_manager.add_position("BTC/USDT", "strategy", 0.1, 0, "2024-01-01T00:00:00")
        self.assertIsNone(result)
    
    def test_price_update_validation(self):
        """Test price update validation"""
        # Add valid position
        pos_id = self.position_manager.add_position("BTC/USDT", "strategy", 0.1, 45000, "2024-01-01T00:00:00")
        
        # Valid price update
        self.position_manager.update_unrealized_pnl({"BTC/USDT": 46000})
        pos = self.position_manager.positions[pos_id]
        self.assertEqual(pos['unrealized_pnl'], 100.0)  # (46000 - 45000) * 0.1
        
        # Invalid price data (should not crash)
        self.position_manager.update_unrealized_pnl("invalid")  # Should handle gracefully

class TestExchangeErrorHandling(unittest.TestCase):
    """Test exchange error handling improvements"""
    
    def test_exchange_error_classification(self):
        """Test that errors are properly classified"""
        # Test retryable vs non-retryable errors
        retryable_error = RetryableExchangeError("Network timeout")
        non_retryable_error = ExchangeError("Invalid API key")
        
        self.assertIsInstance(retryable_error, ExchangeError)
        self.assertNotIsInstance(non_retryable_error, RetryableExchangeError)
    
    @patch('exchange_handler.ccxt')
    def test_exchange_initialization_retry(self, mock_ccxt):
        """Test exchange initialization with retry logic"""
        from exchange_handler import initialize_exchange
        
        # Mock bybit exchange
        mock_exchange = MagicMock()
        mock_exchange.load_markets.side_effect = [
            Exception("Network error"),  # First attempt fails
            None  # Second attempt succeeds
        ]
        mock_exchange.fetch_balance.return_value = {'USDT': {'total': 1000.0}}
        mock_ccxt.bybit.return_value = mock_exchange
        
        # Should succeed after retry
        exchange, balance = initialize_exchange("bybit", "test_key", "test_secret")
        
        # Should have been called twice (original + retry)
        self.assertEqual(mock_exchange.load_markets.call_count, 2)
        self.assertIsNotNone(exchange)

class TestSystemIntegration(unittest.TestCase):
    """Test overall system integration after fixes"""
    
    def test_full_workflow_robustness(self):
        """Test that the full workflow handles errors gracefully"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Initialize components
            state_manager = TradingStateManager(temp_dir + "/state.json")
            position_manager = PositionManager()
            dashboard = DashboardStateManager(temp_dir + "/state.json")
            dashboard.db_path = temp_dir + "/dashboard.db"
            dashboard.init_database()
            
            # Test workflow with various inputs
            test_cases = [
                {
                    'symbol': 'BTC/USDT',
                    'strategy': StrategyNames.ICHIMOKU_TREND,
                    'quantity': 0.1,
                    'price': 45000
                },
                {
                    'symbol': 'eth/usd',  # lowercase (should be sanitized)
                    'strategy': StrategyNames.RSI_REVERSAL,
                    'quantity': 0.5,
                    'price': 3000
                }
            ]
            
            for case in test_cases:
                # Add position
                pos_id = position_manager.add_position(
                    symbol=case['symbol'],
                    strategy=case['strategy'],
                    quantity=case['quantity'],
                    entry_price=case['price'],
                    entry_time="2024-01-01T00:00:00"
                )
                
                self.assertIsNotNone(pos_id)
                
                # Log trade
                trade_data = {
                    'symbol': case['symbol'],
                    'strategy': case['strategy'],
                    'action': 'BUY',
                    'quantity': case['quantity'],
                    'price': case['price']
                }
                
                dashboard.log_trade(trade_data)
            
            # Save state
            success = state_manager.save_state(
                positions=position_manager.positions,
                strategy_states={StrategyNames.ICHIMOKU_TREND: {"signal": "buy"}},
                last_processed_timestamp="2024-01-01T00:00:00",
                equity_history={"2024-01-01": 4000.0},
                trade_history=[]
            )
            
            self.assertTrue(success)
            
            # Verify state can be loaded
            loaded_state = state_manager.load_state()
            self.assertIsNotNone(loaded_state)
            self.assertEqual(len(loaded_state['positions']), 2)
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

def run_all_tests():
    """Run all bug fix tests"""
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestConfigValidation,
        TestAtomicStateWrites,
        TestStrategyNamingConsistency,
        TestPositionManagerValidation,
        TestExchangeErrorHandling,
        TestSystemIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"BUG FIX TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 