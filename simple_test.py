import streamlit as st
import os

st.title("🚀 Trading Portfolio Test")

st.write("✅ Streamlit is working!")
st.write(f"✅ Python version: {st.__version__}")

# Test environment variables
if os.getenv('BYBIT_API_KEY'):
    st.write("✅ Environment variables loaded")
else:
    st.write("❌ Environment variables missing")

st.write("🎯 If you see this, Railway deployment is working!")

# Simple metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Status", "Online", "✅")
with col2:
    st.metric("Test", "Passed", "100%")
with col3:
    st.metric("Railway", "Working", "🚀") 