import streamlit as st
import extra_streamlit_components as stx
import sys
import os

# Path setup to find backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend import auth

def check_login():
    """
    Ensures the user is logged in. 
    If not, it checks cookies.
    If still not, it stops the app and tells them to go to Main.
    """
    if 'user' not in st.session_state:
        st.session_state.user = None

    # If already logged in, we are good
    if st.session_state.user:
        return True

    # If not, try to recover from cookie
    cookie_manager = stx.CookieManager()
    cookie_token = cookie_manager.get(cookie="firebase_token")

    if cookie_token:
        # Validate the token with Firebase
        res = auth.get_account_info(cookie_token)
        if res.status_code == 200:
            st.session_state.user = res.json()['users'][0]
            return True
    
    # If we get here, they are not logged in
    st.warning("🔒 Please log in on the Home Page first.")
    st.stop() # Stops the page from loading further
    return False