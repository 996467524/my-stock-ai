import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from google import genai

# --- 1. 云端安全配置 ---
# 从 Streamlit 后台的 Secrets 自动读取 Key，不再硬编码
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("未在 Secrets 中检测到 GEMINI_API_KEY，请检查配置。")
    st.stop()

# 初始化 AI 客户端（无需设置代理参数）
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
st.title("📈 AI 股票智能诊断 (云端版)")
ticker_input = st.sidebar.text_input("股票代码 (如 NVDA, AAPL)", "NVDA")

try:
    # 抓取数据（云端直连，速度极快）
    df = yf.Ticker(ticker_input).history(period="6mo")

    if not df.empty:
        df['RSI'] = calculate_rsi(df['Close'])
        current_price = df['Close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]

        # 模拟 App 卡片布局
        col1, col2 = st.columns(2)
        col1.metric("当前价格", f"${current_price:.2f}")
        col2.metric("RSI (14) 指标", f"{current_rsi:.2f}")

        # K 线展示
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close']
        )])
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # --- 4. AI 诊断按钮 ---
        if st.button("🚀 获取 AI 深度诊断", use_container_width=True):
            with st.spinner("AI 正在分析中..."):
                try:
                    prompt = f"分析股票 {ticker_input}: 现价 {current_price:.2f}, RSI {current_rsi:.2f}。请以中文给出简明投资建议。"
                    response = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=prompt
                    )
                    st.info(response.text)
                except Exception as e:
                    st.error(f"AI 连接出错，请检查 API Key 配置。")
    else:
        st.warning("未找到该股票数据，请确认代码是否正确。")
except Exception as e:
    st.error(f"系统运行出错: {e}")