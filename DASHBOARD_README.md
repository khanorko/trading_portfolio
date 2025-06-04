# 🤖 Trading Bot Dashboard

Professional real-time monitoring dashboard for your algorithmic trading bot.

## ✨ Features

- **📊 Real-time Portfolio Monitoring** - Live equity curve, P&L tracking
- **📈 Performance Analytics** - Win rate, profit factor, drawdown analysis  
- **🎯 Strategy Breakdown** - Individual strategy performance comparison
- **🔄 Trade History** - Detailed trade logs with filtering
- **⚙️ System Health** - Bot status, API connectivity, error monitoring
- **📱 Auto-refresh** - Configurable real-time updates (15s-2min)
- **💾 Persistent Storage** - SQLite database for historical data

## 🚀 Quick Start (Recommended)

### Option 1: Automated Setup
```bash
cd trading_portfolio  # Navigate to your project directory
python quick_start.py
```

This will:
1. ✅ Check dependencies
2. 📦 Install required packages
3. 🧪 Create sample data (optional)
4. 🚀 Launch dashboard automatically

### Option 2: Manual Setup
```bash
# Install dependencies
pip install streamlit plotly pandas numpy

# Create sample data for testing
python dashboard_integration.py

# Launch dashboard
streamlit run trading_dashboard.py
```

## 📱 Access Your Dashboard

Once running, open your browser to:
**http://localhost:8501**

## 🔧 Integration with Your Trading Bot

### For Live Trading Bot
Add this to your `live_trading_bot.py`:

```python
# In __init__ method
from dashboard_integration import DashboardIntegration
self.dashboard = DashboardIntegration()
self.dashboard.integrate_with_live_bot(self)
```

### For Backtest Results  
Add this to your `run_portfolio.py`:

```python
# After backtest completion
from dashboard_integration import DashboardIntegration
dashboard = DashboardIntegration()
dashboard.log_backtest_results(equity, trades_log)
```

## 📊 Dashboard Sections

### 1. **Key Metrics Row**
- 💰 Total Equity with daily change
- 📈 Total Return percentage
- 🎯 Win Rate
- 📊 Open Positions
- 🔢 Total Trades

### 2. **Performance Metrics**
- Profit Factor
- Maximum Drawdown
- Daily P&L
- Unrealized P&L

### 3. **Interactive Charts**
- Portfolio equity curve (total + strategies)
- Drawdown analysis
- P&L distribution histogram

### 4. **Strategy Analysis**
- Individual strategy performance
- Trade count and average P&L
- Win rate by strategy

### 5. **Recent Activity**
- Last 20 trades with details
- Color-coded P&L (green/red)
- Paper vs live trade indicators

### 6. **System Health**
- Bot online/offline status
- Last update timestamp
- API connection status
- Database statistics

## ⚙️ Configuration Options

### Auto-refresh Settings
- ✅ Enable/disable auto-refresh
- ⏱️ Refresh intervals: 15s, 30s, 1min, 2min

### Time Range Filters
- Last 24 Hours
- Last 7 Days  
- Last 30 Days
- All Time

## 🗄️ Data Storage

Dashboard uses SQLite database (`trading_dashboard.db`) with tables:
- **trades** - Individual trade records
- **equity_snapshots** - Portfolio value over time  
- **performance_metrics** - Calculated performance stats
- **system_health** - Bot status and health checks

## 📁 File Structure

```
trading_portfolio/
├── trading_dashboard.py          # Main dashboard app
├── enhanced_state_manager.py     # Enhanced logging system
├── dashboard_integration.py      # Integration helpers  
├── quick_start.py               # Automated setup script
├── dashboard_requirements.txt    # Python dependencies
└── trading_dashboard.db         # SQLite database (created automatically)
```

## 🛠️ Advanced Features

### Custom Notifications (Optional)
Set up email/Discord alerts for trades:

```python
from dashboard_integration import NotificationSystem

notifications = NotificationSystem({
    'email': {
        'from': 'your-email@gmail.com',
        'to': 'alerts@yourphone.com',
        'password': 'your-app-password',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587
    }
})
```

### Performance Monitoring
Dashboard automatically calculates:
- Sharpe Ratio (approximate)
- Maximum Drawdown
- Profit Factor
- Win Rate by Strategy
- Risk-adjusted Returns

## 🔧 Troubleshooting

### Dashboard Won't Start
```bash
# Check Streamlit installation
pip install --upgrade streamlit

# Check if port 8501 is available
netstat -an | grep 8501

# Run on different port
streamlit run trading_dashboard.py --server.port 8502
```

### No Data Showing
1. ✅ Make sure your bot is integrated with `DashboardIntegration`
2. 🧪 Run sample data: `python dashboard_integration.py`
3. 📊 Check database: Look for `trading_dashboard.db` file

### Performance Issues
- Reduce auto-refresh frequency
- Limit data retention (modify database queries)
- Use shorter time ranges

## 📊 Sample Data

For testing, run:
```bash
python dashboard_integration.py
# Select option 1 or 3 to create sample data
```

This creates:
- 50 realistic trades over 30 days
- Hourly equity snapshots
- Performance metrics
- System health records

## 🔮 Future Enhancements

Planned features:
- 📧 Email/SMS notifications
- 📱 Mobile-responsive design  
- 🔍 Advanced filtering and search
- 📊 Additional chart types
- 🤖 AI-powered insights
- ☁️ Cloud deployment options

## 💡 Tips

1. **Regular Monitoring**: Check dashboard daily for system health
2. **Performance Review**: Weekly analysis of strategy performance  
3. **Risk Management**: Monitor drawdown and position sizing
4. **System Alerts**: Set up notifications for critical events
5. **Data Backup**: Regularly backup `trading_dashboard.db`

## 🆘 Support

If you encounter issues:

1. **Check Requirements**: Python 3.8+, all dependencies installed
2. **Verify Integration**: Ensure bot is logging data properly
3. **Sample Data**: Test with sample data first
4. **Log Files**: Check Streamlit logs for error messages
5. **Database**: Verify `trading_dashboard.db` exists and has data

## 🎯 Next Steps

1. 🚀 **Launch Dashboard**: Run `python quick_start.py`
2. 🔗 **Integrate Bot**: Add dashboard logging to your trading bot
3. 📊 **Monitor Performance**: Use dashboard for daily monitoring
4. 📈 **Optimize Strategy**: Use insights to improve trading performance

---

**Happy Trading! 🚀📈**

*Professional algorithmic trading dashboard built with Streamlit and Plotly*