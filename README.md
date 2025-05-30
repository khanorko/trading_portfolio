# 🤖 Cryptocurrency Trading Bot

A sophisticated algorithmic trading bot with Ichimoku and RSI Reversal strategies, featuring real-time dashboard monitoring and state persistence.

## ⚠️ **IMPORTANT SECURITY NOTICE** ⚠️

**NEVER commit API keys or sensitive data to GitHub!**

This repository is configured to exclude all sensitive files. Always use environment variables for API keys.

## 🚀 **Quick Start**

### 1. **Clone Repository**
```bash
git clone https://github.com/yourusername/trading_portfolio.git
cd trading_portfolio
```

### 2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3. **Configure Environment**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual API keys
nano .env
```

### 4. **Set Up API Keys**
- Get testnet API keys from [Bybit Testnet](https://testnet.bybit.com)
- Add them to your `.env` file
- **NEVER** commit the `.env` file to git

### 5. **Run Paper Trading**
```bash
# Start the trading bot (paper trading)
python start_live_bot.py

# In another terminal, start the dashboard
streamlit run trading_dashboard.py
```

## 📊 **Features**

- **Dual Strategy System**: Ichimoku Trend + RSI Reversal
- **Real-time Dashboard**: Streamlit-based monitoring interface
- **State Persistence**: Survives restarts and crashes
- **Paper Trading**: Safe testing with virtual money
- **Risk Management**: Position sizing and stop losses
- **Realistic Costs**: Trading fees and slippage simulation

## 🔐 **Security Best Practices**

### **Environment Variables**
All sensitive configuration is handled via environment variables:

```bash
BYBIT_API_KEY=your_testnet_api_key
BYBIT_API_SECRET=your_testnet_api_secret
BYBIT_TESTNET=true
INITIAL_CAPITAL=4000
```

### **Files Excluded from Git**
- `.env` files (API keys)
- `*.db` files (trading history)
- `*.log` files (may contain API responses)
- `bot_state.json` (position data)
- `*.csv` files (trading data)

## 🚀 **Railway Deployment**

### **Prerequisites**
1. GitHub account
2. Railway account
3. Bybit testnet API keys

### **Deployment Steps**
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Initialize project
railway init

# 4. Set environment variables
railway variables set BYBIT_API_KEY=your_testnet_key
railway variables set BYBIT_API_SECRET=your_testnet_secret
railway variables set BYBIT_TESTNET=true
railway variables set INITIAL_CAPITAL=4000

# 5. Deploy
railway up
```

## 📈 **Performance**

### **Backtest Results (2021-2023)**
- **Total Return**: 55.61%
- **Final Equity**: $6,224.49 (from $4,000)
- **Max Drawdown**: ~15%
- **Sharpe Ratio**: TBD

### **Strategy Breakdown**
- **Ichimoku Strategy**: Trend-following using cloud breakouts
- **RSI Reversal**: Mean-reversion using oversold/overbought levels
- **Risk Management**: 1.5% risk per trade based on ATR

## 🛡️ **Risk Management**

### **Built-in Safety Features**
- Position sizing based on account balance
- Stop losses using ATR
- Daily loss limits
- Maximum open positions limit
- Emergency stop functionality

### **Paper Trading First**
**ALWAYS test with paper trading before going live:**
1. Run for at least 1-2 weeks
2. Verify all functions work correctly
3. Monitor performance and stability
4. Only then consider live trading with small amounts

## 📊 **Dashboard Features**

Access the dashboard at `http://localhost:8501` (local) or your Railway URL:

- **Real-time Metrics**: Equity, P&L, win rate
- **Interactive Charts**: Equity curve, drawdown analysis
- **Trade History**: Detailed trade log with filtering
- **System Health**: Bot status and error monitoring
- **Performance Analytics**: Strategy breakdown and statistics

## 🔧 **Configuration**

### **Trading Parameters**
```json
{
    "initial_capital": 4000,
    "risk_per_trade": 0.015,
    "max_open_positions": 3,
    "trading_fee_rate": 0.001,
    "slippage_rate": 0.0005
}
```

### **Strategy Allocation**
```json
{
    "allocations": {
        "ICHIMOKU": 0.9,
        "REVERSAL": 0.1
    }
}
```

## 🚨 **Important Warnings**

1. **Start Small**: Even in live trading, start with amounts you can afford to lose
2. **Monitor Closely**: Watch the bot especially in the first days/weeks
3. **Have Backups**: Always have manual override capabilities
4. **Stay Updated**: Keep dependencies and strategies updated
5. **Risk Management**: Never risk more than you can afford to lose

## 📞 **Support**

- Check logs: `railway logs` or local log files
- Monitor dashboard for system health
- Review trade history for performance analysis

## 📄 **License**

This project is for educational purposes. Use at your own risk.

---

**⚠️ Trading cryptocurrencies involves substantial risk of loss and is not suitable for every investor.** 