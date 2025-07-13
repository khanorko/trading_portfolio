import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

st.set_page_config(
    page_title="Trading Bot Dashboard Test",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Trading Bot Dashboard - Test Version")

# Test sidebar
st.sidebar.header("🎛️ Dashboard Controls")
st.sidebar.checkbox("🔄 Auto Refresh", value=False)
st.sidebar.selectbox("Refresh Interval", [15, 30, 60, 120], index=1)

# Test basic content
st.write("✅ Basic Streamlit functionality working")
st.write("✅ Plotly import successful")
st.write("✅ Pandas import successful")

# Test simple chart
data = pd.DataFrame({
    'Date': pd.date_range('2023-01-01', periods=100),
    'Value': range(100)
})

fig = go.Figure()
fig.add_trace(go.Scatter(x=data['Date'], y=data['Value'], name='Test Data'))
st.plotly_chart(fig, use_container_width=True)

st.success("🎉 Test dashboard is working! The issue might be with the full dashboard.") 