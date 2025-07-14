#!/usr/bin/env python3
"""
Setup script for Binance API connection
This script helps you set up and test Binance API keys for paper trading
"""

import os
from pathlib import Path
from dotenv import load_dotenv, set_key
from exchange_handler import initialize_exchange

def create_env_file():
    """Create or update .env file with Binance API keys"""
    env_path = Path('.env')
    
    print("🔑 Binance API Setup")
    print("=" * 50)
    print("To get your Binance API keys:")
    print("1. Go to https://testnet.binance.vision/")
    print("2. Sign up for a testnet account")
    print("3. Generate API keys")
    print("4. Make sure to enable 'Spot & Margin Trading' permissions")
    print()
    
    # Get API keys from user
    api_key = input("Enter your Binance Testnet API Key: ").strip()
    api_secret = input("Enter your Binance Testnet API Secret: ").strip()
    
    if not api_key or not api_secret:
        print("❌ API key and secret are required!")
        return False
    
    # Update .env file
    set_key(env_path, 'BINANCE_API_KEY', api_key)
    set_key(env_path, 'BINANCE_API_SECRET', api_secret)
    set_key(env_path, 'BINANCE_TESTNET', 'true')
    set_key(env_path, 'EXCHANGE_NAME', 'binance')
    
    print("✅ API keys saved to .env file")
    return True

def test_connection():
    """Test the Binance API connection"""
    print("\n🔍 Testing Binance Connection...")
    print("=" * 50)
    
    try:
        # Reload environment variables
        load_dotenv()
        
        # Test connection
        exchange, balance = initialize_exchange("binance")
        
        if exchange:
            print(f"✅ Connection successful!")
            print(f"💰 Account Balance: ${balance:.2f}")
            print(f"📊 Available markets: {len(exchange.markets)}")
            
            # Test BTC/USDT market
            if 'BTC/USDT' in exchange.markets:
                ticker = exchange.fetch_ticker('BTC/USDT')
                print(f"📈 BTC/USDT Price: ${ticker['last']:.2f}")
            
            return True
        else:
            print("❌ Failed to connect to Binance")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Binance Paper Trading Setup")
    print("=" * 50)
    
    # Check if .env already exists
    if Path('.env').exists():
        load_dotenv()
        if os.getenv('BINANCE_API_KEY') and os.getenv('BINANCE_API_SECRET'):
            print("📁 Found existing Binance API keys in .env file")
            test_existing = input("Test existing connection? (y/n): ").strip().lower()
            if test_existing == 'y':
                if test_connection():
                    print("\n✅ Setup complete! You can now run paper trading with Binance.")
                    print("Run: python live_trading_bot.py")
                    return
        
        update_keys = input("Update API keys? (y/n): ").strip().lower()
        if update_keys != 'y':
            return
    
    # Create/update .env file
    if create_env_file():
        # Test connection
        if test_connection():
            print("\n✅ Setup complete! You can now run paper trading with Binance.")
            print("Run: python live_trading_bot.py")
        else:
            print("\n❌ Setup failed. Please check your API keys and try again.")
    else:
        print("\n❌ Setup cancelled.")

if __name__ == "__main__":
    main() 