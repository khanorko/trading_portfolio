#!/usr/bin/env python3
"""
Minimal Test Dashboard
Test if we can load and display the equity data
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Test Dashboard", layout="wide")

st.title("🧪 Test Dashboard - Data Loading Check")

# Load data function
def load_test_data():
    db_path = "trading_dashboard.db"
    
    if not Path(db_path).exists():
        st.error("Database file does not exist!")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Load equity snapshots
        equity_df = pd.read_sql_query(
            "SELECT * FROM equity_snapshots ORDER BY timestamp DESC LIMIT 1000", 
            conn
        )
        
        conn.close()
        return equity_df
        
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

# Load and display data
st.subheader("📊 Data Loading Test")

equity_data = load_test_data()

if equity_data is not None:
    st.success(f"✅ Successfully loaded {len(equity_data)} equity records")
    
    if not equity_data.empty:
        # Show basic info
        latest_equity = equity_data.iloc[0]['total_equity']
        st.metric("💰 Latest Equity", f"${latest_equity:,.2f}")
        
        # Show data range
        st.write(f"**Date Range:** {equity_data['timestamp'].min()} to {equity_data['timestamp'].max()}")
        
        # Show sample data
        st.subheader("📋 Sample Data")
        st.dataframe(equity_data.head(10))
        
        # Simple chart
        st.subheader("📈 Equity Chart")
        
        # Convert timestamps and sort
        chart_data = equity_data.copy()
        chart_data['datetime'] = pd.to_datetime(chart_data['timestamp'])
        chart_data = chart_data.sort_values('datetime')
        
        # Create simple line chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=chart_data['datetime'],
            y=chart_data['total_equity'],
            mode='lines',
            name='Total Equity',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title="Portfolio Equity Over Time",
            xaxis_title="Date",
            yaxis_title="Equity ($)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Calculate return
        if len(chart_data) > 1:
            initial_equity = chart_data['total_equity'].iloc[0]  # First (oldest) record
            final_equity = chart_data['total_equity'].iloc[-1]   # Last (newest) record
            total_return = ((final_equity - initial_equity) / initial_equity * 100) if initial_equity > 0 else 0
            st.metric("📈 Total Return", f"{total_return:.2f}%")
        
    else:
        st.warning("Equity data is empty")
else:
    st.error("Failed to load data")

# Debug info
st.subheader("🔍 Debug Info")
st.write(f"Database file exists: {Path('trading_dashboard.db').exists()}")
if Path('trading_dashboard.db').exists():
    st.write(f"Database size: {Path('trading_dashboard.db').stat().st_size / 1024:.1f} KB") 