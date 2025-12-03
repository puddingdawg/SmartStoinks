import firebase_admin
from firebase_admin import credentials, firestore
import datetime as dt
import yfinance as yf
import pandas as pd

# --- CONFIGURATION ---
# Ensure this file exists in your root folder
CRED_PATH = "firebase_key.json"

# --- FIREBASE INIT ---
# We use a singleton pattern to ensure we only initialize once
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Error initializing Firebase: {e}")

db = firestore.client()

# --- PORTFOLIO FUNCTIONS ---

def get_user_portfolio(user_id):
    """
    Retrieves the user's portfolio from Firestore.
    Returns a dictionary: {'AAPL': {'quantity': 10, 'avg_cost': 150}, ...}
    """
    try:
        doc = db.collection("users").document(user_id).get()
        
        if doc.exists:
            data = doc.to_dict().get("portfolio", {})
            
            # --- MIGRATION LOGIC ---
            # If the database contains the old List format ["AAPL", "MSFT"],
            # we convert it to the new Dictionary format instantly.
            if isinstance(data, list):
                converted_data = {ticker: {'quantity': 1.0, 'avg_cost': 0.0} for ticker in data}
                # Save the converted data back so we don't have to do this again
                save_user_portfolio(user_id, converted_data)
                return converted_data
                
            return data
        return {}
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        return {}
    
def fetch_sector_info(tickers):
    """
    Fetches sector info (e.g., 'Technology', 'Healthcare') for a list of tickers.
    Note: fetching .info is slow, so we use it sparingly.
    """
    sector_map = {}
    for t in tickers:
        try:
            # yfinance allows fetching info object
            info = yf.Ticker(t).info
            sector = info.get('sector', 'Unknown')
            sector_map[t] = sector
        except Exception:
            sector_map[t] = 'Unknown'
    return sector_map

def save_user_portfolio(user_id, portfolio_dict):
    """
    Saves the full portfolio dictionary to Firestore.
    """
    try:
        db.collection("users").document(user_id).set({
            "portfolio": portfolio_dict,
            "last_updated": dt.datetime.now()
        }, merge=True)
    except Exception as e:
        print(f"Error saving portfolio: {e}")

# --- MARKET DATA FUNCTIONS ---

def fetch_market_data(tickers):
    """
    Fetches historical data for the given list of tickers.
    Returns a DataFrame with the Adjusted Close prices.
    """
    if not tickers:
        return pd.DataFrame()
    
    # We fetch 1 year of data to calculate trends and volatility
    start_date = dt.datetime.now() - dt.timedelta(days=365)
    
    try:
        # auto_adjust=False ensures we get the raw columns so we can find 'Adj Close' safely
        data = yf.download(tickers, start=start_date, progress=False, auto_adjust=False)
        
        # CLEANUP: Handle different return formats from yfinance
        # 1. If 'Adj Close' exists, use it.
        if 'Adj Close' in data:
            data = data['Adj Close']
        # 2. If not, use 'Close' (common for indices or crypto)
        elif 'Close' in data:
            data = data['Close']
            
        # 3. If we only fetched one stock, yfinance returns a Series. 
        # We convert it to a DataFrame so the rest of the app doesn't break.
        if isinstance(data, pd.Series):
            data = data.to_frame(name=tickers[0])
            
        return data
    except Exception as e:
        print(f"Error fetching market data: {e}")
        return pd.DataFrame()
    

