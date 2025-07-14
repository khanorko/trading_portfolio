# 🚀 Binance Paper Trading Setup

This guide will help you set up paper trading with Binance instead of Bybit to avoid geographic restrictions.

## Why Switch to Binance?

- ✅ **Better Global Access**: Binance testnet is accessible from more regions
- ✅ **Free Paper Trading**: No real money required
- ✅ **Same Features**: All trading strategies work the same way
- ✅ **Easy Setup**: Simple API key generation

## Quick Setup

### 1. Get Binance Testnet API Keys

1. Go to **https://testnet.binance.vision/**
2. Sign up for a free testnet account
3. Navigate to **API Management**
4. Click **Create API** and generate new keys
5. **Important**: Enable "Spot & Margin Trading" permissions
6. Copy your API Key and Secret Key

### 2. Run the Setup Script

```bash
python setup_binance.py
```

This script will:
- Guide you through entering your API keys
- Save them securely to `.env` file
- Test the connection
- Configure the bot to use Binance

### 3. Start Paper Trading

```bash
python live_trading_bot.py
```

The bot will now connect to Binance testnet instead of Bybit!

## Manual Setup (Alternative)

If you prefer to set up manually, create/update your `.env` file:

```env
# Binance Configuration
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_key_here
BINANCE_TESTNET=true
EXCHANGE_NAME=binance
```

## Verification

After setup, you should see:
```
INFO:exchange_handler:Initializing BINANCE exchange connection...
INFO:exchange_handler:Using Binance Testnet
INFO:exchange_handler:✅ Binance connection successful! Balance: $10000.00
```

## Trading Features

All existing features work with Binance:
- ✅ Ichimoku + RSI strategies
- ✅ Real-time price data
- ✅ Paper trading with testnet funds
- ✅ Dashboard integration
- ✅ Trade logging and analytics

## Troubleshooting

### Connection Issues
- Verify your API keys are correct
- Check that "Spot & Margin Trading" is enabled
- Ensure you're using testnet keys (not mainnet)

### Geographic Blocking
If you still get blocked:
- Try using a VPN
- Contact Binance support
- Consider using simulation mode as fallback

## Switch Back to Bybit

To switch back to Bybit later:
```bash
# In your .env file
EXCHANGE_NAME=bybit
```

## Need Help?

- Check the logs for detailed error messages
- Run `python setup_binance.py` again to test connection
- Verify your API permissions on Binance testnet 