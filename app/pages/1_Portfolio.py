import streamlit as st
import sys
import os
import pandas as pd
import extra_streamlit_components as stx

# --- PATH SETUP ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend import database
from app import session_manager

# --- PAGE CONFIG ---
st.set_page_config(page_title="Manage Portfolio", page_icon="💼", layout="wide")

# --- LOAD CSS ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "style.css")
local_css(css_path)

# --- AUTH CHECK ---
session_manager.check_login()
user_id = st.session_state.user['localId']

# --- MAIN CONTENT ---
st.title("Manage Portfolio")
st.markdown("Add new investments or update your existing holdings.")

# Fetch Portfolio
portfolio = database.get_user_portfolio(user_id)
tickers = list(portfolio.keys())

# --- LAYOUT: 2 Columns (Add vs Delete) ---
c1, c2 = st.columns(2)

# --- SECTION 1: ADD / UPDATE ---
with c1:
    with st.form("add_asset_main"):
        st.subheader("Add or Update Asset")
        st.caption("Enter a ticker to add it. If it exists, this will update the quantity/cost.")
        
        ticker = st.text_input("Ticker Symbol", placeholder="e.g. NVDA").upper()
        
        col_q, col_c = st.columns(2)
        qty = col_q.number_input("Total Shares", min_value=0.01, step=0.1)
        cost = col_c.number_input("Average Cost ($)", min_value=0.0, step=0.1)
        
        if st.form_submit_button("Save Asset", width='stretch'):
            if ticker:
                with st.spinner(f"Verifying {ticker}..."):
                    check = database.fetch_market_data([ticker])
                    if not check.empty:
                        portfolio[ticker] = {'quantity': qty, 'avg_cost': cost}
                        database.save_user_portfolio(user_id, portfolio)
                        st.success(f"Successfully saved {ticker} to your portfolio.")
                        st.rerun()
                    else:
                        st.error(f"Could not find ticker '{ticker}' on the market.")
            else:
                st.warning("Please enter a ticker symbol.")

# --- SECTION 2: REMOVE ---
with c2:
    st.subheader("Remove Asset")
    
    if tickers:
        # The selectbox holds the currently selected asset
        to_remove = st.selectbox("Select Asset to Delete", tickers, key="delete_select")
        
        if st.button("Delete Selected Asset", key="btn_delete_main", width='stretch'):
            # 1. Remove the item from the portfolio dictionary in memory
            del portfolio[to_remove] 
            
            # 2. Save the reduced dictionary back to the database
            database.save_user_portfolio(user_id, portfolio) 
            
            st.success(f"Successfully deleted {to_remove}. Updating portfolio view...")
            st.rerun() # Force the page to reload the data from the DB
    else:
        st.info("Your portfolio is empty.")

# --- SECTION 3: CURRENT HOLDINGS SUMMARY ---
st.subheader("Current Holdings Registry")

if tickers:
    # Convert dictionary to clean DataFrame for viewing
    data = []
    for t, info in portfolio.items():
        data.append({
            "Asset": t,
            "Shares": info['quantity'],
            "Avg Cost": info['avg_cost'],
            "Total Invested": info['quantity'] * info['avg_cost']
        })
    
    df = pd.DataFrame(data)
    
    st.dataframe(
        df,
        column_config={
            "Asset": st.column_config.TextColumn("Ticker", width="small"),
            "Shares": st.column_config.NumberColumn("Quantity", format="%.2f"),
            "Avg Cost": st.column_config.NumberColumn("Avg Cost", format="$%.2f"),
            "Total Invested": st.column_config.NumberColumn("Invested Capital", format="$%.2f"),
        },
        width='stretch',
        hide_index=True
    )
else:
    st.info("No assets found. Use the form above to get started.")