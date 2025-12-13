# SmartStoinks - The-Intelligent-Portfolio-Assistant (Work In Progress)
AI/ML-powered stock portfolio tracker, built with Python, Streamlit, and Firebase. This app allows you to track your portfolio performance, visualize returns against the S&P 500, and manage your assets with a user-friendly and minimalistic UI.

## 🚀 Features
- **Real-time Dashboard:** Net worth tracking, "Top Performer" metrics and Market Indicators(Fear Index ie VIX: FRED API), Bond Mkt, BTC, Gold).
- **Portfolio Management:** Add, edit, and delete assets (Stocks/ETFs).
- **Portfolio Analysis:** Using AI to check recent news about the company and conduct a sentiment analysis, and have portfolio risk indicators ie SHARP Ratio
- **Interactive Charts:** Compare your personal return vs. the S&P 500.
- **AI Forecast:** Using Prophet to forecast next pricing levels
- **AI Stock/ETF Recommender:** Help beginner investors to get start in investing
- **Secure Auth:** User authentication powered by Firebase.

## 🛠️ Installation

### 1. Clone the repository
```
git clone [https://github.com/YOUR_USERNAME/stock-ai-portfolio.git](https://github.com/YOUR_USERNAME/stock-ai-portfolio.git)
cd stock-ai-portfolio
```

### 2. Install Dependencies
```
pip install -r requirements.txt
```

### 3. Setup Credentials (Important!)
This project uses Firebase for the database. Because security keys are private, they are #NOT included in this repository. You need to set them up manually:

Environment Variables: Create a file named .env in the root directory and add your Web API Key

Firebase Keys: Place your firebase_key.json file contents in the .env file.

### 4. Run the App
```
streamlit run app/Home.py
```
