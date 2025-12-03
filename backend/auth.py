import requests

# REPLCAE WITH YOUR API KEY
FIREBASE_WEB_API_KEY = "AIzaSyDDM5CJYmYUvEZbMnTrHc-Bs-gprHTJ5Wo" 

def sign_in(email, password):
    request_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(request_url, json=payload)

def sign_up(email, password):
    request_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(request_url, json=payload)