#!/usr/bin/env python3
"""
Simple startup script for the live trading bot
"""
import os
import sys
from pathlib import Path

def main():
    print("🚀 Starting Live Trading Bot with State Persistence")
    print("=" * 60)
    
    # Check if required files exist
    required_files = [
        "live_trading_bot.py",
        "state_manager.py", 
        "exchange_handler.py",
        "strategies/__init__.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nPlease ensure all files are present before starting.")
        return
    
    print("✅ All required files found")
    print()
    
    # Show configuration
    print("📋 Bot Configuration:")
    print("   - Exchange: Bybit (Paper Trading)")
    print("   - Symbol: BTC/USDT")
    print("   - Timeframe: 4h")
    print("   - Check Interval: 5 minutes")
    print("   - Position Size: 1.5% risk per trade")
    print("   - Strategies: Ichimoku + RSI Reversal")
    print()
    
    # Show state persistence info
    print("💾 State Persistence:")
    print("   - State File: live_bot_state.json")
    print("   - Log File: trading_bot.log")
    print("   - Backup File: live_bot_state.backup.json")
    print()
    
    # Check if previous state exists
    state_file = Path("live_bot_state.json")
    if state_file.exists():
        print("🔄 Previous state found - bot will resume from last session")
    else:
        print("🆕 No previous state - bot will start fresh")
    print()
    
    print("⚠️  IMPORTANT REMINDERS:")
    print("   1. This is PAPER TRADING - no real money at risk")
    print("   2. Bot saves state every 5 minutes and after each trade")
    print("   3. You can safely stop/restart the bot anytime")
    print("   4. Use Ctrl+C to stop gracefully")
    print("   5. Check trading_bot.log for detailed logs")
    print()
    
    # Ask for confirmation
    response = input("Ready to start the live trading bot? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        print("\n🚀 Starting bot...")
        print("   (Press Ctrl+C to stop)")
        print("-" * 60)
        
        # Import and run the bot
        try:
            from live_trading_bot import LiveTradingBot
            bot = LiveTradingBot()
            bot.run()
        except KeyboardInterrupt:
            print("\n👋 Bot stopped by user")
        except Exception as e:
            print(f"\n❌ Error starting bot: {e}")
            print("Check the logs for more details")
    else:
        print("👋 Startup cancelled")

if __name__ == "__main__":
    main() 