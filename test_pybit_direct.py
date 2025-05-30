from pybit.unified_trading import HTTP
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
BYBIT_TESTNET_KEY = os.getenv('BYBIT_API_KEY')
BYBIT_TESTNET_SECRET = os.getenv('BYBIT_API_SECRET')

# Validate that keys are loaded
if not BYBIT_TESTNET_KEY or not BYBIT_TESTNET_SECRET:
    print("ERROR: BYBIT_API_KEY and BYBIT_API_SECRET must be set in .env file")
    exit(1)

print(f"Attempting to connect to Bybit Testnet using PyBit with API Key: {BYBIT_TESTNET_KEY[:5]}...")

try:
    session = HTTP(
        api_key=BYBIT_TESTNET_KEY,
        api_secret=BYBIT_TESTNET_SECRET,
        testnet=True,  # This flag directs PyBit to use https://api-testnet.bybit.com
    )

    print("PyBit session initialized.")
    print("Attempting to fetch wallet balance (accountType='UNIFIED' or 'SPOT')...")
    
    # Try fetching for different relevant account types for Testnet
    account_types_to_try = ["UNIFIED", "SPOT", "CONTRACT", "FUND"] 
    balance_info = None
    
    for acc_type in account_types_to_try:
        try:
            print(f"  Fetching for accountType='{acc_type}'...")
            response = session.get_wallet_balance(accountType=acc_type)
            # PyBit returns a dict, not a raw JSON string, if successful
            if response.get('retCode') == 0:
                print(f"✓ Success for accountType='{acc_type}'!")
                balance_info = response
                break # Found a working account type
            else:
                print(f"    Response for '{acc_type}': {response}")
        except Exception as e_acc_type:
            print(f"    ! Error fetching for accountType='{acc_type}': {e_acc_type}")

    if balance_info:
        print("\nSuccessfully fetched balance via PyBit:")
        print(balance_info)
    else:
        print("\nCould not fetch balance using PyBit for any common account type.")

except Exception as e:
    print(f"\n❌ ERROR during PyBit test: {e}")

print("\nPyBit direct test finished.") 