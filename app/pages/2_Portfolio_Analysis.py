import streamlit as st
import plotly.express as px
import pandas as pd
import sys
import os

# --- PATH SETUP ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend import database
from ml_engine import analysis
from app import session_manager

st.set_page_config(page_title="Portfolio Analysis", layout="wide")

# --- AUTH CHECK ---
session_manager.check_login()

st.title("📈 Deep Dive Analysis")

# --- DATA LOADING ---
user_id = st.session_state.user['localId']
portfolio = database.get_user_portfolio(user_id)
tickers = list(portfolio.keys())

if not tickers:
    st.info("Please add stocks on the Home page first.")
    st.stop()

with st.spinner("Crunching the numbers..."):
    # 1. Fetch Data
    stock_data = database.fetch_market_data(tickers)
    sp500_data = database.fetch_market_data(['^GSPC'])
    
    # 2. Run Math Engine (Beta, Sharpe, Volatility)
    if not sp500_data.empty:
        # Handle S&P 500 formatting
        sp500_series = sp500_data['^GSPC'] if '^GSPC' in sp500_data.columns else sp500_data.iloc[:, 0]
        
        # Calculate Risk Metrics
        risk_df = analysis.calculate_metrics(stock_data, sp500_series)
        
        # Calculate Total Return for plotting
        # (Current Price - Start Price) / Start Price
        total_returns = (stock_data.iloc[-1] - stock_data.iloc[0]) / stock_data.iloc[0] * 100
        
        # Merge metrics into one DataFrame
        risk_df['Total Return (%)'] = total_returns
        risk_df = risk_df.reset_index() # Make Ticker a column
    else:
        st.error("Could not fetch benchmark data.")
        st.stop()

# --- VISUALIZATION ---

# 1. RISK METRICS TABLE
st.subheader("Risk Profile")
st.markdown("""
* **Beta:** Sensitivity to the market. >1.0 means more volatile than the S&P 500.
* **Sharpe:** Risk-adjusted return. >1.0 is good, >2.0 is excellent.
* **Volatility:** How much the price swings on average per year.
""")

# Format the table nicely
st.dataframe(
    risk_df.style.format({
        "Beta": "{:.2f}",
        "Sharpe Ratio": "{:.2f}",
        "Annual Volatility": "{:.1f}%",
        "Total Return (%)": "{:.2f}%"
    }).background_gradient(subset=['Sharpe Ratio'], cmap="RdYlGn"),
    use_container_width=True,
    hide_index=True
)

st.divider()

# 2. RISK VS RETURN SCATTER PLOT
st.subheader("⚖️ Risk vs. Reward")
st.write("Ideally, you want stocks in the **Top-Left** (High Return, Low Risk).")

fig_scatter = px.scatter(
    risk_df, 
    x="Annual Volatility", 
    y="Total Return (%)", 
    text="Ticker",
    size=[10]*len(risk_df), # Make dots fixed size
    color="Sharpe Ratio",
    color_continuous_scale="RdYlGn",
    title="Risk (Volatility) vs Return (1 Year)"
)

# Add quadrants/lines for context
avg_return = risk_df['Total Return (%)'].mean()
avg_risk = risk_df['Annual Volatility'].mean()

fig_scatter.add_vline(x=avg_risk, line_width=1, line_dash="dash", line_color="gray", annotation_text="Avg Risk")
fig_scatter.add_hline(y=avg_return, line_width=1, line_dash="dash", line_color="gray", annotation_text="Avg Return")
fig_scatter.update_traces(textposition='top center')

st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# 3. CORRELATION MATRIX (Bonus Feature!)
st.subheader("🔗 Correlation Matrix")
st.write("Do your stocks move together? (1.0 = move identically, 0.0 = no relationship)")

# Calculate correlation
corr_matrix = stock_data.pct_change().corr()

fig_corr = px.imshow(
    corr_matrix, 
    text_auto=".2f",
    color_continuous_scale="RdBu_r", # Red = Negative, Blue = Positive
    aspect="auto",
    title="Stock Correlation Heatmap"
)
st.plotly_chart(fig_corr, use_container_width=True)