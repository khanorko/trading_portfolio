"""
Real-Time Trading Bot Dashboard using Streamlit
Professional monitoring interface for algorithmic trading bot
"""
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import time
import numpy as np
from pathlib import Path
import os

# Import configuration
from config import Config, DATABASE_PATH

# Configure Streamlit page
st.set_page_config(
    page_title="🤖 Trading Bot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .positive { color: #00C851; font-weight: bold; }
    .negative { color: #ff4444; font-weight: bold; }
    .neutral { color: #33b5e5; font-weight: bold; }
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_database_data():
    """Load data from SQLite database with enhanced error handling"""
    try:
        if not os.path.exists(DATABASE_PATH):
            st.error(f"Database not found at {DATABASE_PATH}")
            return {'trades': pd.DataFrame(), 'equity': pd.DataFrame(), 'health': pd.DataFrame()}
        
        conn = sqlite3.connect(DATABASE_PATH)
        
        # Load trades
        trades_query = """
        SELECT * FROM trades 
        ORDER BY timestamp DESC
        """
        trades_df = pd.read_sql_query(trades_query, conn)
        
        # Load equity snapshots
        equity_query = """
        SELECT * FROM equity_snapshots 
        ORDER BY timestamp DESC
        LIMIT 1000
        """
        equity_df = pd.read_sql_query(equity_query, conn)
        
        # Load system health (if table exists)
        health_df = pd.DataFrame()
        try:
            health_query = """
            SELECT * FROM system_health 
            ORDER BY timestamp DESC 
            LIMIT 10
            """
            health_df = pd.read_sql_query(health_query, conn)
        except:
            pass  # Table might not exist yet
        
        conn.close()
        
        # Auto-generate demo data if no trades exist and we have very little equity data
        if trades_df.empty and len(equity_df) < 10:
            st.info("🎯 No trading data found. Generating demo data for dashboard demonstration...")
            generate_demo_data_automatically()
            
            # Reload data after generating demo data
            conn = sqlite3.connect(DATABASE_PATH)
            trades_df = pd.read_sql_query(trades_query, conn)
            equity_df = pd.read_sql_query(equity_query, conn)
            conn.close()
        
        return {
            'trades': trades_df,
            'equity': equity_df,
            'health': health_df
        }
        
    except Exception as e:
        st.error(f"Error loading database: {e}")
        return {'trades': pd.DataFrame(), 'equity': pd.DataFrame(), 'health': pd.DataFrame()}

def generate_demo_data_automatically():
    """Generate demo data automatically for dashboard demonstration"""
    try:
        from enhanced_state_manager import DashboardStateManager
        import random
        from datetime import datetime, timedelta
        
        dashboard = DashboardStateManager()
        
        # Generate demo trades over the last 7 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        # Create realistic trade scenarios
        current_time = start_time
        trade_id = 1
        
        strategies = ["IchimokuTrend", "RsiReversal"]
        base_price = 95000.0
        
        while current_time < end_time and trade_id <= 15:  # Limit to 15 trades
            # Generate 1-2 trades per day on average
            if random.random() < 0.25:  # 25% chance of trade each 4-hour period
                strategy = random.choice(strategies)
                
                # Generate entry trade
                entry_price = base_price + random.uniform(-2000, 2000)
                quantity = random.uniform(0.01, 0.05)  # 0.01 to 0.05 BTC
                
                entry_trade = {
                    'symbol': 'BTC/USDT',
                    'strategy': strategy,
                    'side': 'buy',
                    'quantity': quantity,
                    'price': entry_price,
                    'timestamp': current_time.isoformat(),
                    'position_id': f'demo_pos_{trade_id}'
                }
                
                # Log entry trade
                dashboard.log_trade(entry_trade)
                
                # Generate exit trade 4-24 hours later
                exit_time = current_time + timedelta(hours=random.uniform(4, 24))
                if exit_time < end_time:
                    # Generate realistic P&L
                    price_change_pct = random.uniform(-0.05, 0.08)  # -5% to +8%
                    exit_price = entry_price * (1 + price_change_pct)
                    pnl = (exit_price - entry_price) * quantity
                    
                    exit_trade = {
                        'symbol': 'BTC/USDT',
                        'strategy': strategy,
                        'side': 'sell',
                        'quantity': quantity,
                        'price': exit_price,
                        'timestamp': exit_time.isoformat(),
                        'position_id': f'demo_pos_{trade_id}',
                        'pnl': pnl
                    }
                    
                    # Log exit trade
                    dashboard.log_trade(exit_trade)
                    trade_id += 1
            
            current_time += timedelta(hours=4)
        
        # Generate equity snapshots
        snapshot_time = start_time
        current_equity = 4000.0
        
        while snapshot_time < end_time:
            # Add some random equity fluctuation
            daily_change = random.uniform(-0.02, 0.03)  # -2% to +3% daily
            current_equity *= (1 + daily_change/6)  # 4-hour change
            
            # Create equity snapshot
            equity_data = {
                'timestamp': snapshot_time.isoformat(),
                'total_equity': current_equity,
                'ichimoku_equity': current_equity * 0.9,  # 90% allocation
                'reversal_equity': current_equity * 0.1,  # 10% allocation
                'open_positions': random.randint(0, 2),
                'unrealized_pnl': random.uniform(-100, 200),
                'daily_pnl': random.uniform(-50, 100)
            }
            
            dashboard.log_equity_snapshot_direct(equity_data)
            snapshot_time += timedelta(hours=4)
        
        st.success(f"✅ Generated demo trading data with {trade_id-1} completed trades")
        
    except Exception as e:
        st.error(f"Failed to generate demo data: {e}")
        st.info("Dashboard will show live data as it becomes available from the trading bot.")

def calculate_metrics(data):
    """Calculate key performance metrics"""
    if data['equity'].empty:
        return {
            'total_equity': 0,
            'daily_pnl': 0,
            'total_return': 0,
            'open_positions': 0,
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0
        }
    
    # Latest equity data
    latest_equity = data['equity'].iloc[0] if not data['equity'].empty else {}
    
    # Trade statistics (handle empty trades gracefully)
    if not data['trades'].empty:
        completed_trades = data['trades'][data['trades']['action'] == 'SELL']
        total_trades = len(completed_trades)
        winning_trades = len(completed_trades[completed_trades['pnl'] > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Profit factor
        gross_profit = completed_trades[completed_trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(completed_trades[completed_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    else:
        # No trades data available
        total_trades = 0
        win_rate = 0
        profit_factor = 0
    
    # Max drawdown calculation
    if not data['equity'].empty:
        equity_values = data['equity']['total_equity'].values[::-1]  # Reverse for chronological order
        cummax = np.maximum.accumulate(equity_values)
        drawdown = (cummax - equity_values) / cummax
        max_drawdown = np.max(drawdown) * 100
    else:
        max_drawdown = 0
    
    # Total return
    if not data['equity'].empty and len(data['equity']) > 1:
        initial_equity = data['equity']['total_equity'].iloc[-1]  # Oldest record
        current_equity = data['equity']['total_equity'].iloc[0]   # Latest record
        total_return = ((current_equity - initial_equity) / initial_equity * 100) if initial_equity > 0 else 0
    else:
        total_return = 0
    
    return {
        'total_equity': latest_equity.get('total_equity', 0),
        'daily_pnl': latest_equity.get('daily_pnl', 0),
        'total_return': total_return,
        'open_positions': latest_equity.get('open_positions', 0),
        'total_trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': 0  # Would need risk-free rate data
    }

def main():
    # Main title
    st.markdown('<div class="main-header">🤖 Trading Bot Dashboard</div>', unsafe_allow_html=True)
    
    # Sidebar controls
    st.sidebar.header("🎛️ Dashboard Controls")
    
    # Auto-refresh settings
    auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh", value=False)  # Default to False
    refresh_interval = st.sidebar.selectbox("Refresh Interval", [15, 30, 60, 120], index=1)
    
    # Use proper auto-refresh with session state timing
    if auto_refresh:
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time.time()
        
        if time.time() - st.session_state.last_refresh > refresh_interval:
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            st.rerun()
    
    # Manual refresh
    if st.sidebar.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()
    
    # Time range selector
    time_range = st.sidebar.selectbox(
        "📅 Time Range", 
        ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"],
        index=1
    )
    
    # Bot Control Section
    st.sidebar.header("🤖 Bot Control")
    bot_status = st.sidebar.empty()  # Placeholder for status

    # Global bot instance and thread (use session state to persist)
    if 'bot' not in st.session_state:
        st.session_state.bot = None
    if 'bot_thread' not in st.session_state:
        st.session_state.bot_thread = None
    if 'bot_running' not in st.session_state:
        st.session_state.bot_running = False

    # Start/Stop Buttons
    if st.sidebar.button("🚀 Start Live Bot"):
        if not st.session_state.bot_running:
            from live_trading_bot import LiveTradingBot
            import threading
            st.session_state.bot = LiveTradingBot()
            st.session_state.bot_thread = threading.Thread(target=st.session_state.bot.run)
            st.session_state.bot_thread.start()
            st.session_state.bot_running = True
            bot_status.success("Bot started! Fetching real-time data...")

    if st.sidebar.button("🛑 Stop Bot"):
        if st.session_state.bot_running:
            st.session_state.bot.stop()  # Use the new stop method
            st.session_state.bot_thread.join(timeout=10)  # Wait for thread to stop
            st.session_state.bot_running = False
            bot_status.warning("Bot stopped.")

    # Display Bot Status
    if st.session_state.bot_running:
        bot_status.success("Bot Running (Live Mode)")
    else:
        bot_status.error("Bot Stopped")

    # Live Log Viewer (tail last 10 lines)
    st.sidebar.subheader("📜 Live Logs")
    log_placeholder = st.sidebar.empty()
    try:
        with open('trading_bot.log', 'r') as log_file:
            logs = log_file.readlines()[-10:]
            log_placeholder.text(''.join(logs))
    except FileNotFoundError:
        log_placeholder.text("No logs available yet.")
    
    # Load data
    data = load_database_data()
    
    # Check if data exists (after potential demo data generation)
    if data['trades'].empty and data['equity'].empty:
        st.warning("⚠️ No data available. Make sure your trading bot is running and logging data.")
        
        # Show setup instructions
        with st.expander("📋 Setup Instructions"):
            st.markdown("""
            ### To get data in your dashboard:
            
            1. **Integrate Enhanced State Manager**:
               ```python
               from enhanced_state_manager import DashboardStateManager
               dashboard_state = DashboardStateManager()
               ```
            
            2. **Log trades in your bot**:
               ```python
               dashboard_state.log_trade(trade_data)
               dashboard_state.log_equity_snapshot(position_manager, current_prices)
               ```
            
            3. **Run your trading bot** - data will appear here automatically!
            """)
        return
    
    # Calculate metrics
    metrics = calculate_metrics(data)
    
    # Status indicator
    if not data['health'].empty:
        latest_health = data['health'].iloc[0]
        last_update = pd.to_datetime(latest_health['timestamp'])
        minutes_ago = (datetime.now() - last_update).total_seconds() / 60
        
        if minutes_ago < 5:
            status = "🟢 Online"
            status_color = "positive"
        elif minutes_ago < 15:
            status = "🟡 Warning"
            status_color = "neutral"
        else:
            status = "🔴 Offline"
            status_color = "negative"
    else:
        status = "❓ Unknown"
        status_color = "neutral"
        minutes_ago = 0
    
    # Top-level status
    col_status1, col_status2, col_status3 = st.columns([2, 2, 1])
    with col_status1:
        st.markdown(f"**System Status:** <span class='{status_color}'>{status}</span>", unsafe_allow_html=True)
    with col_status2:
        st.markdown(f"**Last Update:** {minutes_ago:.0f} minutes ago")
    with col_status3:
        st.markdown(f"**🕒 {datetime.now().strftime('%H:%M:%S')}**")
    
    st.markdown("---")
    
    # Main KPI metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "💰 Total Equity", 
            f"${metrics['total_equity']:,.2f}",
            delta=f"${metrics['daily_pnl']:,.2f}" if metrics['daily_pnl'] != 0 else None
        )
    
    with col2:
        st.metric(
            "📈 Total Return", 
            f"{metrics['total_return']:,.1f}%",
            delta=f"{metrics['total_return']:,.1f}%" if metrics['total_return'] != 0 else None
        )
    
    with col3:
        st.metric(
            "🎯 Win Rate", 
            f"{metrics['win_rate']:.1f}%"
        )
    
    with col4:
        st.metric(
            "📊 Open Positions", 
            f"{metrics['open_positions']}"
        )
    
    with col5:
        st.metric(
            "🔢 Total Trades", 
            f"{metrics['total_trades']}"
        )
    
    st.markdown("---")
    
    # Secondary metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        color = "positive" if metrics['profit_factor'] > 1 else "negative"
        st.markdown(f"**Profit Factor:** <span class='{color}'>{metrics['profit_factor']:.2f}</span>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"**Max Drawdown:** <span class='negative'>{metrics['max_drawdown']:.1f}%</span>", unsafe_allow_html=True)
    
    with col3:
        daily_pnl_color = "positive" if metrics['daily_pnl'] >= 0 else "negative"
        st.markdown(f"**Daily P&L:** <span class='{daily_pnl_color}'>${metrics['daily_pnl']:,.2f}</span>", unsafe_allow_html=True)
    
    with col4:
        unrealized_pnl = 0
        if not data['equity'].empty and 'unrealized_pnl' in data['equity'].columns:
            unrealized_pnl = data['equity'].iloc[0]['unrealized_pnl']
        st.markdown(f"**Unrealized P&L:** <span class='neutral'>${unrealized_pnl:,.2f}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts section
    if not data['equity'].empty:
        # Equity curve chart
        st.subheader("📈 Portfolio Equity Curve")
        
        fig_equity = go.Figure()
        
        # Convert timestamps and sort chronologically
        equity_data = data['equity'].copy()
        equity_data['datetime'] = pd.to_datetime(equity_data['timestamp'])
        equity_data = equity_data.sort_values('datetime')
        
        # Total equity line
        fig_equity.add_trace(go.Scatter(
            x=equity_data['datetime'],
            y=equity_data['total_equity'],
            mode='lines',
            name='Total Equity',
            line=dict(color='#1f77b4', width=3),
            hovertemplate='<b>Total Equity</b><br>Date: %{x}<br>Value: $%{y:,.2f}<extra></extra>'
        ))
        
        # Ichimoku strategy
        if 'ichimoku_equity' in equity_data.columns:
            fig_equity.add_trace(go.Scatter(
                x=equity_data['datetime'],
                y=equity_data['ichimoku_equity'],
                mode='lines',
                name='Ichimoku Strategy',
                line=dict(color='#2ca02c', width=2),
                hovertemplate='<b>Ichimoku</b><br>Date: %{x}<br>Value: $%{y:,.2f}<extra></extra>'
            ))
        
        # RSI Reversal strategy
        if 'reversal_equity' in equity_data.columns:
            fig_equity.add_trace(go.Scatter(
                x=equity_data['datetime'],
                y=equity_data['reversal_equity'],
                mode='lines',
                name='RSI Reversal Strategy',
                line=dict(color='#d62728', width=2),
                hovertemplate='<b>RSI Reversal</b><br>Date: %{x}<br>Value: $%{y:,.2f}<extra></extra>'
            ))
        
        fig_equity.update_layout(
            title="Portfolio Performance Over Time",
            xaxis_title="Date",
            yaxis_title="Equity ($)",
            height=500,
            hovermode='x unified',
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        
        st.plotly_chart(fig_equity, use_container_width=True)
        
        # Drawdown chart
        st.subheader("📉 Drawdown Analysis")
        
        # Calculate drawdown
        equity_values = equity_data['total_equity'].values
        cummax = np.maximum.accumulate(equity_values)
        drawdown = (cummax - equity_values) / cummax * 100
        
        fig_drawdown = go.Figure()
        fig_drawdown.add_trace(go.Scatter(
            x=equity_data['datetime'],
            y=-drawdown,  # Negative for visualization
            mode='lines',
            fill='tonexty',
            name='Drawdown',
            line=dict(color='red', width=1),
            fillcolor='rgba(255, 0, 0, 0.3)'
        ))
        
        fig_drawdown.update_layout(
            title="Portfolio Drawdown",
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            height=300,
            showlegend=False
        )
        
        st.plotly_chart(fig_drawdown, use_container_width=True)
    
    # Two-column layout for trade analysis
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Strategy Performance")
        if not data['trades'].empty:
            # Strategy breakdown
            strategy_stats = data['trades'][data['trades']['action'] == 'SELL'].groupby('strategy').agg({
                'pnl': ['count', 'sum', 'mean'],
                'quantity': 'sum'
            }).round(2)
            
            if not strategy_stats.empty:
                strategy_stats.columns = ['Trade Count', 'Total P&L', 'Avg P&L', 'Total Quantity']
                strategy_stats['Win Rate %'] = data['trades'][
                    (data['trades']['action'] == 'SELL') & (data['trades']['pnl'] > 0)
                ].groupby('strategy')['pnl'].count() / strategy_stats['Trade Count'] * 100
                
                st.dataframe(strategy_stats.fillna(0), use_container_width=True)
        else:
            st.info("No completed trades yet")
    
    with col2:
        st.subheader("📊 P&L Distribution")
        if not data['trades'].empty:
            completed_trades = data['trades'][data['trades']['action'] == 'SELL']
            if not completed_trades.empty:
                fig_hist = px.histogram(
                    completed_trades, 
                    x='pnl', 
                    nbins=20, 
                    title="Trade P&L Distribution",
                    color_discrete_sequence=['#1f77b4']
                )
                fig_hist.update_layout(height=400)
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No completed trades for distribution")
        else:
            st.info("No trade data available")
    
    # Recent trades table
    st.subheader("🔄 Recent Trading Activity")
    if not data['trades'].empty:
        # Format recent trades
        recent_trades = data['trades'].head(20).copy()
        recent_trades['timestamp'] = pd.to_datetime(recent_trades['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Select and rename columns for display
        display_columns = ['timestamp', 'symbol', 'strategy', 'action', 'quantity', 'price', 'pnl']
        if 'paper_traded' in recent_trades.columns:
            recent_trades['paper_traded'] = recent_trades['paper_traded'].map({True: '📝', False: '💰'})
            display_columns.append('paper_traded')
        
        display_trades = recent_trades[display_columns]
        display_trades.columns = ['Time', 'Symbol', 'Strategy', 'Action', 'Quantity', 'Price', 'P&L', 'Type']
        
        # Style the dataframe
        def color_pnl(val):
            if pd.isna(val) or val == 0:
                return ''
            color = 'color: green' if val > 0 else 'color: red'
            return color
        
        styled_trades = display_trades.style.map(color_pnl, subset=['P&L'])
        st.dataframe(styled_trades, use_container_width=True, height=400)
    else:
        st.info("No trades recorded yet")

    # System information in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("ℹ️ System Information")
    
    if not data['health'].empty:
        latest_health = data['health'].iloc[0]
        st.sidebar.markdown(f"**Status:** {latest_health['status']}")
        st.sidebar.markdown(f"**API Connected:** {'✅' if latest_health['api_connection'] else '❌'}")
        st.sidebar.markdown(f"**Error Count:** {latest_health['error_count']}")
    
    # Database stats
    db_stats = {
        'Trades': len(data['trades']),
        'Equity Snapshots': len(data['equity']),
        'Health Checks': len(data['health'])
    }
    
    st.sidebar.markdown("**Database Records:**")
    for key, value in db_stats.items():
        st.sidebar.markdown(f"- {key}: {value:,}")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
        "🤖 Trading Bot Dashboard | Real-time monitoring and analytics"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
