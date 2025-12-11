import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import extra_streamlit_components as stx

# --- PATH SETUP ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend import database, auth
from ml_engine import analysis
from app import session_manager

# --- PAGE CONFIG ---
st.set_page_config(page_title="SmartStoinks", page_icon="📈", layout="wide")

# --- FUNCTION TO LOAD CSS ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# LOAD THE STYLE
css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
local_css(css_path)

# --- AUTHENTICATION SETUP ---
cookie_manager = stx.CookieManager()

# 1. Initialize Session State
if 'user' not in st.session_state: 
    st.session_state.user = None

if 'logging_out' not in st.session_state: 
    st.session_state.logging_out = False

# 2. AUTO-LOGIN LOGIC
# We only try to login if the user is NOT logged in
if not st.session_state.user and not st.session_state.logging_out:
    cookie_token = cookie_manager.get("firebase_token")
    
    # Only try to validate if the token is a real string (not empty)
    if cookie_token and cookie_token != "":
        res = auth.get_account_info(cookie_token)
        if res.status_code == 200:
            st.session_state.user = res.json()['users'][0]
            st.rerun()   # Acts like Refresh
        else:
            # Token is invalid (or expired), delete it
            cookie_manager.delete("firebase_token")

# --- LOGIN SCREEN ---
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 8, 1])
    with c2:
        st.markdown("<br><br><h1 style='text-align: center;'>SmartStoinks</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>The smarter way to track your future.</p>", unsafe_allow_html=True)
        
        # 1. Create Tabs for Switching
        tab_login, tab_signup = st.tabs(["Log In", "Create Account"])
        
        # 2. LOGIN TAB
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                
                # Note: This key triggers the Gold styling from your CSS
                if st.form_submit_button("Log In", use_container_width=True, key="gold_login_btn"):
                    res = auth.sign_in(email, password)
                    if res.status_code == 200:
                        temp_user = res.json()
                        user_details = auth.get_account_info(temp_user['idToken'])
                        if user_details.status_code == 200:
                            st.session_state.user = user_details.json()['users'][0]
                        else:
                            st.session_state.user = temp_user
                        # Save valid token
                        cookie_manager.set("firebase_token", temp_user['idToken'])
                        st.rerun()
                    else:
                        st.error("Incorrect details.")

        # 3. SIGN UP TAB (Maybe Include Edge Case of User)
        with tab_signup:
            with st.form("signup_form"):
                new_email = st.text_input("New Email")
                new_pass = st.text_input("New Password", type="password")
                
                if st.form_submit_button("Create Account", use_container_width=True):
                    with st.spinner("Creating account..."):
                        res = auth.sign_up(new_email, new_pass)
                        if res.status_code == 200:
                            st.success("Account created successfully! Please switch to the Log In tab.")
                        else:
                            # Try to parse the error message
                            try:
                                err_msg = res.json().get('error', {}).get('message', 'Unknown Error')
                            except:
                                err_msg = "Could not create account."
                            st.error(f"Error: {err_msg}")
    st.stop()

# --- MAIN APP (Only runs if logged in) ---
user_id = st.session_state.user['localId']
email = st.session_state.user['email']

# SIDEBAR
st.sidebar.markdown(f"### Hello, {email.split('@')[0].capitalize()}.")

# 3. NUCLEAR LOGOUT BUTTON
if st.sidebar.button("Log Out", key="logout"):
    
    st.session_state.logging_out = True
    
    st.session_state.user = None

    cookie_manager.set("firebase_token", "")
    
    st.rerun()

st.sidebar.markdown("---")
portfolio = database.get_user_portfolio(user_id)
tickers = list(portfolio.keys())


# DATA FETCH, Welcome Bubble, when user haven't add stocks to their portfolio
if not tickers:
    # REPLACEMENT: Using CSS Classes from style.css
    st.markdown("""
    <div class="welcome-bubble">
        <p class="welcome-text">
            Welcome to SmartStoinks! Please go to the portfolio page in the sidebar to add your first asset.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Not sure what this does
with st.spinner("Updating portfolio..."):
    prices = database.fetch_market_data(tickers)

# To calculate Values Displayed
total_val, total_cost = 0, 0
rows = []
for t in tickers:
    qty = portfolio[t]['quantity']
    cost = portfolio[t]['avg_cost']
    price = prices[t].iloc[-1] if t in prices else 0
    val = qty * price
    rows.append({"Ticker": t, "Price": price, "Value": val, 
                 "Gain": ((val - (qty*cost))/(qty*cost)*100) if cost > 0 else 0,
                 "P/L": val - (qty*cost)})
    total_val += val
    total_cost += (qty*cost)

df = pd.DataFrame(rows)
total_pl = total_val - total_cost

# --- UI: YOUR NET WORTH SUMMARY SECTION ---
st.markdown("<h1>Your Net Worth</h1>", unsafe_allow_html=True)
st.markdown(f"<h1 style='font-size: 5rem !important; margin-top: -20px;'>${total_val:,.2f}</h1>", unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("Total Earnings", f"${total_pl:,.2f}")
m2.metric("Return", f"{(total_pl/total_cost*100):.2f}%" if total_cost > 0 else "0%")
if not df.empty:
    top = df.loc[df['Gain'].idxmax()]
    m3.metric("Top Performer", top['Ticker'], f"{top['Gain']:.2f}%")

st.markdown("---")

# --- UI: PERFORMANCE CHART ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Performance vs Market")
    
    # 1. Determine Start Date (Account Creation vs 1 Year Default)
    # We try to grab the creation timestamp from the user session
    created_at = st.session_state.user.get('createdAt')
    
    if created_at:
        # Convert ms timestamp string to datetime object
        start_date = pd.to_datetime(int(created_at), unit='ms').tz_localize(None)
    else:
        # Fallback: If date missing, default to 1 year ago
        start_date = pd.Timestamp.now() - pd.Timedelta(days=365)

    # 2. Fetch & Filter Data
    sp500 = database.fetch_market_data(['^GSPC'])
    
    if not sp500.empty:
        # Filter both datasets to start from account creation
        # We use a 1-day buffer to ensure we catch the opening price of the first day
        filter_date = start_date - pd.Timedelta(days=1)
        
        user_hist = prices[prices.index >= filter_date]
        sp_hist = sp500[sp500.index >= filter_date]
        
        # Guard clause: If account is brand new (no data yet), show last 5 days just to have a chart
        if len(user_hist) < 2:
            user_hist = prices.tail(5)
            sp_hist = sp500.tail(5)

        # 3. Calculate Growth % (Normalized to 0% at start)
        user_returns = user_hist.pct_change().fillna(0).mean(axis=1)
        user_growth = (1 + user_returns).cumprod().sub(1).mul(100)
        
        sp_series = sp_hist['^GSPC'] if '^GSPC' in sp_hist else sp_hist.iloc[:,0]
        sp_growth = (1 + sp_series.pct_change().fillna(0)).cumprod().sub(1).mul(100)
        
        # 4. Plot
        fig = go.Figure()
        
        # User (Gold Area)
        fig.add_trace(go.Scatter(
            x=user_growth.index, y=user_growth,
            mode='lines', name='My Portfolio',
            fill='tozeroy', 
            line=dict(color='#CBA135', width=3)
        ))
        
        # S&P (Grey Dash)
        fig.add_trace(go.Scatter(
            x=sp_growth.index, y=sp_growth,
            mode='lines', name='S&P 500',
            line=dict(color='#8C8C8C', width=2, dash='dash')
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'family': "DM Sans"},
            margin=dict(t=10, l=0, r=0, b=0),
            hovermode="x unified",
            xaxis=dict(showgrid=False, showline=True, linecolor='#1A1A1A', tickfont=dict(color='#1A1A1A')),
            yaxis=dict(showgrid=True, gridcolor='#EAEAEA', tickfont=dict(color='#1A1A1A')),
            legend=dict(orientation="h", y=1.02, x=1, font=dict(color='#1A1A1A'))
        )
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Allocation")
    fig_pie = px.pie(df, values='Value', names='Ticker', hole=0.7, 
                     color_discrete_sequence=['#1A1A1A', '#CBA135', '#8C8C8C', '#E0E0E0'])
    fig_pie.update_layout(
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=0, l=0, r=0, b=0)
    )
    fig_pie.update_traces(textinfo='percent', textfont_size=14)
    st.plotly_chart(fig_pie, use_container_width=True)
