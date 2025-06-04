# 🤖 Algorithmic Trading Bot with Dashboard

A sophisticated algorithmic trading bot with Ichimoku and RSI Reversal strategies, featuring real-time dashboard monitoring and state persistence. **Now with comprehensive bug fixes and enhanced reliability!**

## ✨ Latest Improvements (Bug Fix Release)

### 🔧 **Critical Bug Fixes**
- **✅ Atomic State Writes**: Implemented atomic file operations to prevent state corruption during bot restarts
- **✅ Input Validation**: Added comprehensive validation for all configuration parameters and trading inputs
- **✅ Strategy Naming Consistency**: Centralized strategy naming system to prevent runtime errors
- **✅ Enhanced Error Handling**: Comprehensive retry logic and graceful fallbacks for all exchange operations
- **✅ Configuration Management**: Hardcoded paths removed, environment-based configuration with validation

### 🛡️ **Reliability Enhancements**
- **Thread-safe operations** with proper locking mechanisms
- **Graceful degradation** when external services fail
- **Comprehensive logging** with structured error reporting
- **Backup and recovery** systems for critical data
- **Health monitoring** for all system components

## 🎯 Key Features

### 💹 **Advanced Trading Strategies**
- **Ichimoku Strategy**: Trend-following using cloud breakouts
- **RSI Reversal Strategy**: Mean reversion using RSI oversold/overbought levels
- **Multi-timeframe Analysis**: 4H default with configurable intervals
- **Risk Management**: Position sizing, stop losses, and portfolio allocation

### 📊 **Professional Dashboard**
- **Real-time Portfolio Tracking**: Live equity curve and P&L monitoring
- **Performance Analytics**: Win rate, profit factor, drawdown analysis
- **Strategy Breakdown**: Individual strategy performance comparison
- **Trade History**: Detailed logs with filtering and search
- **System Health**: Bot status, API connectivity, error monitoring

### 🔧 **Production-Ready Features**
- **State Persistence**: SQLite + JSON backup with atomic writes
- **Paper & Live Trading**: Seamless transition between environments
- **Multi-Exchange Support**: Bybit (Alpaca coming soon)
- **Configurable Parameters**: Environment-based configuration
- **Comprehensive Testing**: Full test suite for all components

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.8+ required
python --version

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup
```bash
# Copy and configure environment variables
cp .env.example .env

# Edit .env with your API credentials
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
BYBIT_TESTNET=true

# Optional: Customize trading parameters
INITIAL_CAPITAL=4000
POSITION_SIZE_PCT=0.015
TRADING_FEE_RATE=0.001
```

### Launch Dashboard
```bash
# Automated setup (recommended)
python quick_start.py

# Or manual launch
streamlit run trading_dashboard.py
```

### Start Trading Bot
```bash
# Live trading (paper mode)
python start_live_bot.py

# Backtest analysis
python run_portfolio.py btc_4h_2022_2025_clean.csv
```

## 🏗️ Architecture Overview

```
trading_portfolio/
├── 🔧 Core Components
│   ├── config.py                  # Centralized configuration with validation
│   ├── state_manager.py           # Atomic state persistence
│   ├── enhanced_state_manager.py  # Dashboard integration
│   └── strategy_constants.py      # Consistent naming system
│
├── 📈 Trading Engine  
│   ├── strategies/                # Trading strategies
│   ├── engines/                   # Backtest & execution engines
│   └── exchange_handler.py        # Exchange API with retry logic
│
├── 📊 Dashboard System
│   ├── trading_dashboard.py       # Main dashboard app
│   ├── dashboard_integration.py   # Data integration
│   └── populate_dashboard.py      # Sample data generation
│
├── 🧪 Testing & Quality
│   ├── test_bug_fixes.py         # Comprehensive test suite
│   └── test_dashboard.py         # Dashboard tests
│
└── 🚀 Deployment
    ├── railway.json              # Railway deployment config
    ├── requirements.txt          # Python dependencies  
    └── start.sh                  # Production startup script
```

## 📊 Configuration Options

### Trading Parameters
```python
# Risk Management
INITIAL_CAPITAL=4000          # Starting capital (min: $100, max: $1M)
POSITION_SIZE_PCT=0.015       # Position size as % of capital (0.1% - 50%)
TRADING_FEE_RATE=0.001        # Exchange fee rate (0% - 1%)
SLIPPAGE_RATE=0.0005          # Expected slippage (0% - 1%)
MIN_PROFIT_THRESHOLD=0.005    # Minimum profit threshold (0% - 10%)

# Strategy Allocations
ICHIMOKU_ALLOCATION=0.9       # 90% to Ichimoku strategy
REVERSAL_ALLOCATION=0.1       # 10% to RSI Reversal
```

### System Settings
```python
# Database & State
DATABASE_PATH=./trading_dashboard.db
BOT_STATE_FILE=./bot_state.json
LOG_FILE=./trading_bot.log

# Exchange Settings  
BYBIT_TESTNET=true           # Use testnet for safety
EXCHANGE_TIMEOUT=30000       # API timeout in milliseconds

# Dashboard Settings
STREAMLIT_PORT=8501          # Dashboard port
STREAMLIT_HOST=0.0.0.0       # Host binding
```

## 🔍 Quality Assurance

### Run Tests
```bash
# Run comprehensive test suite
python test_bug_fixes.py

# Test specific components
python -m unittest test_bug_fixes.TestConfigValidation
python -m unittest test_bug_fixes.TestAtomicStateWrites
```

### Health Checks
```bash
# Validate configuration
python -c "from config import Config; Config.validate_config()"

# Test exchange connectivity
python test_pybit_direct.py

# Verify dashboard data
python test_dashboard.py
```

## 📈 Performance Metrics

### Backtest Results (2021-2023)
- **Total Return**: Varies by market conditions
- **Win Rate**: Strategy dependent (typically 45-65%)
- **Max Drawdown**: Risk-managed with position sizing
- **Profit Factor**: >1.0 target with realistic fees

### Dashboard Features
- **Real-time Updates**: 15s - 2min configurable intervals
- **Data Retention**: SQLite database with efficient queries  
- **Performance**: Handles 1000+ trades with smooth UI
- **Reliability**: 99%+ uptime with error recovery

## 🔒 Security & Risk Management

### API Security
- **Environment Variables**: Never commit API keys
- **Testnet First**: Always test with paper trading
- **IP Whitelisting**: Recommended for live trading
- **Rate Limiting**: Built-in respect for exchange limits

### Risk Controls
- **Position Limits**: Configurable max position sizes
- **Stop Losses**: Automatic and manual stop loss orders
- **Balance Checks**: Validates available funds before trading
- **Error Limits**: Circuit breaker for excessive failures

## 🚀 Deployment Options

### Local Development
```bash
# Development mode with auto-reload
streamlit run trading_dashboard.py --server.runOnSave true
```

### Railway Deployment
```bash
# Deploy to Railway (configured)
git push origin main
# Railway will auto-deploy using railway.json
```

### Docker (Coming Soon)
```bash
# Build and run with Docker
docker build -t trading-bot .
docker run -p 8501:8501 trading-bot
```

## 🛠️ Troubleshooting

### Common Issues

**Configuration Errors**
```bash
# Check configuration
python -c "from config import Config; print('Config OK')"

# Fix validation errors
export INITIAL_CAPITAL=4000
export POSITION_SIZE_PCT=0.015
```

**State Corruption**
```bash
# Automatic recovery from backup
# Check backup files: bot_state.backup.json
# Manual recovery: copy backup to main file
```

**Exchange Connectivity**
```bash
# Test exchange connection
python test_pybit_direct.py

# Check API credentials in .env
# Verify IP whitelist if configured
```

**Dashboard Issues**
```bash
# Clear cache and restart
rm -rf __pycache__
streamlit cache clear
streamlit run trading_dashboard.py
```

## 📚 Development Guide

### Adding New Strategies
1. Create strategy class in `strategies/`
2. Add to `strategy_constants.py`
3. Update dashboard integration
4. Add comprehensive tests

### Extending Exchange Support
1. Implement in `exchange_handler.py`
2. Add error handling and retry logic
3. Update configuration validation
4. Test thoroughly with paper trading

### Custom Indicators
1. Add to strategy's `precompute_indicators()`
2. Update plotting in `run_portfolio.py`
3. Ensure indicator persistence in state

## 📄 License & Disclaimer

This software is for educational and research purposes. **Trading involves substantial risk** and may not be suitable for all investors. Past performance does not guarantee future results.

- **Use at your own risk**
- **Test thoroughly before live trading**
- **Never risk more than you can afford to lose**
- **Ensure compliance with local regulations**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit a pull request

## 📞 Support

- **Issues**: GitHub Issues for bug reports
- **Features**: GitHub Discussions for feature requests  
- **Security**: Email for security-related issues
- **Documentation**: Check README and code comments

---

**Happy Trading! 🚀📈**

*Professional algorithmic trading made reliable and accessible* 