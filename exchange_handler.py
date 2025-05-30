import ccxt
import pandas as pd
import decimal
import time
import traceback # Import traceback module
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API Configuration from Environment Variables ---
# Alpaca Configuration
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_API_SECRET = os.getenv('ALPACA_API_SECRET')

# Bybit Configuration
BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET')
BYBIT_TESTNET = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'

# Validate that required keys are loaded
if not BYBIT_API_KEY or not BYBIT_API_SECRET:
    print("WARNING: BYBIT_API_KEY and BYBIT_API_SECRET not found in environment variables.")
    print("Please create a .env file with your API keys or set them as environment variables.")

# ALPACA_PAPER_URL = "https://paper-api.alpaca.markets" # No longer directly used in config
# --------------------------

# --- Bybit Configuration ---
# IMPORTANT: For Bybit Testnet, generate keys from https://testnet.bybit.com
# For Bybit Live, generate keys from https://www.bybit.com
# --------------------------

def initialize_exchange(exchange_name="bybit", api_key=None, secret_key=None, paper_mode=True):
    """Initializes the CCXT exchange object.
    Uses environment variables if api_key or secret_key are not provided.

    Args:
        exchange_name (str): The exchange to use ('alpaca' or 'bybit'). Defaults to "bybit".
        api_key (str, optional): Your API key. Defaults to None (uses environment variable).
        secret_key (str, optional): Your API secret. Defaults to None (uses environment variable).
        paper_mode (bool): Whether to use Paper Trading (Alpaca) or Testnet (Bybit). Defaults to True.

    Returns:
        ccxt.Exchange: Initialized exchange object, or None if initialization fails.
    """
    final_api_key = None
    final_secret_key = None

    if exchange_name.lower() == "alpaca":
        final_api_key = api_key if api_key else ALPACA_API_KEY
        final_secret_key = secret_key if secret_key else ALPACA_API_SECRET
        if not final_api_key or not final_secret_key:
            print(f"ERROR: Alpaca API Key or Secret Key is missing.")
            return None
    elif exchange_name.lower() == "bybit":
        final_api_key = api_key if api_key else BYBIT_API_KEY
        final_secret_key = secret_key if secret_key else BYBIT_API_SECRET
        if not final_api_key or not final_secret_key:
            print(f"ERROR: Bybit API Key or Secret Key is missing.")
            return None
    else:
        print(f"ERROR: Unsupported exchange '{exchange_name}'. Supported exchanges: 'alpaca', 'bybit'")
        return None

    exchange = None
    try:
        if exchange_name.lower() == "alpaca":
            config = {
                'apiKey': final_api_key,
                'secret': final_secret_key,
                'enableRateLimit': True,
                'verbose': False,
            }
            exchange = ccxt.alpaca(config)
            if paper_mode:
                print(f"INFO: Alpaca: Enabling Paper Trading mode (https://paper-api.alpaca.markets)")
                exchange.set_sandbox_mode(True) # For Alpaca, this points to paper-api.alpaca.markets
            else:
                print(f"INFO: Alpaca: Using Live Trading API.")

        elif exchange_name.lower() == "bybit":
            config = {
                'apiKey': final_api_key,
                'secret': final_secret_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}, # Default to spot, can be 'linear' for USDT perps
                'verbose': False,
            }
            exchange = ccxt.bybit(config)

            if paper_mode:
                print(f"\nINFO: Bybit: Enabling Testnet mode.")
                print(f"      Make sure API keys were generated on https://testnet.bybit.com")
                exchange.set_sandbox_mode(True) # This switches URLs to https://api-testnet.bybit.com
                print(f"      API endpoint should now be: https://api-testnet.bybit.com")
            else:
                print(f"\nINFO: Bybit: Using Live Trading API (https://api.bybit.com)")
                print(f"      Make sure API keys were generated on https://www.bybit.com")

        print(f"\nCCXT Version: {ccxt.__version__}")
        print(f"Attempting to connect to {exchange_name.capitalize()} ({'Testnet/Paper' if paper_mode else 'Live'})...")

        # Test connection with a public endpoint first
        print(f"\n[1] Testing {exchange_name.capitalize()} public API endpoint (fetch server time)...")
        timestamp = exchange.fetch_time()
        print(f"✓ Server time: {timestamp} ({pd.to_datetime(timestamp, unit='ms')} UTC)")

        print(f"\n[2] Loading market data...")
        exchange.load_markets()
        market_count = len(exchange.markets) if exchange.markets else 0
        print(f"✓ {market_count} markets available.")

        if exchange_name.lower() == "bybit":
            print(f"\n[3] Fetching ticker for BTC/USDT...")
            ticker = exchange.fetch_ticker('BTC/USDT') # Common spot market ticker
            print(f"✓ BTC/USDT last price: {ticker['last']}")

        # Test private endpoint (authentication)
        print(f"\n[4] Testing private API endpoint (fetch balance)...")
        balance_params = {}
        if exchange_name.lower() == "bybit" and exchange.options.get('defaultType') == 'spot':
             # For Bybit spot, specify accountType if needed, or let CCXT handle defaults
             # The playbook suggests fetch_balance({"type": "spot"}), CCXT might map this to accountType or similar
             # For Unified Trading Accounts (UTA), 'UNIFIED' or 'CONTRACT'. For normal Spot, 'SPOT'.
             # Let's try with default first, then with specific type if error or empty
             pass # Rely on CCXT default first

        balance = exchange.fetch_balance(balance_params)
        print(f"✓ Authentication successful! Account balance retrieved.")

        # Detailed inspection for Bybit Unified Trading Account
        if exchange_name.lower() == "bybit":
            print("    Inspecting raw balance response for UTA structure:")
            # balance.get('info') usually contains the raw response from the exchange
            raw_balance_info = balance.get('info', {})
            print(f"      Raw info: {raw_balance_info}")
            
            if isinstance(raw_balance_info.get('result'), dict) and isinstance(raw_balance_info['result'].get('list'), list):
                uta_list = raw_balance_info['result']['list']
                if uta_list:
                    for uta_account_details in uta_list:
                        acc_type = uta_account_details.get('accountType')
                        print(f"    Account Type from list: {acc_type}")
                        total_wallet_balance = uta_account_details.get('totalWalletBalance')
                        coins = uta_account_details.get('coin', [])
                        print(f"      Total Wallet Balance ({acc_type}): {total_wallet_balance}")
                        if coins:
                            print("      Assets in this account type:")
                            for coin_data in coins:
                                asset_name = coin_data.get('coin')
                                equity = coin_data.get('equity')
                                usd_value = coin_data.get('usdValue')
                                wallet_balance_coin = coin_data.get('walletBalance')
                                print(f"        - {asset_name}: Equity={equity}, USD Value={usd_value}, Wallet Balance={wallet_balance_coin}")
                        else:
                            print("        No individual coin data listed under this account type.")
                else:
                    print("    UTA 'list' is empty in raw balance response.")
            else:
                print("    Raw balance response does not match expected UTA list structure.")

        # General non-zero asset check from 'total' (fallback)
        total_balance_ccxt = balance.get('total', {})
        non_zero_assets = {asset: amount for asset, amount in total_balance_ccxt.items() if amount > 0}
        if non_zero_assets:
            print("\n    Assets from CCXT 'total' field (non-zero):")
            for asset, amount in non_zero_assets.items():
                print(f"      - {asset}: {amount}")
        else:
            print("\n    No assets with non-zero balance found in CCXT parsed 'total' field.")

        print(f"\nSuccessfully connected and tested {exchange_name.capitalize()}!")
        
        # Fetch and return USDT balance along with the exchange object
        usdt_available_balance = get_usdt_balance(exchange) # Call the new function
        
        return exchange, usdt_available_balance # Return both

    except ccxt.AuthenticationError as e_auth:
        print(f"\n❌ AUTHENTICATION ERROR for {exchange_name.capitalize()}: {e_auth}")
        if exchange_name.lower() == "bybit":
            if paper_mode:
                print("    Ensure your API keys are for TESTNET (from https://testnet.bybit.com).Mismatch between live/testnet keys is common.")
            else:
                print("    Ensure your API keys are for LIVE (from https://www.bybit.com).")
        print("    Check API key, secret, permissions, and IP whitelist if applicable.")
        traceback.print_exc()
    except ccxt.NetworkError as e_net:
        print(f"\n❌ NETWORK ERROR for {exchange_name.capitalize()}: {e_net}")
        print("    Check your internet connection and if the exchange API is reachable.")
        traceback.print_exc()
    except ccxt.ExchangeError as e_exc:
        print(f"\n❌ EXCHANGE ERROR for {exchange_name.capitalize()}: {e_exc}")
        print("    This could be a temporary issue with the exchange or an invalid request.")
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR during {exchange_name.capitalize()} initialization: {e}")
        traceback.print_exc()
    
    return None, 0.0 # Return tuple in case of failure too

# --- New function to fetch historical OHLCV data ---
def fetch_historical_ohlcv(exchange_obj, symbol, timeframe='4h', start_date_str=None, end_date_str=None, limit_per_fetch=500):
    """
    Fetches historical OHLCV (Open, High, Low, Close, Volume) data from the exchange.

    Args:
        exchange_obj (ccxt.Exchange): Initialized CCXT exchange object.
        symbol (str): The trading symbol (e.g., 'BTC/USDT').
        timeframe (str): The timeframe for candles (e.g., '1m', '5m', '1h', '4h', '1d').
        start_date_str (str, optional): Start date string (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD).
                                         If None, fetches most recent data up to limit.
        end_date_str (str, optional): End date string (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD).
                                       If None, fetches data up to the present.
        limit_per_fetch (int): Number of candles to fetch per API call.

    Returns:
        pandas.DataFrame: DataFrame with OHLCV data, DatetimeIndex, and columns
                          ['open', 'high', 'low', 'close', 'volume'], or None if error.
    """
    if not exchange_obj.has['fetchOHLCV']:
        print(f"ERROR: Exchange {exchange_obj.id} does not support fetchOHLCV().")
        return None

    try:
        # Convert start_date_str and end_date_str to milliseconds timestamps
        since_timestamp = None
        if start_date_str:
            # Ensure datetime conversion handles various formats flexibly
            parsed_start_date = pd.to_datetime(start_date_str, errors='coerce')
            if pd.isna(parsed_start_date):
                print(f"ERROR: Could not parse start_date_str: {start_date_str}")
                return None
            since_timestamp = exchange_obj.parse8601(parsed_start_date.isoformat())


        end_datetime_obj = None
        if end_date_str:
            end_datetime_obj = pd.to_datetime(end_date_str, errors='coerce')
            if pd.isna(end_datetime_obj):
                print(f"ERROR: Could not parse end_date_str: {end_date_str}")
                return None

        all_candles = []
        current_since = since_timestamp
        is_first_fetch = True

        while True:
            fetch_start_time_str = pd.to_datetime(current_since, unit='ms').isoformat() if current_since else "latest available"
            print(f"Fetching {limit_per_fetch} {timeframe} candles for {symbol} from {fetch_start_time_str}...")
            
            params = {} 
            candles = exchange_obj.fetch_ohlcv(symbol, timeframe, since=current_since, limit=limit_per_fetch, params=params)

            if not candles: 
                if is_first_fetch and since_timestamp:
                     print(f"WARN: No data returned from exchange for {symbol} starting {start_date_str}.")
                elif not is_first_fetch:
                    print("No more candles returned, assuming end of data for the period.")
                else:
                    print("No candles returned on the first fetch (without a specific start date).")
                break
            
            is_first_fetch = False
            all_candles.extend(candles)
            
            last_candle_timestamp = candles[-1][0]
            
            # Stop if the last candle fetched is beyond the desired end_date_str
            if end_datetime_obj and pd.to_datetime(last_candle_timestamp, unit='ms') > end_datetime_obj:
                print(f"Last fetched candle timestamp ({pd.to_datetime(last_candle_timestamp, unit='ms')}) is past target end date ({end_datetime_obj}). Stopping fetch.")
                break

            if len(candles) < limit_per_fetch:
                print(f"Fetched {len(candles)} candles (less than limit {limit_per_fetch}), assuming end of available historical data.")
                break

            current_since = last_candle_timestamp + 1 
            
            time.sleep(exchange_obj.rateLimit / 1000) 

        if not all_candles:
            print(f"No OHLCV data fetched for {symbol} with the given parameters.")
            return pd.DataFrame() 

        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        df = df[~df.index.duplicated(keep='first')]
        df = df.sort_index()

        # Filter based on original start_date_str and end_date_str
        # This is important if over-fetching occurred or to precisely match the requested range.
        if start_date_str:
            # Re-parse start_datetime_obj for robust filtering, in case it wasn't set or was None initially
            start_datetime_obj_filter = pd.to_datetime(start_date_str, errors='coerce') 
            if not pd.isna(start_datetime_obj_filter):
                df = df[df.index >= start_datetime_obj_filter]
        
        if end_date_str and end_datetime_obj: # end_datetime_obj already parsed
            # For OHLCV, usually want to include candles that *start* within the end_date.
            # If end_date_str is '2023-12-31', we typically want data up to '2023-12-31 23:59:59'.
            # pd.to_datetime('2023-12-31') becomes '2023-12-31 00:00:00'.
            # To include the full day, filter up to end of day if no time specified.
            if end_datetime_obj.time() == pd.Timestamp('00:00:00').time():
                # Ensure we compare with a timezone-naive or consistent timezone object if df.index is aware
                df = df[df.index < (end_datetime_obj + pd.Timedelta(days=1)).tz_localize(None) if df.index.tz is not None else end_datetime_obj + pd.Timedelta(days=1)]
            else:
                df = df[df.index <= end_datetime_obj.tz_localize(None) if df.index.tz is not None else end_datetime_obj]


        print(f"Successfully fetched and processed {len(df)} {timeframe} candles for {symbol}.")
        if not df.empty:
            print(f"Data range: {df.index.min()} to {df.index.max()}")
        return df

    except ccxt.NetworkError as e:
        print(f"NETWORK ERROR fetching OHLCV for {symbol}: {e}")
        traceback.print_exc()
        return None
    except ccxt.ExchangeError as e:
        print(f"EXCHANGE ERROR fetching OHLCV for {symbol}: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"UNEXPECTED ERROR fetching OHLCV for {symbol}: {e}")
        traceback.print_exc()
        return None

def execute_trade(exchange_obj, symbol, order_type, side, amount_base_currency_to_trade, current_price, sim_timestamp=None):
    """Places a trade order on the exchange for a specific BASE currency amount.
       Generic function relying on CCXT standardization.

    Args:
        exchange_obj (ccxt.Exchange): Initialized and loaded CCXT exchange object (e.g., ccxt.alpaca).
        symbol (str): The trading symbol (e.g., 'BTC/USD').
        order_type (str): Type of order (e.g., 'market').
        side (str): 'buy' or 'sell'.
        amount_base_currency_to_trade (float): The amount of the base currency to trade.
        current_price (float): The current market price (used for logging and checks).
        sim_timestamp (pd.Timestamp, optional): The simulation timestamp that triggered this trade. Defaults to None.

    Returns:
        dict: The order receipt from CCXT if successful, otherwise None.
    """
    if not exchange_obj:
        print(f"TRADE_ERROR: Exchange object not available.")
        return None

    # Check for API key (required for trading)
    if not hasattr(exchange_obj, 'apiKey') or not exchange_obj.apiKey:
        print(f"TRADE_ERROR: No API key configured. Trading is not possible with public-only access.")
        return None

    # Attempt to load markets if not already loaded
    if not exchange_obj.markets:
        try:
            print("INFO: Markets not loaded in execute_trade, attempting load...")
            exchange_obj.load_markets()
            print("INFO: Markets loaded successfully.")
        except Exception as e_reload:
             print(f"TRADE_ERROR: Failed reloading markets in execute_trade: {e_reload}")
             return None

    if symbol not in exchange_obj.markets:
        print(f"TRADE_ERROR: Symbol '{symbol}' not found in loaded exchange markets.")
        return None

    if current_price <= 0:
        print(f"TRADE_ERROR: Invalid current_price ({current_price}) for order calculation.")
        return None

    market = exchange_obj.markets[symbol]

    try:
        # Precision and limits might differ slightly between exchanges, but CCXT tries to abstract this
        # Fetch necessary precision/limits from the loaded market info
        price_precision_val = market.get('precision', {}).get('price')
        amount_precision_val = market.get('precision', {}).get('amount')
        price_decimals = abs(decimal.Decimal(str(price_precision_val)).as_tuple().exponent) if price_precision_val is not None else 2
        amount_decimals = abs(decimal.Decimal(str(amount_precision_val)).as_tuple().exponent) if amount_precision_val is not None else 5 # Default based on previous code
        min_amount = market.get('limits', {}).get('amount', {}).get('min')
        min_cost = market.get('limits', {}).get('cost', {}).get('min')

        # Use amount_to_precision for formatting
        formatted_amount_base = exchange_obj.amount_to_precision(symbol, amount_base_currency_to_trade)
        formatted_amount_base_float = float(formatted_amount_base)

        print(f"\n--- TRADE ACTION (ATTEMPTING ORDER) ---")
        sim_time_str = f", Sim Time: {sim_timestamp}" if sim_timestamp else ""
        print(f"  Attempt Time: {pd.Timestamp.now()} (PC time){sim_time_str}, Symbol: {symbol}")
        print(f"  Order Type: {order_type}, Side: {side}")
        print(f"  Current Price: {current_price:.{price_decimals}f} {market.get('quote', 'QUOTE')}")
        print(f"  Formatted Base Amount: {formatted_amount_base} {market.get('base', 'BASE')}")
        # Print limits if available
        if min_amount: print(f"  Min Amount: {min_amount}")
        if min_cost: print(f"  Min Cost: {min_cost} {market.get('quote', 'QUOTE')}") # Cost is usually in quote currency

        # Pre-check basic conditions
        if min_amount is not None and formatted_amount_base_float < min_amount:
             print(f"TRADE_ERROR: Calculated amount {formatted_amount_base_float:.{amount_decimals}f} {market.get('base', 'BASE')} is below minimum {min_amount:.{amount_decimals}f}.")
             time.sleep(1) # Add delay even for pre-check failure
             return None
        estimated_cost = formatted_amount_base_float * current_price
        if min_cost is not None and estimated_cost < min_cost:
             print(f"TRADE_ERROR: Estimated cost {estimated_cost:.{price_decimals}f} {market.get('quote', 'QUOTE')} is below minimum cost {min_cost:.{price_decimals}f}.")
             time.sleep(1) # Add delay even for pre-check failure
             return None


        order = None
        if order_type.lower() == 'market':
            print(f"  PLACING ORDER: exchange.create_market_{side}_order('{symbol}', {formatted_amount_base_float})")
            if side.lower() == 'buy':
                 order = exchange_obj.create_market_buy_order(symbol, formatted_amount_base_float)
            elif side.lower() == 'sell':
                 order = exchange_obj.create_market_sell_order(symbol, formatted_amount_base_float)
            else:
                raise ValueError(f"Invalid order side: {side}")
        else:
            # TODO: Implement other order types if needed (e.g., limit)
            print(f"TRADE_ERROR: Unsupported order type '{order_type}'. Only 'market' implemented.")
            time.sleep(1) # Add delay even for unsupported type error
            return None

        print(f"  SUCCESS: Order placed: ID {order.get('id', 'N/A')}, Status {order.get('status', 'N/A')}")
        print(f"-------------------------------------")
        time.sleep(1) # Add delay after successful trade
        return order

    except ccxt.InsufficientFunds as e:
        print(f"  TRADE_ERROR (InsufficientFunds): {e}")
        print(f"  Ensure your account for {market.get('quote', 'QUOTE')} or {market.get('base', 'BASE')} has enough balance.")
    except ccxt.NetworkError as e:
        print(f"  TRADE_ERROR (NetworkError): {e}")
    except ccxt.ExchangeError as e: # Catch broader exchange errors
        print(f"  TRADE_ERROR (ExchangeError): {e}")
    except ValueError as e: # Catch the invalid side error
         print(f"  TRADE_ERROR (Input): {e}")
    except Exception as e:
        print(f"  TRADE_ERROR (Unexpected): An unexpected error occurred: {e}")

    print(f"-------------------------------------")
    time.sleep(1) # Add delay after failed trade attempt
    return None


def fetch_and_print_recent_trades(exchange_obj, symbol, limit=50):
    """Fetches and prints the recent trade history for the given symbol using CCXT."""
    print(f"\n--- Fetching Recent Trade History ({limit} trades) --- ")
    if not exchange_obj:
        print("ERROR: Exchange object not provided.")
        return

    try:
        print(f"Fetching last {limit} trades for {symbol}...")
        # Ensure markets are loaded
        if not exchange_obj.markets:
             print("Markets not loaded, attempting to load...")
             exchange_obj.load_markets()
        elif symbol not in exchange_obj.markets:
             print(f"Symbol {symbol} not found in loaded markets, reloading...")
             exchange_obj.load_markets(reload=True)

        if symbol not in exchange_obj.markets:
             print(f"ERROR: Symbol {symbol} not found in exchange markets even after load attempt.")
             return

        # Check if fetchMyTrades is supported
        if not exchange_obj.has['fetchMyTrades']:
            print(f"ERROR: The exchange '{exchange_obj.id}' does not support fetchMyTrades via CCXT.")
            return

        my_trades = exchange_obj.fetch_my_trades(symbol=symbol, limit=limit)

        if my_trades:
            print(f"Found {len(my_trades)} recent trades:")
            my_trades.sort(key=lambda x: x['timestamp'], reverse=True)
            market_info = exchange_obj.markets[symbol]
            # Use market info for precision where possible
            quote_precision_val = market_info.get('precision', {}).get('quote')
            amount_precision_val = market_info.get('precision', {}).get('amount')
            price_precision_val = market_info.get('precision', {}).get('price')
            quote_decimals = abs(decimal.Decimal(str(quote_precision_val)).as_tuple().exponent) if quote_precision_val is not None else 2
            amount_decimals = abs(decimal.Decimal(str(amount_precision_val)).as_tuple().exponent) if amount_precision_val is not None else 5
            price_decimals = abs(decimal.Decimal(str(price_precision_val)).as_tuple().exponent) if price_precision_val is not None else 2

            for trade in my_trades:
                trade_id = trade.get('id', 'N/A')
                dt = pd.to_datetime(trade.get('timestamp'), unit='ms') if trade.get('timestamp') else 'N/A'
                side = trade.get('side', 'N/A')
                price = trade.get('price')
                amount = trade.get('amount')
                cost = trade.get('cost')
                fee = trade.get('fee', {})
                fee_cost = fee.get('cost') if fee else None
                fee_currency = fee.get('currency', '???') if fee else '???'
                # Format outputs using fetched precision
                price_str = f"{price:.{price_decimals}f}" if price is not None else "N/A"
                cost_str = f"{cost:.{quote_decimals}f}" if cost is not None else "N/A"
                amount_str = f"{amount:.{amount_decimals}f}" if amount is not None else "N/A"
                fee_cost_str = f"{fee_cost:.{quote_decimals+2}f}" if fee_cost is not None else "N/A" # Fee might have higher precision

                print(f"  ID: {trade_id}, Time: {dt}, Side: {side}, "
                      f"Amount: {amount_str}, Price: {price_str}, Cost: {cost_str}, "
                      f"Fee: {fee_cost_str} {fee_currency}")
        else:
            print(f"No recent trades found for {symbol} with the provided API keys.")

    except ccxt.AuthenticationError:
        print("Error fetching trades: AuthenticationError. Check your API keys.")
    except ccxt.NetworkError as e_net:
        print(f"Error fetching trades: NetworkError - {e_net}")
    except ccxt.ExchangeError as e_exc:
        print(f"Error fetching trades: ExchangeError - {e_exc}")
    except Exception as e_fetch:
        print(f"An unexpected error occurred while fetching trades: {e_fetch}")
    print("----------------------------------------------") 

def get_usdt_balance(exchange_obj, account_type_preference=['SPOT', 'UNIFIED']):
    """
    Fetches the available USDT balance from the exchange object.
    Prioritizes specified account types for Bybit UTA.

    Args:
        exchange_obj (ccxt.Exchange): Initialized CCXT exchange object.
        account_type_preference (list): Preferred account types for Bybit (e.g., ['SPOT', 'UNIFIED']).

    Returns:
        float: Available USDT balance, or 0.0 if not found or error.
    """
    if not exchange_obj:
        print("ERROR (get_usdt_balance): Exchange object not provided.")
        return 0.0
    try:
        balance_data = exchange_obj.fetch_balance()
        
        usdt_balance = 0.0

        if exchange_obj.id == 'bybit':
            # For Bybit, handle potential Unified Trading Account (UTA) structure
            raw_info = balance_data.get('info', {})
            if isinstance(raw_info.get('result'), dict) and isinstance(raw_info['result'].get('list'), list):
                uta_list = raw_info['result']['list']
                found_preferred_account = False
                for acc_type in account_type_preference:
                    for account_details in uta_list:
                        if account_details.get('accountType') == acc_type:
                            coins = account_details.get('coin', [])
                            for coin_data in coins:
                                if coin_data.get('coin') == 'USDT':
                                    # 'availableToWithdraw' or 'walletBalance' can be used. 
                                    # 'walletBalance' might be total, 'availableToWithdraw' is safer for trading.
                                    # Let's try 'availableToWithdraw' first, fallback to 'walletBalance'
                                    balance_str = coin_data.get('availableToWithdraw') 
                                    if balance_str is None: # Fallback if 'availableToWithdraw' isn't there
                                        balance_str = coin_data.get('walletBalance')
                                    
                                    if balance_str is not None:
                                        usdt_balance = float(balance_str)
                                        print(f"INFO (get_usdt_balance): Found USDT balance ({usdt_balance}) in Bybit account type: {acc_type}")
                                        found_preferred_account = True
                                        break
                            if found_preferred_account:
                                break
                    if found_preferred_account:
                        break
                if not found_preferred_account:
                     print(f"WARN (get_usdt_balance): USDT not found in preferred Bybit account types: {account_type_preference}. Checking CCXT 'free' balance.")
            
            if usdt_balance == 0.0 and 'USDT' in balance_data.get('free', {}): # Fallback to CCXT's parsed 'free' balance
                usdt_balance = float(balance_data['free']['USDT'])
                print(f"INFO (get_usdt_balance): Found USDT balance ({usdt_balance}) via CCXT 'free' field for Bybit.")

        elif 'USDT' in balance_data.get('free', {}): # For other exchanges like Alpaca (or as general fallback)
            usdt_balance = float(balance_data['free']['USDT'])
            print(f"INFO (get_usdt_balance): Found USDT balance ({usdt_balance}) via CCXT 'free' field for {exchange_obj.id}.")
        else:
            print(f"WARN (get_usdt_balance): Could not find USDT in 'free' balances for {exchange_obj.id}.")
            # Check 'total' as a last resort, though 'free' is preferred for trading
            if 'USDT' in balance_data.get('total', {}):
                usdt_total = float(balance_data['total']['USDT'])
                print(f"INFO (get_usdt_balance): Found USDT in 'total' balance ({usdt_total}), but 'free' is preferred. Using 0.0 as fallback for available.")


        return usdt_balance

    except Exception as e:
        print(f"ERROR (get_usdt_balance): Could not fetch or parse USDT balance: {e}")
        traceback.print_exc()
        return 0.0 