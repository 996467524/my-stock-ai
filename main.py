import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from openai import OpenAI  # 使用 OpenAI 兼容库调用 DeepSeek

# --- 1. 配置 DeepSeek API ---
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    st.error("❌ 未在 Secrets 中配置 DEEPSEEK_API_KEY")
    st.stop()

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

st.set_page_config(page_title="AI 股票智能投顾 (DeepSeek版)", layout="wide")

# --- 2. 核心指标计算 ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 3. 仿 App 界面设计 ---
st.title("📈 股票智能诊断 (DeepSeek 驱动)")
ticker_input = st.sidebar.text_input("股票代码 (如 NVDA, AAPL)", "NVDA")

try:
    df = yf.Ticker(ticker_input).history(period="6mo")
    if not df.empty:
        df['RSI'] = calculate_rsi(df['Close'])
        current_price = df['Close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]

        col1, col2 = st.columns(2)
        col1.metric("当前价格", f"${current_price:.2f}")
        col2.metric("RSI (14) 指标", f"{current_rsi:.2f}")

        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close']
        )])
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width='stretch')

        # --- 4. DeepSeek 诊断按钮 ---
        if st.button("🚀 获取 DeepSeek 深度诊断", width='stretch'):
            with st.spinner("DeepSeek 正在深度分析中..."):
                try:
                    # 调用 DeepSeek-V3 模型 (标识符为 deepseek-chat)
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "你是一位专业的股票分析师，请根据提供的数据给出中文投资建议。"},
                            {"role": "user", "content": f"股票:{ticker_input}, 现价:{current_price:.2f}, RSI:{current_rsi:.2f}。"}
                        ],
                        stream=False
                    )
                    st.success("✅ 诊断完成：")
                    st.markdown(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"诊断失败: {e}")
    else:
        st.warning("未找到股票数据。")
except Exception as e:
    st.error(f"系统错误: {e}")