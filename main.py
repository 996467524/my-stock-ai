import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from openai import OpenAI
from datetime import datetime

# --- 1. 配置 DeepSeek API ---
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    st.error("❌ 未在 Secrets 中配置 DEEPSEEK_API_KEY")
    st.stop()

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# 页面配置
st.set_page_config(page_title="智投助手 - 实时行情诊断", layout="wide")

# --- 2. 界面样式优化 (修正了之前的参数拼写错误) ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e6e9ef; }
    </style>
    """, unsafe_allow_html=True) # 这里修正了拼写错误

# --- 3. 辅助函数 ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 4. 侧边栏 ---
ticker_input = st.sidebar.text_input("股票代码", value="NVDA").upper()

# --- 5. 数据抓取与实时展示 ---
try:
    stock = yf.Ticker(ticker_input)
    # 抓取最近的历史数据 (包含当日最近的 tick)
    hist = stock.history(period="5d", interval="1d")

    if not hist.empty:
        # 获取最新的一行数据作为“当日实时”
        latest_day = hist.iloc[-1]
        prev_day = hist.iloc[-2] if len(hist) > 1 else latest_day

        cur_p = latest_day['Close']
        open_p = latest_day['Open']
        high_p = latest_day['High']
        low_p = latest_day['Low']

        # 计算涨跌 (对比前一日收盘)
        change = cur_p - prev_day['Close']
        pct_change = (change / prev_day['Close']) * 100

        # 页面标题
        st.title(f"📊 {ticker_input} 实时看板")

        # 第一排：实时行情 OHLC
        # 国内习惯红涨绿跌，但 Streamlit 的 delta 颜色 normal=绿涨, inverse=红涨
        # 为了符合国内习惯，我们手动根据涨跌设置 delta_color
        d_color = "normal" if change >= 0 else "inverse"

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("最新价", f"${cur_p:.2f}", f"{change:+.2f} ({pct_change:+.2f}%)", delta_color=d_color)
        c2.metric("今日开盘", f"${open_p:.2f}")
        c3.metric("今日最高", f"${high_p:.2f}")
        c4.metric("今日最低", f"${low_p:.2f}")
        c5.metric("成交量", f"{latest_day['Volume']:,.0f}")

        st.divider()

        # 第二排：图表与技术指标
        full_hist = stock.history(period="6mo")
        rsi_val = calculate_rsi(full_hist['Close']).iloc[-1]

        # K线图 (修正警告：使用 width='stretch')
        fig = go.Figure(data=[go.Candlestick(
            x=full_hist.index, open=full_hist['Open'], high=full_hist['High'],
            low=full_hist['Low'], close=full_hist['Close'],
            increasing_line_color='#ef5350', decreasing_line_color='#26a69a' # 红涨绿跌
        )])
        fig.update_layout(xaxis_rangeslider_visible=False, height=450, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, width='stretch')

        # --- 6. AI 诊断 ---
        st.subheader("🤖 DeepSeek 智能分析报告")
        if st.button("生成深度诊断报告", type="primary"):
            with st.spinner("AI 正在扫描盘面..."):
                try:
                    prompt = f"""
                    股票：{ticker_input}
                    最新价：{cur_p:.2f} (今日最高:{high_p:.2f}, 最低:{low_p:.2f})
                    RSI(14)：{rsi_val:.2f}
                    请根据以上数据提供简洁的中文投资建议，包括压力位、支撑位分析。
                    """
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.success("分析完成")
                    st.info(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI 服务异常: {e}")
    else:
        st.warning("查无此股，请检查代码。")
except Exception as e:
    st.error(f"数据加载错误: {e}")