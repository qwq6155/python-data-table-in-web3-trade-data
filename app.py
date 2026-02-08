import streamlit as st
import pandas as pd
import plotly.express as px
import time

# 导入你刚才写好的抓取函数
# 注意：listener.py 必须和 app.py 在同一个文件夹
from listener import fetch_swaps

# --- 页面基础设置 ---

st.set_page_config(
    page_title="🦄 Uniswap V2 实时监控看板",
    page_icon="📊",
    layout="wide"
)

# --- 标题区 ---
st.title("🦄 Uniswap V2 (USDC/ETH) 链上数据分析师")
st.markdown("此看板实时监听以太坊主网，捕捉 Uniswap V2 上的每一笔 Swap 交易。")

# --- 侧边栏：控制台 ---
st.sidebar.header("🎛️ 控制面板")
st.sidebar.write("调整参数并点击刷新")

# 滑块：选择回溯多少个区块
lookback = st.sidebar.slider("回溯区块数量 (Lookback)", min_value=10, max_value=200, value=50)
# 输入框：定义什么是“大户”
whale_threshold = st.sidebar.number_input("大户阈值 (USD)", min_value=1000, value=10000, step=1000)

# 刷新按钮
if st.sidebar.button("🚀 刷新数据", type="primary"):

    with st.spinner(f'正在从链上抓取过去 {lookback} 个区块的数据，请稍候...'):
        # 调用你的爬虫脚本
        df = fetch_swaps(lookback)

        # 模拟一点加载感
        time.sleep(0.5)

    if not df.empty:
        # --- 第一部分：核心指标 (KPI) ---
        st.subheader("📈 核心市场指标")
        col1, col2, col3, col4 = st.columns(4)

        # 计算最新价格
        latest_price = df.iloc[-1]['price']
        # 计算总交易量
        total_volume = df['usdc_amount'].sum()
        # 买单数量 vs 卖单数量
        buy_count = len(df[df['action'] == "Buy ETH"])
        sell_count = len(df[df['action'] == "Sell ETH"])

        col1.metric("当前 ETH 价格", f"${latest_price:,.2f}")
        col2.metric("期间总交易量", f"${total_volume:,.0f}")
        col3.metric("🟢 买单 (Buy)", f"{buy_count} 笔")
        col4.metric("🔴 卖单 (Sell)", f"{sell_count} 笔")

        st.divider()  # 分割线

        # --- 第二部分：图表分析 ---
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("📊 价格走势 (Block Level)")
            # 价格折线图
            fig_price = px.line(df, x="block", y="price",
                                title="ETH/USDC 价格波动", markers=True)
            st.plotly_chart(fig_price, use_container_width=True)

        with col_right:
            st.subheader("🐋 大户分布 (散点图)")
            # 气泡图：横轴是时间，纵轴是金额，颜色代表买卖
            fig_scatter = px.scatter(df, x="block", y="usdc_amount",
                                     size="usdc_amount", color="action",
                                     hover_data=['tx_hash'],
                                     title=f"交易金额分布 (气泡大小=金额)",
                                     color_discrete_map={"Buy ETH": "green", "Sell ETH": "red"})
            st.plotly_chart(fig_scatter, use_container_width=True)

        # --- 第三部分：大户预警 ---
        st.subheader(f"🚨 大户监控 (单笔 > ${whale_threshold})")

        # 筛选大户
        whales = df[df['usdc_amount'] >= whale_threshold]

        if not whales.empty:
            st.warning(f"发现 {len(whales)} 笔大额交易！")
            # 展示表格，并高亮最大的一笔
            st.dataframe(
                whales[['block', 'action', 'eth_amount', 'usdc_amount', 'price', 'tx_hash']].style.highlight_max(axis=0,
                                                                                                                 color='lightgreen'),
                use_container_width=True
            )
        else:
            st.success("🌊 风平浪静，暂无巨鲸出没")

        # --- 第四部分：原始数据 ---
        with st.expander("查看所有原始数据"):
            st.dataframe(df)

    else:
        st.error("⚠️ 当前范围内未抓取到数据，请尝试增大‘回溯区块数量’。")

else:
    st.info("👈 请点击左侧侧边栏的 **‘刷新数据’** 按钮开始分析。")
