import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import numpy as np

# --- PATH SETUP ---
# Allows importing modules from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend import database, auth
from ml_engine import analysis

# --- PAGE CONFIG ---
st.set_page_config(page_title="Intelligent Portfolio", layout="wide")

# --- AUTHENTICATION LOGIC ---
if 'user' not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔒 Portfolio Tracker - Login")
    
    tab1, tab2 = st.tabs(["Log In", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Log In"):
            with st.spinner("Authenticating..."):
                res = auth.sign_in(email, password)
                if res.status_code == 200:
                    st.session_state.user = res.json()
                    st.success("Success!")
                    st.rerun()
                else:
                    st.error("Login Failed: " + res.json().get('error', {}).get('message', ''))

    with tab2:
        new_email = st.text_input("New Email")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            with st.spinner("Creating Account..."):
                res = auth.sign_up(new_email, new_pass)
                if res.status_code == 200:
                    st.success("Account created! Please Log In.")
                else:
                    st.error("Error: " + res.json().get('error', {}).get('message', ''))
    
    st.stop() # STOP EXECUTION HERE if not logged in

# --- MAIN APP START ---
user_id = st.session_state.user['localId']
user_email = st.session_state.user['email']

# --- SIDEBAR: ASSET MANAGER ---
st.sidebar.title(f"👤 {user_email}")
if st.sidebar.button("Log Out"):
    st.session_state.user = None
    st.rerun()

st.sidebar.divider()
st.sidebar.header("💼 Asset Manager")

# 1. Load Portfolio (Dictionary)
portfolio = database.get_user_portfolio(user_id)
tickers = list(portfolio.keys())

# 2. Add / Edit Asset Form
with st.sidebar.expander("➕ Add / Edit Asset", expanded=True):
    with st.form("add_asset_form"):
        ticker_in = st.text_input("Ticker (e.g. AAPL)", max_chars=5).upper()
        qty_in = st.number_input("Quantity", min_value=0.01, step=0.1)
        cost_in = st.number_input("Avg Cost ($)", min_value=0.0)
        
        if st.form_submit_button("Save Asset"):
            if ticker_in:
                with st.spinner(f"Validating {ticker_in}..."):
                    check = database.fetch_market_data([ticker_in])
                    if not check.empty:
                        portfolio[ticker_in] = {'quantity': qty_in, 'avg_cost': cost_in}
                        database.save_user_portfolio(user_id, portfolio)
                        st.success(f"Saved {ticker_in}!")
                        st.rerun()
                    else:
                        st.error("Invalid Ticker")

# 3. Remove Asset
if tickers:
    with st.sidebar.expander("❌ Remove Asset"):
        to_remove = st.selectbox("Select Asset", tickers)
        if st.button("Delete Asset"):
            del portfolio[to_remove]
            database.save_user_portfolio(user_id, portfolio)
            st.rerun()

# --- MAIN DASHBOARD ---
st.title("📊 My Portfolio Dashboard")

if not tickers:
    st.info("👈 Use the sidebar to add your first stock!")
    st.stop()

# 1. FETCH DATA (Stocks + S&P 500 + Sectors)
with st.spinner("Syncing market data & Analyzing Risk..."):
    # Fetch User Stocks
    current_prices_df = database.fetch_market_data(tickers)
    
    # Fetch Benchmark (S&P 500)
    sp500_data = database.fetch_market_data(['^GSPC'])
    
    # Fetch Sectors (Cache this to speed up)
    @st.cache_data
    def get_sectors(ticker_list):
        return database.fetch_sector_info(ticker_list)
    
    sector_map = get_sectors(tickers)

# 2. RUN AI ANALYSIS (Metrics: Beta & Sharpe)
if not sp500_data.empty:
    # Handle Series vs DataFrame for S&P
    sp500_series = sp500_data['^GSPC'] if '^GSPC' in sp500_data.columns else sp500_data.iloc[:, 0]
    risk_metrics = analysis.calculate_metrics(current_prices_df, sp500_series)
else:
    risk_metrics = pd.DataFrame()

# 3. CALCULATE PORTFOLIO FINANCIALS
rows = []
total_portfolio_value = 0
total_invested = 0
sector_distribution = {}

for ticker in tickers:
    qty = portfolio[ticker]['quantity']
    avg_cost = portfolio[ticker]['avg_cost']
    
    # Safe price fetch
    if ticker in current_prices_df.columns:
        current_price = current_prices_df[ticker].iloc[-1]
    else:
        current_price = 0
        
    market_value = qty * current_price
    total_cost = qty * avg_cost
    unrealized_pl = market_value - total_cost
    pl_pct = (unrealized_pl / total_cost * 100) if total_cost > 0 else 0
    
    total_portfolio_value += market_value
    total_invested += total_cost
    
    # Sector Math
    sector = sector_map.get(ticker, "Unknown")
    sector_distribution[sector] = sector_distribution.get(sector, 0) + market_value

    # Get Metrics
    beta = risk_metrics.loc[ticker, 'Beta'] if ticker in risk_metrics.index else 0
    sharpe = risk_metrics.loc[ticker, 'Sharpe Ratio'] if ticker in risk_metrics.index else 0

    rows.append({
        "Ticker": ticker,
        "Sector": sector,
        "Qty": qty,
        "Price": current_price,
        "Value": market_value,
        "P/L ($)": unrealized_pl,
        "Return (%)": pl_pct,
        "Beta": beta,
        "Sharpe": sharpe
    })

df_portfolio = pd.DataFrame(rows)

# 4. KPI DISPLAY
total_pl = total_portfolio_value - total_invested
total_pl_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Net Worth", f"${total_portfolio_value:,.2f}")
kpi2.metric("Total P/L", f"${total_pl:,.2f}", delta=f"{total_pl_pct:.2f}%")
kpi3.metric("Sharpe Ratio", f"{df_portfolio['Sharpe'].mean():.2f}") 
kpi4.metric("Portfolio Beta", f"{df_portfolio['Beta'].mean():.2f}")

st.divider()

# 5. CHARTS ROW (Sector Pie + Holdings Table)
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Sector Allocation")
    sector_df = pd.DataFrame(list(sector_distribution.items()), columns=['Sector', 'Value'])
    if not sector_df.empty:
        fig_sector = px.pie(sector_df, values='Value', names='Sector', hole=0.4)
        fig_sector.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_sector, width="stretch")

with col2:
    st.subheader("Holdings Analysis")
    st.dataframe(
        df_portfolio.style.format({
            "Price": "${:.2f}",
            "Value": "${:,.2f}",
            "P/L ($)": "${:,.2f}",
            "Return (%)": "{:.2f}%",
            "Beta": "{:.2f}",
            "Sharpe": "{:.2f}"
        }).background_gradient(subset=['Return (%)'], cmap="RdYlGn"),
        width=1000,
        hide_index=True
    )

st.divider()

# 6. BENCHMARK COMPARISON
st.subheader("📈 Performance vs S&P 500")
with st.spinner("Comparing against S&P 500..."):
    # Calculate Portfolio History (Weighted by current value)
    daily_returns = current_prices_df.pct_change().fillna(0)
    
    # Dynamic Weights (Simplified: assumes current weights held constant)
    if total_portfolio_value > 0:
        weights = df_portfolio.set_index('Ticker')['Value'] / total_portfolio_value
        weights = weights.reindex(daily_returns.columns).fillna(0)
        portfolio_daily_returns = (daily_returns * weights).sum(axis=1)
        portfolio_cumulative = (1 + portfolio_daily_returns).cumprod()
        
        # S&P 500
        sp500_returns = sp500_series.pct_change().fillna(0)
        sp500_cumulative = (1 + sp500_returns).cumprod()
        
        comparison_df = pd.DataFrame({
            "Your Portfolio": portfolio_cumulative,
            "S&P 500": sp500_cumulative
        }).dropna()
        
        fig_bench = px.line(comparison_df)
        fig_bench.update_traces(patch={"line": {"color": "gray", "dash": "dash"}}, selector={"name": "S&P 500"})
        fig_bench.update_traces(patch={"line": {"color": "#4CAF50", "width": 3}}, selector={"name": "Your Portfolio"})
        st.plotly_chart(fig_bench, width="stretch")

# 7. AI FORECAST
st.divider()
st.subheader("🤖 AI Price Forecaster")
selected_ticker = st.selectbox("Select asset to predict:", tickers)

if st.button(f"Generate Forecast for {selected_ticker}"):
    with st.spinner(f"Running Prophet AI Model on {selected_ticker}..."):
        forecast = analysis.predict_future(current_prices_df, selected_ticker, days=30)
        
        # Plot
        fig_forecast = px.line(forecast, x='ds', y='yhat', title=f"{selected_ticker} 30-Day Forecast")
        fig_forecast.add_scatter(x=forecast['ds'], y=forecast['yhat_upper'], mode='lines', 
                                 name='Upper Bound', line=dict(width=0))
        fig_forecast.add_scatter(x=forecast['ds'], y=forecast['yhat_lower'], mode='lines', 
                                 name='Lower Bound', line=dict(width=0), fill='tonexty')
        st.plotly_chart(fig_forecast, width="stretch")