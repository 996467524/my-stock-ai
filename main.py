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
st.set_page_config(page_title="智投助手 - 专业股票分析", layout="wide", initial_sidebar_state="expanded")

# --- 2. 界面样式优化 (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_view_html=True)

# --- 3. 辅助函数 ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 4. 侧边栏配置 ---
st.sidebar.header("🔍 股票筛选")
ticker_input = st.sidebar.text_input("输入股票代码", value="NVDA", help="美股直接输入代码(如AAPL)，港股输入代码+相关后缀(如0700.HK)").upper()
period_choice = st.sidebar.selectbox("查看周期", ["1d", "5d", "1mo", "6mo", "1y"], index=3)

# --- 5. 获取实时与历史数据 ---
try:
    stock_obj = yf.Ticker(ticker_input)
    # 获取最近两天的历史数据以计算涨跌
    hist = stock_obj.history(period="2d")
    # 获取实时完整行情
    info = stock_obj.fast_info

    if not hist.empty:
        # 基础指标计算
        current_price = info.last_price
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Open'].iloc[0]
        change = current_price - prev_close
        pct_change = (change / prev_close) * 100

        # 今日详细数据 (OHLC)
        open_p = info.open if info.open else hist['Open'].iloc[-1]
        high_p = info.day_high if info.day_high else hist['High'].iloc[-1]
        low_p = info.day_low if info.day_low else hist['Low'].iloc[-1]
        volume = info.last_volume

        # --- 主页面布局 ---
        st.title(f"📊 {ticker_input} 实时行情看板")
        st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (服务器时间)")

        # 第一排：核心数据卡片
        col1, col2, col3, col4 = st.columns(4)

        # 涨跌颜色判断 (国内习惯：红涨绿跌)
        price_color = "inverse" if change < 0 else "normal"

        col1.metric("最新价", f"${current_price:.2f}", f"{change:+.2f} ({pct_change:+.2f}%)", delta_color=price_color)
        col2.metric("今日开盘", f"${open_p:.2f}")
        col3.metric("今日最高", f"${high_p:.2f}")
        col4.metric("今日最低", f"${low_p:.2f}")

        # 第二排：详细技术数据
        df_long = stock_obj.history(period="6mo")
        rsi_val = calculate_rsi(df_long['Close']).iloc[-1]

        st.markdown("---")
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.write(f"📈 **成交量:** {volume:,.0f}")
        t_col2.write(f"指标 **RSI (14):** {rsi_val:.2f}")
        t_col3.write(f"📅 **统计周期:** 最近6个月")

        # K线图
        fig = go.Figure(data=[go.Candlestick(
            x=df_long.index, open=df_long['Open'], high=df_long['High'],
            low=df_long['Low'], close=df_long['Close'],
            increasing_line_color='#ef5350', decreasing_line_color='#26a69a' # 红涨绿跌
        )])
        fig.update_layout(title=f"{ticker_input} 历史趋势图", xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

        # --- 6. DeepSeek AI 诊断 ---
        st.markdown("### 🤖 DeepSeek AI 智能诊断")
        if st.button("开始深度分析报告", type="primary", use_container_width=True):
            with st.spinner("正在召集 AI 专家进行多维度评估..."):
                try:
                    analysis_prompt = f"""
                    你是一个资深中国证券分析师。请对以下股票进行深度诊断：
                    股票代码：{ticker_input}
                    当前实时价：{current_price:.2f} (今日开盘:{open_p:.2f}, 最高:{high_p:.2f}, 最低:{low_p:.2f})
                    RSI指标：{rsi_val:.2f}
                    
                    请从技术面、动能、以及风险提示三个维度，用简洁且专业的中文给出结论。
                    """

                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "你是一位专注于全球市场的中文投顾专家，语气稳重专业。"},
                            {"role": "user", "content": analysis_prompt}
                        ]
                    )
                    st.success("诊断完成")
                    st.info(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI 诊断暂时无法完成: {e}")

    else:
        st.warning("⚠️ 无法获取该代码的数据，请检查代码是否正确（例如：美股 NVDA，港股 0700.HK）。")

except Exception as e:
    st.error(f"⚠️ 系统数据调度错误: {e}")