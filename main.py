import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from google import genai

# --- 1. 安全配置 (由 Streamlit Secrets 提供) ---
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("❌ 未在 Secrets 中配置 GEMINI_API_KEY，请在 Streamlit 后台检查配置。")
    st.stop()

# 初始化客户端：强制指定 v1beta 路径，这是 2025 年新 Key 最兼容的路径
client = genai.Client(
    api_key=API_KEY,
    http_options={'api_version': 'v1beta'}
)

st.set_page_config(page_title="AI 股票智能投顾", layout="wide")

# --- 2. 核心指标计算 ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 3. 仿 App 界面设计 ---
st.title("📈 AI 股票智能诊断 (云端正式版)")
ticker_input = st.sidebar.text_input("股票代码 (如 NVDA, AAPL, TSLA)", "NVDA")

try:
    # 抓取数据 (云端直连)
    df = yf.Ticker(ticker_input).history(period="6mo")

    if not df.empty:
        df['RSI'] = calculate_rsi(df['Close'])
        current_price = df['Close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]

        # 布局
        col1, col2 = st.columns(2)
        col1.metric("当前价格", f"${current_price:.2f}")
        col2.metric("RSI (14) 指标", f"{current_rsi:.2f}")

        # K 线展示 (修复 width 弃用警告)
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close']
        )])
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width='stretch')

        # --- 4. AI 诊断按钮 ---
        if st.button("🚀 获取 AI 深度诊断", width='stretch'):
            with st.spinner("AI 正在根据实时数据生成建议..."):
                try:
                    prompt = f"分析股票 {ticker_input}: 现价 {current_price:.2f}, RSI 指标 {current_rsi:.2f}。请以中文给出专业的投资建议。"

                    # 【关键修复】：使用 models/ 前缀补全模型路径
                    response = client.models.generate_content(
                        model="models/gemini-1.5-flash",
                        contents=prompt
                    )

                    st.success("✅ AI 诊断完成：")
                    st.markdown(response.text)

                except Exception as e:
                    # 如果仍然报错，将显示具体的错误代码，方便最终调试
                    st.error(f"诊断失败。错误详情: {e}")
                    st.info("💡 请确保已在 Secrets 中填入最新的 API Key (TOML 格式)。")
    else:
        st.warning("未找到该股票数据，请确认代码是否输入正确。")
except Exception as e:
    st.error(f"系统运行出错: {e}")