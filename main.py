import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from google import genai

# --- 1. 配置 (云端版：无需代理设置) ---
# 建议通过 Streamlit 的 Secrets 管理 API KEY，或者先直接填在这里
API_KEY = "AIzaSyDqwPnBsDwoX28ny-K3o13y1BLG-TcVPfo"

client = genai.Client(api_key=API_KEY)

st.set_page_config(page_title="AI 股票智能投顾", layout="wide")

# --- 2. 核心指标计算 ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 3. 仿 App 界面设计 ---
st.title("📱 智能股票分析 App")
ticker_input = st.sidebar.text_input("输入股票代码", "NVDA")

try:
    df = yf.Ticker(ticker_input).history(period="6mo")
    if not df.empty:
        current_price = df['Close'].iloc[-1]
        rsi = calculate_rsi(df['Close']).iloc[-1]

        col1, col2 = st.columns(2)
        col1.metric("当前现价", f"${current_price:.2f}")
        col2.metric("RSI 指标", f"{rsi:.2f}")

        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        st.plotly_chart(fig, use_container_width=True)

        if st.button("🚀 获取 AI 深度诊断", use_container_width=True):
            with st.spinner("AI 正在分析..."):
                try:
                    response = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=f"分析股票 {ticker_input}: 现价 {current_price}, RSI {rsi}。请给中文建议。"
                    )
                    st.info(response.text)
                except Exception as e:
                    st.error(f"AI 诊断暂时不可用: {e}")
    else:
        st.warning("请检查股票代码输入是否正确。")
except Exception as e:
    st.error(f"加载失败: {e}")