import numpy as np
import pandas as pd
from prophet import Prophet

def analyze_risk(stock_data):
    """
    Calculates the Annualized Volatility for each stock.
    Input: DataFrame of prices.
    Output: Dictionary {Ticker: Risk_Percentage}
    """
    if stock_data.empty:
        return {}

    # Calculate daily returns
    daily_returns = stock_data.pct_change().dropna()
    
    # Standard Deviation * sqrt(252 trading days)
    volatility = daily_returns.std() * np.sqrt(252)
    
    # Return as a clean dictionary
    return volatility.to_dict()

def predict_simple_trend(stock_data):
    """
    A simple dummy AI function to show architecture.
    Returns: 'Bullish' if the 50-day average is above the 200-day average.
    """
    trends = {}
    for ticker in stock_data.columns:
        prices = stock_data[ticker].dropna()
        if len(prices) > 200:
            ma50 = prices.rolling(window=50).mean().iloc[-1]
            ma200 = prices.rolling(window=200).mean().iloc[-1]
            trends[ticker] = "Bullish 🟢" if ma50 > ma200 else "Bearish 🔴"
        else:
            trends[ticker] = "Not enough data ⚪"
    return trends

import pandas as pd
import numpy as np

def calculate_metrics(stock_data, benchmark_data, risk_free_rate=0.04):
    """
    Calculates Beta and Sharpe Ratio for each stock.
    Returns a DataFrame with metrics.
    """
    metrics = []
    
    # Calculate daily returns
    stock_returns = stock_data.pct_change().dropna()
    bench_returns = benchmark_data.pct_change().dropna()
    
    # Align dates (Crucial: specific stocks might have missing days compared to S&P)
    # We use inner join to only compare days where both have data
    aligned_data = pd.concat([stock_returns, bench_returns], axis=1, join='inner').dropna()
    
    # Separate them back out
    # Assuming benchmark is the last column or we access by name if passed differently
    # For simplicity here, we assume single column benchmark passed in
    market_col = aligned_data.columns[-1]
    
    for ticker in stock_data.columns:
        if ticker not in aligned_data.columns:
            continue
            
        r_stock = aligned_data[ticker]
        r_market = aligned_data[market_col]
        
        # --- BETA CALCULATION ---
        # Beta = Covariance(Stock, Market) / Variance(Market)
        covariance = np.cov(r_stock, r_market)[0, 1]
        market_variance = np.var(r_market)
        beta = covariance / market_variance if market_variance != 0 else 0
        
        # --- SHARPE RATIO CALCULATION ---
        # Sharpe = (Mean Return - Risk Free) / Std Dev
        # Annualized
        avg_return = r_stock.mean() * 252
        std_dev = r_stock.std() * np.sqrt(252)
        sharpe = (avg_return - risk_free_rate) / std_dev if std_dev != 0 else 0
        
        metrics.append({
            "Ticker": ticker,
            "Beta": round(beta, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Annual Volatility": round(std_dev * 100, 1)
        })
        
    return pd.DataFrame(metrics).set_index("Ticker")

def predict_future(stock_data, ticker, days=30):
    """Prophet Forecasting (Same as before)"""
    df = stock_data[[ticker]].reset_index()
    df.columns = ['ds', 'y']
    df['ds'] = df['ds'].dt.tz_localize(None)
    
    model = Prophet(daily_seasonality=True)
    model.fit(df)
    
    future = model.make_future_dataframe(periods=days)
    forecast = model.predict(future)
    
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(days)