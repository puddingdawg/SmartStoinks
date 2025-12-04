import streamlit as st
import plotly.express as px
import sys
import os

# 1. SETUP PATHS & IMPORTS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend import database
from ml_engine import analysis
from app import session_manager # <--- Importing your new file!

st.set_page_config(page_title="AI Forecast", layout="wide")

# 2. CHECK LOGIN (The Gatekeeper)
session_manager.check_login()

# 3. PAGE CONTENT
st.title("🔮 AI Price Forecaster")

user_id = st.session_state.user['localId']
portfolio = database.get_user_portfolio(user_id)
tickers = list(portfolio.keys())

if not tickers:
    st.info("Please add stocks to your portfolio on the Home page first.")
    st.stop()

# Select Asset
selected_ticker = st.selectbox("Select asset to predict:", tickers)

if st.button(f"Generate Forecast for {selected_ticker}", key="forecast_btn"):
    with st.spinner(f"Training Prophet AI Model on {selected_ticker}..."):
        # Fetch Data just for this prediction
        prices_df = database.fetch_market_data([selected_ticker])
        
        # Run AI
        forecast = analysis.predict_future(prices_df, selected_ticker, days=30)
        
        # Plot
        fig_forecast = px.line(forecast, x='ds', y='yhat', 
                               title=f"{selected_ticker} 30-Day Forecast",
                               labels={'ds': 'Date', 'yhat': 'Predicted Price ($)'})
        
        # Add Confidence Intervals (The "Cone")
        fig_forecast.add_scatter(x=forecast['ds'], y=forecast['yhat_upper'], mode='lines', 
                                 name='Upper Bound', line=dict(width=0))
        fig_forecast.add_scatter(x=forecast['ds'], y=forecast['yhat_lower'], mode='lines', 
                                 name='Lower Bound', line=dict(width=0), fill='tonexty')
        
        st.plotly_chart(fig_forecast, width="stretch")
        
        st.success("Analysis Complete. The shaded area represents the AI's confidence interval.")