import streamlit as st
import subprocess
import json
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_lottie import st_lottie
import requests
import os
import re
from datetime import datetime
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import sys
import streamlit.components.v1 as components

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入akshare配置模块
try:
    from src.tools.akshare_config import configure_akshare_timeout
    # 设置akshare超时时间为30秒
    configure_akshare_timeout(30)
    print("已设置akshare超时时间为30秒")
except ImportError:
    print("未找到akshare_config模块，将使用默认超时设置")

# 导入akshare库
try:
    import akshare as ak
except ImportError:
    st.error("未找到akshare库，请确保已安装: `pip install akshare`")

# 验证股票代码格式
def validate_ticker(ticker):
    """
    验证股票代码格式是否有效

    Args:
        ticker: 股票代码

    Returns:
        bool: 股票代码格式是否有效
    """
    # 检查是否为6位数字
    if not ticker or not re.match(r'^\d{6}$', ticker):
        return False

    # 检查前缀是否有效（沪市以6或9开头，深市以0或3开头，北交所以8开头）
    first_digit = ticker[0]
    if first_digit not in ['0', '3', '6', '8', '9']:
        return False

    return True

# 添加生成HTML报告的函数
def generate_html_report(ticker, stock_name, action, quantity, confidence, reasoning, agent_signals, sections, report_text, position_ratio, holding_cost, risk_tolerance, investment_horizon):
    """生成HTML格式的分析报告"""
    # 设置报告的样式
    report_style = """
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1, h2, h3 { color: #2c3e50; }
        h1 { border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; margin-top: 30px; }
        .summary-box { background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; }
        .decision { font-size: 24px; font-weight: bold; margin: 10px 0; }
        .buy { color: #e74c3c; }  /* 红色 - 买入 */
        .sell { color: #2ecc71; }  /* 绿色 - 卖出 */
        .hold { color: #f39c12; }  /* 黄色 - 持有 */
        .signal-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .signal-table th, .signal-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .signal-table th { background-color: #f2f2f2; }
        .bullish { color: #e74c3c; }  /* 红色 - 看涨 */
        .bearish { color: #2ecc71; }  /* 绿色 - 看跌 */
        .neutral { color: #f39c12; }  /* 黄色 - 中性 */
        .section { margin: 20px 0; }
        .footer { margin-top: 50px; font-size: 12px; color: #7f8c8d; text-align: center; }
    </style>
    """

    # 设置决策类别的样式
    decision_class = "buy" if action == "buy" else "sell" if action == "sell" else "hold"

    # 转换action为中文
    action_map = {"buy": "买入", "sell": "卖出", "hold": "持有"}
    action_zh = action_map.get(action, action)

    # 生成信号表格HTML
    signals_html = ""
    for signal in agent_signals:
        agent_name = signal.get("agent_name", "未知")
        signal_value = signal.get("signal", "neutral")
        signal_confidence = signal.get("confidence", 0.0)

        # 转换agent_name为中文
        agent_name_map = {
            "valuation_analysis": "估值分析",
            "sentiment_analysis": "情绪分析",
            "fundamental_analysis": "基本面分析",
            "technical_analysis": "技术分析"
        }
        agent_name_zh = agent_name_map.get(agent_name, agent_name)

        # 转换signal为中文
        signal_map = {
            "bullish": "看涨",
            "bearish": "看跌",
            "neutral": "中性"
        }
        signal_value_zh = signal_map.get(signal_value, signal_value)

        # 设置信号类别
        signal_class = "bullish" if signal_value == "bullish" else "bearish" if signal_value == "bearish" else "neutral"

        signals_html += f"""
        <tr>
            <td>{agent_name_zh}</td>
            <td class="{signal_class}">{signal_value_zh}</td>
            <td>{signal_confidence:.2f}</td>
        </tr>
        """

    # 生成各部分分析HTML
    sections_html = ""
    for section_name, section_content in sections.items():
        # 转换section_name为中文
        section_name_map = {
            "fundamental_analysis": "基本面分析",
            "technical_analysis": "技术分析",
            "sentiment_analysis": "情绪分析",
            "risk_assessment": "风险评估"
        }
        section_name_zh = section_name_map.get(section_name, section_name)

        sections_html += f"""
        <div class="section">
            <h2>{section_name_zh}</h2>
            <p>{section_content}</p>
        </div>
        """

    # 生成完整的HTML报告
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>投资分析报告 - {ticker} {stock_name}</title>
        {report_style}
    </head>
    <body>
        <h1>投资分析报告 - {ticker} {stock_name}</h1>

        <div class="summary-box">
            <h2>决策摘要</h2>
            <p class="decision {decision_class}">{action_zh}，建议仓位: {position_ratio}%，置信度: {confidence:.2f}</p>
            <p><strong>当前仓位:</strong> {position_ratio}%</p>
            <p><strong>持仓成本:</strong> {holding_cost} 元/股</p>
            <p><strong>风险承受能力:</strong> {risk_tolerance}</p>
            <p><strong>投资期限:</strong> {investment_horizon}</p>
        </div>

        <h2>信号分析</h2>
        <table class="signal-table">
            <tr>
                <th>分析类型</th>
                <th>信号</th>
                <th>置信度</th>
            </tr>
            {signals_html}
        </table>

        <h2>推理过程</h2>
        <div class="section">
            <p>{reasoning}</p>
        </div>

        <h2>详细分析</h2>
        {sections_html}

        <div class="footer">
            <p>© 2025 智能投资决策系统 | 基于人工智能的A股投资分析工具</p>
            <p>免责声明：本系统提供的分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """

    return html_report

# 设置页面配置
st.set_page_config(
    page_title="智能投资决策系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化会话状态
if 'run_id' not in st.session_state:
    st.session_state.run_id = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'log_output' not in st.session_state:
    st.session_state.log_output = []
if 'history' not in st.session_state:
    st.session_state.history = []
if 'view_full_log' not in st.session_state:
    st.session_state.view_full_log = False
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False
if 'reset_requested' not in st.session_state:
    st.session_state.reset_requested = False

# 如果请求了重置，执行重置操作
if st.session_state.reset_requested:
    # 清除缓存
    st.cache_data.clear()
    # 重置状态
    st.session_state.analysis_complete = False
    st.session_state.analysis_result = None
    st.session_state.progress = 0
    st.session_state.log_output = []
    st.session_state.run_id = None
    # 重置标志
    st.session_state.reset_requested = False
    # 显示成功消息
    st.success("应用已重置，缓存已清除！")

# 定义回调函数
def request_reset():
    st.session_state.reset_requested = True

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .card {
        border-radius: 10px;
        padding: 20px;
        background-color: #f8f9fa;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .info-box {
        background-color: #e3f2fd;
        border-left: 5px solid #1E88E5;
        padding: 10px 15px;
        margin-bottom: 15px;
        border-radius: 0 5px 5px 0;
    }
    .success-box {
        background-color: #e8f5e9;
        border-left: 5px solid #4CAF50;
        padding: 10px 15px;
        margin-bottom: 15px;
        border-radius: 0 5px 5px 0;
    }
    .warning-box {
        background-color: #fff8e1;
        border-left: 5px solid #FFC107;
        padding: 10px 15px;
        margin-bottom: 15px;
        border-radius: 0 5px 5px 0;
    }
    .danger-box {
        background-color: #ffebee;
        border-left: 5px solid #F44336;
        padding: 10px 15px;
        margin-bottom: 15px;
        border-radius: 0 5px 5px 0;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E88E5;
    }
    .metric-label {
        font-size: 1rem;
        color: #616161;
    }
    .progress-container {
        margin-top: 20px;
        margin-bottom: 40px;
    }
    .analysis-section {
        margin-top: 30px;
        margin-bottom: 30px;
    }
    .signal-bullish {
        color: #FF4136;  /* 红色 - 看涨 */
        font-weight: bold;
    }
    .signal-bearish {
        color: #2ECC40;  /* 绿色 - 看跌 */
        font-weight: bold;
    }
    .signal-neutral {
        color: #FFC107;  /* 黄色 - 中性 */
        font-weight: bold;
    }
    .footer {
        text-align: center;
        margin-top: 50px;
        padding: 20px;
        color: #9e9e9e;
        font-size: 0.8rem;
    }
    .stProgress > div > div > div > div {
        background-color: #1E88E5;
    }
    .stock-card {
        background: linear-gradient(135deg, #0D47A1 0%, #1976D2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stock-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .stock-info {
        display: flex;
        justify-content: space-between;
        margin-top: 10px;
    }
    .stock-info-item {
        text-align: center;
    }
    .stock-info-value {
        font-size: 1.2rem;
        font-weight: bold;
    }
    .stock-info-label {
        font-size: 0.8rem;
        opacity: 0.8;
    }
    .log-container {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        max-height: 300px;
        overflow-y: auto;
        overflow-x: hidden;
    }
    .log-line {
        padding: 3px 0;
        border-bottom: 1px solid #eee;
        white-space: pre-wrap;
        word-break: break-word;
    }
    .api-request-box {
        background-color: #e3f2fd;
        border-left: 5px solid #2196F3;
        padding: 10px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    .spinner {
        width: 16px;
        height: 16px;
        border: 2px solid #999;
        border-top: 2px solid #1E88E5;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
</style>
""", unsafe_allow_html=True)

# 加载动画
@st.cache_data
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# 加载动画资源
lottie_analysis = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_qp1q7mct.json")
lottie_success = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_jvkzwngh.json")

# 侧边栏
with st.sidebar:
    # 添加logo和标题
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <div style="font-size: 1.8rem; font-weight: bold; background: linear-gradient(90deg, #4CAF50, #1E88E5, #F44336); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            <span style="font-size: 2rem;">📊</span> 智能投资决策系统
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height: 2px; background: linear-gradient(to right, #4CAF50, #1E88E5, #F44336); margin: 10px 0 25px 0; border-radius: 2px;"></div>', unsafe_allow_html=True)

    # 创建主要参数区域
    st.markdown('<div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 15px; color: #1E88E5;"><span style="margin-right: 8px;">📝</span>基本参数</div>', unsafe_allow_html=True)

    # 股票代码输入
    ticker = st.text_input("股票代码", value="600519", help="输入6位股票代码，如：600519", placeholder="请输入股票代码")

    # 验证股票代码格式
    if ticker and not validate_ticker(ticker):
        st.warning("请输入有效的股票代码格式（6位数字，沪市以6或9开头，深市以0或3开头，北交所以8开头）")

    # 仓位占比设置
    position_ratio = st.slider("仓位占比", min_value=1, max_value=100, value=30, step=1, help="设置投资仓位占总资金的百分比")

    # 持仓成本设置
    holding_cost = st.number_input("持仓成本", min_value=0.0, max_value=10000.0, value=0.0, step=0.01, help="如有持仓，请输入持仓成本价，无持仓则保持为0")

    # 新闻数量设置
    num_of_news = st.slider("分析新闻数量", min_value=1, max_value=20, value=5, help="设置要分析的相关新闻数量")

    # 是否显示推理过程
    show_reasoning = st.checkbox("显示推理过程", value=True, help="是否显示AI推理过程")

    # 高级设置折叠面板
    with st.expander("🔧 高级设置", expanded=False):
        st.markdown('<div style="font-size: 1rem; font-weight: bold; margin-bottom: 15px; color: #1E88E5;">高级参数配置</div>', unsafe_allow_html=True)

        risk_tolerance = st.select_slider(
            "风险承受能力",
            options=["保守", "适中", "激进"],
            value="适中",
            help="设置您的风险承受能力"
        )

        investment_horizon = st.select_slider(
            "投资期限",
            options=["短期", "中期", "长期"],
            value="中期",
            help="设置您的投资期限"
        )

    # 添加分隔线
    st.markdown('<div style="height: 2px; background: linear-gradient(to right, #e0e0e0, #9E9E9E, #e0e0e0); margin: 25px 0; border-radius: 2px;"></div>', unsafe_allow_html=True)

    # 系统设置标题
    st.markdown('<div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 15px; color: #1E88E5;"><span style="margin-right: 8px;">⚙️</span>系统设置</div>', unsafe_allow_html=True)

    # 添加清除缓存按钮（使用回调函数）
    st.button("清除缓存并重置",
              help="清除所有缓存数据并重置应用",
              on_click=request_reset,
              use_container_width=True,
              type="primary")

    # 添加调试模式开关
    st.session_state.debug_mode = st.checkbox("调试模式",
                                             value=st.session_state.debug_mode,
                                             help="开启调试模式，显示更多技术细节")

    # 添加页脚
    st.markdown('<div style="height: 2px; background: linear-gradient(to right, #e0e0e0, #9E9E9E, #e0e0e0); margin: 25px 0 15px 0; border-radius: 2px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.8rem; color: #888; text-align: center; margin-top: 20px;">© 2025 智能投资决策系统<br>基于人工智能的A股投资分析工具</div>', unsafe_allow_html=True)

# 主页面
st.title("智能投资决策系统")

# 添加股票卡片样式
st.markdown("""
<style>
.stock-card {
    background: linear-gradient(135deg, #0D47A1 0%, #1976D2 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.stock-title {
    font-size: 1.5rem;
    font-weight: bold;
    margin-bottom: 10px;
}
.stock-info {
    display: flex;
    justify-content: space-between;
    margin-top: 10px;
}
.stock-info-item {
    text-align: center;
}
.stock-info-value {
    font-size: 1.2rem;
    font-weight: bold;
}
.stock-info-label {
    font-size: 0.8rem;
    opacity: 0.8;
}
</style>
""", unsafe_allow_html=True)

# 获取股票简称的函数
@st.cache_data(ttl=3600)  # 缓存1小时
def get_stock_name(ticker):
    """
    根据股票代码获取股票简称

    Args:
        ticker: 股票代码，如"600519"

    Returns:
        股票简称，如获取失败则返回"未知股票"
    """
    try:
        # 使用 stock_info_a_code_name 函数获取所有 A 股的代码和名称
        st.session_state.log_output.append(f"DEBUG: 正在获取股票 {ticker} 的简称...")

        # 如果缓存中没有股票信息，则获取并缓存
        if 'stock_info_df' not in st.session_state:
            st.session_state.log_output.append(f"DEBUG: 首次获取所有股票代码和名称...")
            st.session_state.stock_info_df = ak.stock_info_a_code_name()
            st.session_state.log_output.append(f"DEBUG: 成功获取所有股票代码和名称")

        # 查找对应的股票
        stock_info = st.session_state.stock_info_df[st.session_state.stock_info_df['code'] == ticker]
        if not stock_info.empty:
            stock_name = stock_info['name'].values[0]
            st.session_state.log_output.append(f"DEBUG: 成功获取股票简称: {stock_name}")
            return stock_name
        st.session_state.log_output.append(f"DEBUG: 未找到股票代码 {ticker} 对应的简称")
        return "未知股票"
    except Exception as e:
        st.session_state.log_output.append(f"ERROR: 获取股票简称时出错: {str(e)}")
        return "未知股票"

@st.cache_data(ttl=3600)  # 缓存1小时
def get_realtime_data():
    """
    获取所有A股实时行情数据，并缓存结果

    Returns:
        DataFrame: 包含所有A股实时行情数据的DataFrame
    """
    try:
        # 检查是否在 Streamlit 环境中运行
        is_streamlit_env = hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists()

        # 安全地记录日志
        def log_message(message):
            if is_streamlit_env and hasattr(st, 'session_state') and hasattr(st.session_state, 'log_output'):
                st.session_state.log_output.append(message)
            print(message)  # 同时打印到控制台

        log_message(f"DEBUG: 获取所有A股实时行情数据...")
        realtime_data = ak.stock_zh_a_spot_em()
        log_message(f"DEBUG: 成功获取所有A股实时行情数据")
        return realtime_data
    except Exception as e:
        message = f"ERROR: 获取实时行情数据时出错: {str(e)}"
        if hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists() and hasattr(st, 'session_state') and hasattr(st.session_state, 'log_output'):
            st.session_state.log_output.append(message)
        print(message)
        return pd.DataFrame()

@st.cache_data(ttl=86400)  # 缓存24小时
def get_financial_indicator(symbol, start_year):
    """
    获取指定股票的财务指标数据，并缓存结果

    Args:
        symbol: 股票代码
        start_year: 开始年份

    Returns:
        DataFrame: 包含财务指标数据的DataFrame
    """
    try:
        # 检查是否在 Streamlit 环境中运行
        is_streamlit_env = hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists()

        # 安全地记录日志
        def log_message(message):
            if is_streamlit_env and hasattr(st, 'session_state') and hasattr(st.session_state, 'log_output'):
                st.session_state.log_output.append(message)
            print(message)  # 同时打印到控制台

        log_message(f"DEBUG: 获取股票 {symbol} 的财务指标数据...")
        financial_data = ak.stock_financial_analysis_indicator(symbol=symbol, start_year=start_year)
        log_message(f"DEBUG: 成功获取股票 {symbol} 的财务指标数据")
        return financial_data
    except Exception as e:
        message = f"ERROR: 获取财务指标数据时出错: {str(e)}"
        if hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists() and hasattr(st, 'session_state') and hasattr(st.session_state, 'log_output'):
            st.session_state.log_output.append(message)
        print(message)
        return pd.DataFrame()

@st.cache_data(ttl=86400)  # 缓存24小时
def get_latest_financial_report_date():
    """
    获取最新的财务报表发布日期

    Returns:
        str: 最新的财务报表发布日期，格式为YYYY-MM-DD
    """
    try:
        # 检查是否在 Streamlit 环境中运行
        is_streamlit_env = hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists()

        # 安全地记录日志
        def log_message(message):
            if is_streamlit_env and hasattr(st, 'session_state') and hasattr(st.session_state, 'log_output'):
                st.session_state.log_output.append(message)
            print(message)  # 同时打印到控制台

        # 获取当前日期
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        # 确定最新的财报季度
        if current_month >= 1 and current_month < 4:
            # 1-3月，最新财报应该是去年第三季度报告
            report_year = current_year - 1
            report_date = f"{report_year}-09-30"
        elif current_month >= 4 and current_month < 8:
            # 4-7月，最新财报应该是去年年报
            report_year = current_year - 1
            report_date = f"{report_year}-12-31"
        elif current_month >= 8 and current_month < 11:
            # 8-10月，最新财报应该是今年第一季度报告
            report_date = f"{current_year}-03-31"
        else:
            # 11-12月，最新财报应该是今年第二季度报告
            report_date = f"{current_year}-06-30"

        log_message(f"DEBUG: 预计最新财报日期为 {report_date}")
        return report_date
    except Exception as e:
        message = f"ERROR: 获取最新财报日期时出错: {str(e)}"
        if hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists() and hasattr(st, 'session_state') and hasattr(st.session_state, 'log_output'):
            st.session_state.log_output.append(message)
        print(message)
        return f"{datetime.now().year-1}-12-31"  # 默认返回去年年报日期

@st.cache_data(ttl=3600)  # 缓存1小时
def get_income_statement(symbol):
    """
    获取指定股票的利润表数据，并缓存结果

    Args:
        symbol: 股票代码

    Returns:
        DataFrame: 包含利润表数据的DataFrame
    """
    try:
        # 检查是否在 Streamlit 环境中运行
        is_streamlit_env = hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists()

        # 安全地记录日志
        def log_message(message):
            if is_streamlit_env and hasattr(st, 'session_state') and hasattr(st.session_state, 'log_output'):
                st.session_state.log_output.append(message)
            print(message)  # 同时打印到控制台

        log_message(f"DEBUG: 获取股票 {symbol} 的利润表数据...")
        # 判断股票代码前缀
        prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
        income_statement = ak.stock_financial_report_sina(stock=f"{prefix}{symbol}", symbol="利润表")
        log_message(f"DEBUG: 成功获取股票 {symbol} 的利润表数据")
        return income_statement
    except Exception as e:
        message = f"ERROR: 获取利润表数据时出错: {str(e)}"
        if hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists() and hasattr(st, 'session_state') and hasattr(st.session_state, 'log_output'):
            st.session_state.log_output.append(message)
        print(message)
        return pd.DataFrame()

@st.cache_data(ttl=3600)  # 缓存1小时
def get_financial_metrics_cached(symbol):
    """
    获取财务指标数据的缓存版本

    Args:
        symbol: 股票代码，如"600519"

    Returns:
        Dict: 包含财务指标数据的字典
    """
    try:
        # 检查是否在 Streamlit 环境中运行
        is_streamlit_env = hasattr(st, 'runtime') and hasattr(st.runtime, 'exists') and st.runtime.exists()

        # 安全地记录日志
        def log_message(message):
            if is_streamlit_env and hasattr(st, 'session_state') and hasattr(st.session_state, 'log_output'):
                st.session_state.log_output.append(message)
            print(message)  # 同时打印到控制台

        log_message(f"DEBUG: 正在获取 {symbol} 的财务指标数据(缓存版)...")

        # 获取实时行情数据
        realtime_data = get_realtime_data()
        if realtime_data is None or realtime_data.empty:
            log_message(f"WARNING: 无法获取实时行情数据")
            return [{}]

        stock_data = realtime_data[realtime_data['代码'] == symbol]
        if stock_data.empty:
            log_message(f"WARNING: 未找到股票 {symbol} 的实时行情数据")
            return [{}]

        stock_data = stock_data.iloc[0]

        # 获取新浪财务指标
        current_year = datetime.now().year
        financial_data = get_financial_indicator(symbol, str(current_year-2))  # 获取近两年的数据，确保有足够的历史数据
        if financial_data is None or financial_data.empty:
            log_message(f"WARNING: 无法获取新浪财务指标数据")
            return [{}]

        # 按日期排序并获取最新的数据
        financial_data['日期'] = pd.to_datetime(financial_data['日期'])
        financial_data = financial_data.sort_values('日期', ascending=False)
        latest_financial = financial_data.iloc[0] if not financial_data.empty else pd.Series()

        # 获取最新财报预期日期
        expected_latest_date = get_latest_financial_report_date()
        actual_latest_date = latest_financial.get('日期').strftime('%Y-%m-%d') if not financial_data.empty and '日期' in latest_financial else "未知"

        # 检查数据是否最新
        if actual_latest_date != "未知":
            actual_date = datetime.strptime(actual_latest_date, '%Y-%m-%d')
            expected_date = datetime.strptime(expected_latest_date, '%Y-%m-%d')
            date_diff = (expected_date - actual_date).days

            if date_diff > 90:  # 如果数据滞后超过90天
                log_message(f"WARNING: 财务数据可能不是最新的。最新数据日期: {actual_latest_date}，预期最新日期: {expected_latest_date}")
            else:
                log_message(f"INFO: 财务数据日期: {actual_latest_date}，符合预期的最新财报周期")

        # 获取利润表数据
        income_statement = get_income_statement(symbol)
        latest_income = income_statement.iloc[0] if not income_statement.empty else pd.Series()

        # 构建完整指标数据
        def convert_percentage(value):
            """将百分比值转换为小数"""
            try:
                return float(value) / 100.0 if value is not None else 0.0
            except:
                return 0.0

        all_metrics = {
            # 市场数据
            "market_cap": float(stock_data.get("总市值", 0)),
            "float_market_cap": float(stock_data.get("流通市值", 0)),

            # 盈利数据
            "revenue": float(latest_income.get("营业总收入", 0)),
            "net_income": float(latest_income.get("净利润", 0)),
            "return_on_equity": convert_percentage(latest_financial.get("净资产收益率(%)", 0)),
            "net_margin": convert_percentage(latest_financial.get("销售净利率(%)", 0)),
            "operating_margin": convert_percentage(latest_financial.get("营业利润率(%)", 0)),

            # 增长指标
            "revenue_growth": convert_percentage(latest_financial.get("主营业务收入增长率(%)", 0)),
            "earnings_growth": convert_percentage(latest_financial.get("净利润增长率(%)", 0)),
            "book_value_growth": convert_percentage(latest_financial.get("净资产增长率(%)", 0)),

            # 财务健康指标
            "current_ratio": float(latest_financial.get("流动比率", 0)),
            "debt_to_equity": convert_percentage(latest_financial.get("资产负债率(%)", 0)),
            "free_cash_flow_per_share": float(latest_financial.get("每股经营性现金流(元)", 0)),
            "earnings_per_share": float(latest_financial.get("加权每股收益(元)", 0)),

            # 估值比率
            "pe_ratio": float(stock_data.get("市盈率-动态", 0)),
            "price_to_book": float(stock_data.get("市净率", 0)),
            "price_to_sales": float(stock_data.get("总市值", 0)) / float(latest_income.get("营业总收入", 1)) if float(latest_income.get("营业总收入", 0)) > 0 else 0,

            # 数据日期信息
            "data_date": actual_latest_date,
            "expected_latest_date": expected_latest_date
        }

        # 只返回 agent 需要的指标
        agent_metrics = {
            # 盈利能力指标
            "return_on_equity": all_metrics["return_on_equity"],
            "net_margin": all_metrics["net_margin"],
            "operating_margin": all_metrics["operating_margin"],

            # 增长指标
            "revenue_growth": all_metrics["revenue_growth"],
            "earnings_growth": all_metrics["earnings_growth"],
            "book_value_growth": all_metrics["book_value_growth"],

            # 财务健康指标
            "current_ratio": all_metrics["current_ratio"],
            "debt_to_equity": all_metrics["debt_to_equity"],
            "free_cash_flow_per_share": all_metrics["free_cash_flow_per_share"],
            "earnings_per_share": all_metrics["earnings_per_share"],

            # 估值比率
            "pe_ratio": all_metrics["pe_ratio"],
            "price_to_book": all_metrics["price_to_book"],
            "price_to_sales": all_metrics["price_to_sales"],

            # 数据日期信息
            "data_date": all_metrics["data_date"],
            "expected_latest_date": all_metrics["expected_latest_date"]
        }

        log_message(f"DEBUG: 成功构建 {symbol} 的财务指标数据(缓存版)")
        return [agent_metrics]

    except Exception as e:
        log_message(f"ERROR: 获取财务指标时出错: {str(e)}")
        return [{}]

# 显示股票卡片（无论是否已运行分析）
if ticker and validate_ticker(ticker):
    # 获取股票简称
    with st.spinner("正在获取股票信息..."):
        stock_name = get_stock_name(ticker)

    # 如果分析已完成，尝试从日志中提取更准确的股票名称
    if st.session_state.analysis_complete:
        for line in st.session_state.log_output:
            if "股票名称" in line:
                name_match = re.search(r'股票名称[：:]\s*(.+)', line)
                if name_match:
                    stock_name = name_match.group(1)
                    break

    # 显示股票信息获取状态
    if stock_name == "未知股票":
        st.warning(f"未能获取到股票 {ticker} 的简称信息，请确认股票代码是否正确")

    # 显示股票卡片
    st.markdown(f"""
    <div class="stock-card">
        <div class="stock-title">{stock_name} ({ticker})</div>
        <div class="stock-info">
            <div class="stock-info-item">
                <div class="stock-info-value">{position_ratio}%</div>
                <div class="stock-info-label">仓位占比</div>
            </div>
            <div class="stock-info-item">
                <div class="stock-info-value">{holding_cost:.2f}</div>
                <div class="stock-info-label">持仓成本</div>
            </div>
            <div class="stock-info-item">
                <div class="stock-info-value">{datetime.now().strftime('%Y-%m-%d')}</div>
                <div class="stock-info-label">分析日期</div>
            </div>
            <div class="stock-info-item">
                <div class="stock-info-value">{risk_tolerance}</div>
                <div class="stock-info-label">风险偏好</div>
            </div>
            <div class="stock-info-item">
                <div class="stock-info-value">{investment_horizon}</div>
                <div class="stock-info-label">投资期限</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 创建分析按钮
run_button = st.button("开始分析", key="run_analysis", help="点击开始分析", use_container_width=True)

# 添加日志过滤和美化函数
def format_log_line(log_line):
    """格式化日志行，添加颜色和图标"""
    # 过滤掉一些不必要的API调用日志
    if "api_calls" in log_line and any(x in log_line for x in ["DEBUG", "INFO - 请求内容", "INFO - 请求配置"]):
        return None

    # 隐藏用户路径信息 - 使用正则表达式匹配更多可能的路径格式
    # 匹配绝对路径
    log_line = re.sub(r'/home/[^/]+/[^/]+/[^/]+/A_Share_investment_Agent/?', '[项目路径]/', log_line)
    # 匹配任何包含用户名的路径
    log_line = re.sub(r'/home/[^/]+/', '[用户目录]/', log_line)
    # 匹配包含workspace的路径
    log_line = re.sub(r'workspace/github-experiments/A_Share_investment_Agent/?', '[项目路径]/', log_line)

    # 处理长行，将时间戳和日志级别分离出来
    if len(log_line) > 30 and " - " in log_line:
        parts = log_line.split(" - ", 2)
        if len(parts) >= 3:
            timestamp = parts[0]
            module = parts[1]
            content = parts[2]
            # 只保留时间部分，去掉日期
            if ":" in timestamp:
                time_only = timestamp.split(" ")[1]
                log_line = f"{time_only} | {module} | {content}"

    # 为不同类型的日志添加颜色和图标
    if "ERROR" in log_line:
        return f"🔴 {log_line}"
    elif "WARNING" in log_line:
        return f"⚠️ {log_line}"
    elif "SUCCESS" in log_line:
        return f"✅ {log_line}"
    elif "基本面分析" in log_line:
        return f"📊 {log_line}"
    elif "技术分析" in log_line:
        return f"📈 {log_line}"
    elif "情绪分析" in log_line:
        return f"😀 {log_line}"
    elif "风险管理" in log_line:
        return f"⚖️ {log_line}"
    elif "投资组合管理" in log_line:
        return f"🎯 {log_line}"
    else:
        return f"ℹ️ {log_line}"

# 当点击运行按钮时
if run_button:
    st.session_state.run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state.analysis_complete = False
    st.session_state.analysis_result = None
    st.session_state.progress = 0
    st.session_state.log_output = []

    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()

    # 显示分析中的动画
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                if lottie_analysis is not None:
                    st_lottie(lottie_analysis, height=200, key="analysis_animation")
                else:
                    st.info("正在分析中，请稍候...")
            except Exception as e:
                st.info("正在分析中，请稍候...")

    # 准备命令行参数
    cmd_args = [
        "python", "src/main.py",
        "--ticker", ticker,
        "--position-ratio", str(position_ratio),
        "--holding-cost", str(holding_cost),
        "--num-of-news", str(num_of_news)
    ]

    if show_reasoning:
        cmd_args.append("--show-reasoning")

    # 添加超时处理
    cmd_args = ["timeout", "300"] + cmd_args  # 设置5分钟超时

    # 创建日志容器
    log_title = st.empty()
    log_container = st.empty()

    # 显示日志标题
    log_title.markdown("<h3 style='margin-top:20px;'>📋 运行日志</h3>", unsafe_allow_html=True)

    # 添加查看完整日志的按钮（只在分析完成后显示）
    view_full_log_button = st.empty()

    # 分析阶段和进度
    analysis_stages = [
        ("收集市场数据", 0.1),
        ("分析基本面", 0.3),
        ("评估技术指标", 0.5),
        ("分析市场情绪", 0.7),
        ("风险评估", 0.8),
        ("生成投资决策", 0.9),
        ("完成分析", 1.0)
    ]

    # API请求状态指示器
    api_request_indicator = st.empty()

    # 添加API请求计数器
    api_request_count = 0
    last_api_update_time = time.time()

    stage_index = 0
    current_stage, target_progress = analysis_stages[stage_index]

    # 更新状态文本
    status_text.markdown(f"<div class='info-box'>正在{current_stage}...</div>", unsafe_allow_html=True)

    # 读取输出并更新进度
    logs = []
    last_update_time = time.time()
    timeout_seconds = 60  # 设置超时时间为60秒

    try:
        # 检查环境变量是否正确设置
        if not os.path.exists('.env'):
            raise Exception("未找到.env文件，请确保环境变量已正确配置")

        # 检查API密钥是否设置
        with open('.env', 'r') as f:
            env_content = f.read()
            if 'OPENAI_API_KEY=' not in env_content or 'OPENAI_API_KEY=your_api_key_here' in env_content:
                raise Exception("API密钥未正确设置，请在.env文件中配置OPENAI_API_KEY")

        # 运行命令并捕获输出
        try:
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
        except Exception as e:
            raise Exception(f"启动分析进程失败: {str(e)}")

        # 设置全局超时
        start_time = time.time()
        max_execution_time = 300  # 5分钟全局超时

        # 分析阶段和进度
        analysis_stages = [
            ("收集市场数据", 0.1),
            ("分析基本面", 0.3),
            ("评估技术指标", 0.5),
            ("分析市场情绪", 0.7),
            ("风险评估", 0.8),
            ("生成投资决策", 0.9),
            ("完成分析", 1.0)
        ]

        stage_index = 0
        current_stage, target_progress = analysis_stages[stage_index]

        # 更新状态文本
        status_text.markdown(f"<div class='info-box'>正在{current_stage}...</div>", unsafe_allow_html=True)

        # 读取输出并更新进度
        logs = []
        last_update_time = time.time()
        timeout_seconds = 60  # 设置超时时间为60秒

        try:
            for line in iter(process.stdout.readline, ''):
                logs.append(line.strip())
                st.session_state.log_output.append(line.strip())

                # 更新最后活动时间
                last_update_time = time.time()

                # 检测API请求
                if ("api_calls" in line and ("请求内容" in line or "请求配置" in line)) or "使用工具" in line:
                    api_request_count += 1
                    last_api_update_time = time.time()

                    # 提取当前阶段信息
                    stage_info = current_stage
                    if "基本面分析" in line:
                        stage_info = "基本面分析"
                    elif "技术分析" in line:
                        stage_info = "技术分析"
                    elif "情绪分析" in line:
                        stage_info = "情绪分析"
                    elif "风险管理" in line:
                        stage_info = "风险管理"
                    elif "投资组合管理" in line:
                        stage_info = "投资决策"

                    # 更新API请求状态指示器
                    api_request_indicator.markdown(f"""
                    <div class="api-request-box">
                        <div style="display:flex; align-items:center;">
                            <div style="margin-right:15px;">
                                <div class="spinner"></div>
                            </div>
                            <div>
                                <strong>AI正在思考中...</strong><br>
                                <small>正在进行{stage_info}，大型语言模型正在处理复杂数据，请耐心等待</small>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # 检测API响应
                if "api_calls" in line and ("API 调用成功" in line or "SUCCESS" in line):
                    # 清除API请求状态指示器
                    api_request_indicator.empty()

                # 检查API请求是否超时
                current_time = time.time()
                if api_request_count > 0 and current_time - last_api_update_time > 30:
                    # 更新API请求状态指示器，显示等待时间
                    wait_time = int(current_time - last_api_update_time)
                    api_request_indicator.markdown(f"""
                    <div class="api-request-box" style="background-color:#fff8e1; border-left:5px solid #FFC107;">
                        <div style="display:flex; align-items:center;">
                            <div style="margin-right:15px;">
                                <div class="spinner"></div>
                            </div>
                            <div>
                                <strong>AI仍在思考中...</strong><br>
                                <small>已等待 {wait_time} 秒，复杂的分析可能需要1-2分钟，请继续等待</small>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 如果等待超过2分钟，显示更详细的提示
                    if wait_time > 120:
                        api_request_indicator.markdown(f"""
                        <div class="api-request-box" style="background-color:#ffebee; border-left:5px solid #F44336;">
                            <div style="display:flex; align-items:center;">
                                <div style="margin-right:15px;">
                                    <div class="spinner"></div>
                                </div>
                                <div>
                                    <strong>AI处理时间较长...</strong><br>
                                    <small>已等待 {wait_time} 秒，当前网络或服务器可能较忙，请继续等待或考虑稍后再试</small>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    last_api_update_time = current_time

                # 更新日志显示，处理长行文本并美化
                formatted_logs = []
                for log_line in logs[-20:]:  # 显示更多行
                    formatted_line = format_log_line(log_line)
                    if formatted_line:  # 如果不是被过滤的行
                        formatted_logs.append(formatted_line)

                # 使用markdown而不是code来显示，以支持emoji
                if formatted_logs:
                    log_html = f"""
                    <div class='log-container' id='log-container'>
                    <div style="text-align:right; margin-bottom:5px; font-size:0.8rem; color:#666;">
                        显示最近 {len(formatted_logs)} 条日志，共 {len(logs)} 条
                    </div>
                    """
                    for log in formatted_logs:
                        log_html += f"<div class='log-line'>{log}</div>"
                    log_html += """
                    </div>
                    <script>
                        // 自动滚动到底部
                        var logContainer = document.getElementById('log-container');
                        if (logContainer) {
                            logContainer.scrollTop = logContainer.scrollHeight;
                        }
                    </script>
                    """
                    log_container.markdown(log_html, unsafe_allow_html=True)

                # 检查是否应该更新阶段
                if "基本面分析" in line and stage_index < 1:
                    stage_index = 1
                    current_stage, target_progress = analysis_stages[stage_index]
                    status_text.markdown(f"<div class='info-box'>正在{current_stage}...</div>", unsafe_allow_html=True)
                elif "技术分析" in line and stage_index < 2:
                    stage_index = 2
                    current_stage, target_progress = analysis_stages[stage_index]
                    status_text.markdown(f"<div class='info-box'>正在{current_stage}...</div>", unsafe_allow_html=True)
                elif "情绪分析" in line and stage_index < 3:
                    stage_index = 3
                    current_stage, target_progress = analysis_stages[stage_index]
                    status_text.markdown(f"<div class='info-box'>正在{current_stage}...</div>", unsafe_allow_html=True)
                elif "风险管理" in line and stage_index < 4:
                    stage_index = 4
                    current_stage, target_progress = analysis_stages[stage_index]
                    status_text.markdown(f"<div class='info-box'>正在{current_stage}...</div>", unsafe_allow_html=True)
                elif "投资组合管理" in line and stage_index < 5:
                    stage_index = 5
                    current_stage, target_progress = analysis_stages[stage_index]
                    status_text.markdown(f"<div class='info-box'>正在{current_stage}...</div>", unsafe_allow_html=True)

                # 缓慢增加进度，直到目标进度
                if st.session_state.progress < target_progress:
                    st.session_state.progress += 0.005
                    progress_bar.progress(st.session_state.progress)
                    time.sleep(0.05)

                # 检查是否超时
                current_time = time.time()
                if current_time - last_update_time > timeout_seconds:
                    # 如果超过60秒没有新的输出，强制进入下一阶段
                    if stage_index < len(analysis_stages) - 1:
                        stage_index += 1
                        current_stage, target_progress = analysis_stages[stage_index]
                        status_text.markdown(f"<div class='warning-box'>正在{current_stage}...(自动前进)</div>", unsafe_allow_html=True)
                        last_update_time = current_time  # 重置超时计时器
                        st.warning(f"数据处理超时，已自动进入下一阶段: {current_stage}")
                    else:
                        # 如果已经是最后一个阶段，则结束处理
                        break

                # 检查全局超时
                if time.time() - start_time > max_execution_time:
                    st.error("分析执行时间超过5分钟，已自动终止。请检查网络连接或稍后再试。")
                    logs.append("ERROR: 分析执行时间超过5分钟，已自动终止")
                    st.session_state.log_output.append("ERROR: 分析执行时间超过5分钟，已自动终止")
                    break

                # 检查是否包含决策结果
                if "Final Result:" in line:
                    # 获取下一行，这应该是JSON结果
                    try:
                        # 查找"Final Result:"后面的内容
                        result_index = logs.index(line)
                        if result_index < len(logs) - 1:
                            # 获取下一行
                            result_line = logs[result_index + 1].strip()

                            # 添加调试信息
                            st.session_state.log_output.append(f"DEBUG: 找到决策结果行: {result_line}")

                            # 尝试解析JSON
                            try:
                                # 如果结果行是JSON格式
                                if result_line.startswith('{') and result_line.endswith('}'):
                                    parsed_result = json.loads(result_line)
                                    if all(k in parsed_result for k in ["action", "quantity", "confidence"]):
                                        st.session_state.analysis_result = parsed_result
                                        st.session_state.log_output.append(f"DEBUG: 成功解析决策结果: action={parsed_result['action']}")
                                    else:
                                        st.session_state.log_output.append(f"WARNING: 解析的JSON缺少必要字段: {parsed_result}")
                                else:
                                    # 尝试在行中查找JSON对象
                                    json_match = re.search(r'({.*})', result_line)
                                    if json_match:
                                        json_str = json_match.group(1)
                                        parsed_result = json.loads(json_str)
                                        if all(k in parsed_result for k in ["action", "quantity", "confidence"]):
                                            st.session_state.analysis_result = parsed_result
                                            st.session_state.log_output.append(f"DEBUG: 从行中提取并解析决策结果: action={parsed_result['action']}")
                                        else:
                                            st.session_state.log_output.append(f"WARNING: 从行中提取的JSON缺少必要字段: {parsed_result}")
                            except json.JSONDecodeError as je:
                                st.session_state.log_output.append(f"WARNING: JSON解析失败: {str(je)}")
                        else:
                            st.session_state.log_output.append(f"WARNING: 找到'Final Result:'但没有后续行")
                    except ValueError as ve:
                        # 处理'Final Result:\n' is not in list错误
                        error_detail = f"解析决策结果时出错: {str(ve)}。可能是'Final Result:'行格式不正确"
                        st.session_state.log_output.append(f"ERROR: {error_detail}")

                        # 尝试查找包含"Final Result:"的行
                        for i, log_line in enumerate(logs):
                            if "Final Result:" in log_line:
                                st.session_state.log_output.append(f"DEBUG: 找到包含'Final Result:'的行: {log_line}, 索引: {i}")
                                if i < len(logs) - 1:
                                    result_line = logs[i + 1].strip()
                                    st.session_state.log_output.append(f"DEBUG: 下一行内容: {result_line}")
                                    try:
                                        if result_line.startswith('{') and result_line.endswith('}'):
                                            parsed_result = json.loads(result_line)
                                            if all(k in parsed_result for k in ["action", "quantity", "confidence"]):
                                                st.session_state.analysis_result = parsed_result
                                                st.session_state.log_output.append(f"DEBUG: 通过备用索引方法解析决策结果: action={parsed_result['action']}")
                                                break
                                    except json.JSONDecodeError:
                                        pass
                    except Exception as e:
                        # 更详细的错误信息
                        error_detail = f"解析决策结果时出错: {str(e)}。日志行: {line}"
                        st.session_state.log_output.append(f"ERROR: {error_detail}")

            # 如果上述方法都失败，尝试直接从所有日志中查找JSON对象
            if not hasattr(st.session_state, 'analysis_result') or st.session_state.analysis_result is None:
                st.session_state.log_output.append("DEBUG: 尝试备用方法查找决策结果")
                try:
                    for log_line in logs:
                        log_line = log_line.strip()
                        if log_line.startswith('{') and log_line.endswith('}'):
                            try:
                                parsed_result = json.loads(log_line)
                                if all(k in parsed_result for k in ["action", "quantity", "confidence"]):
                                    st.session_state.analysis_result = parsed_result
                                    st.session_state.log_output.append(f"DEBUG: 通过备用方法找到决策结果: action={parsed_result['action']}")
                                    break
                            except json.JSONDecodeError:
                                continue
                except Exception as backup_error:
                    st.session_state.log_output.append(f"ERROR: 备用解析方法也失败: {str(backup_error)}")
        except Exception as e:
            st.error(f"处理输出时出错: {str(e)}")
            # 记录错误到日志
            error_msg = f"ERROR: 处理输出时出错: {str(e)}"
            logs.append(error_msg)
            st.session_state.log_output.append(error_msg)

            # 确保即使出错也显示一些日志信息
            if len(logs) == 0:
                logs.append("未能捕获到任何输出，请检查后台运行状态")
                st.session_state.log_output.append("未能捕获到任何输出，请检查后台运行状态")

            log_container.markdown("\n".join([format_log_line(log) for log in logs[-15:] if format_log_line(log)]))

        # 确保进程已结束
        try:
            process.wait(timeout=5)  # 等待进程结束，最多5秒
        except Exception:
            # 如果进程没有正常结束，强制终止
            process.terminate()
            st.warning("分析进程未正常结束，已强制终止")
            logs.append("WARNING: 分析进程未正常结束，已强制终止")
            st.session_state.log_output.append("WARNING: 分析进程未正常结束，已强制终止")

        # 确保进度达到100%
        progress_bar.progress(1.0)
        stage_index = 6
        current_stage, target_progress = analysis_stages[stage_index]
        status_text.markdown(f"<div class='success-box'>{current_stage}</div>", unsafe_allow_html=True)

        # 清除API请求状态指示器
        api_request_indicator.empty()

        # 标记分析完成
        st.session_state.analysis_complete = True

        # 分析完成后显示成功动画
        if st.session_state.analysis_complete:
            success_container = st.container()
            with success_container:
                if lottie_success is not None:
                    st_lottie(lottie_success, height=200, key="success_animation")
                else:
                    st.success("分析已完成！")

            # 显示分析结果
            if "analysis_result" in st.session_state and st.session_state.analysis_result:
                result = st.session_state.analysis_result

                # 添加调试信息
                if st.session_state.debug_mode:
                    st.markdown("### 调试信息")
                    st.code(f"原始结果: {result}")

                    # 直接从JSON中提取关键信息，不做任何转换
                    action_raw = result.get("action", "未知")
                    quantity = result.get("quantity", 0)
                    confidence = result.get("confidence", 0.0)
                    reasoning = result.get("reasoning", "")
                    agent_signals = result.get("agent_signals", [])

                    st.markdown(f"提取的action值: `{action_raw}`")

                    # 转换action为中文，确保与JSON一致
                    action_map = {"buy": "买入", "sell": "卖出", "hold": "持有"}
                    action_zh = action_map.get(action_raw, action_raw)

                    st.markdown(f"转换后的中文action值: `{action_zh}`")

                    # 设置颜色
                    action_color = "#FF4136" if action_raw == "buy" else "#2ECC40" if action_raw == "sell" else "#FFC107"

                    st.markdown("---")
                else:
                    # 直接从JSON中提取关键信息，不做任何转换
                    action_raw = result.get("action", "未知")
                    quantity = result.get("quantity", 0)
                    confidence = result.get("confidence", 0.0)
                    reasoning = result.get("reasoning", "")
                    agent_signals = result.get("agent_signals", [])

                    # 转换action为中文，确保与JSON一致
                    action_map = {"buy": "买入", "sell": "卖出", "hold": "持有"}
                    action_zh = action_map.get(action_raw, action_raw)

                    # 设置颜色
                    action_color = "#FF4136" if action_raw == "buy" else "#2ECC40" if action_raw == "sell" else "#FFC107"

                # # 创建主要结果展示区域
                # st.markdown(f"""
                # <div style="background-color:#f8f9fa; padding:20px; border-radius:10px; margin-bottom:20px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                #     <h2 style="text-align:center; margin-bottom:20px; color:{action_color};">分析结果: {action_zh}</h2>
                #     <div style="display:flex; justify-content:space-around; align-items:center;">
                #         <div style="text-align:center;">
                #             <div style="font-size:2.5rem; font-weight:bold; color:{action_color};">{action_zh}</div>
                #             <div style="color:#666; margin-top:5px;">交易行动</div>
                #         </div>
                #         <div style="text-align:center;">
                #             <div style="font-size:2rem; font-weight:bold;">{position_ratio}%</div>
                #             <div style="color:#666; margin-top:5px;">建议仓位</div>
                #         </div>
                #         <div style="text-align:center;">
                #             <div style="font-size:2rem; font-weight:bold;">{confidence:.2f}</div>
                #             <div style="color:#666; margin-top:5px;">置信度</div>
                #         </div>
                #     </div>
                #     <div style="margin-top:20px; padding:15px; background-color:#fff; border-radius:5px; border-left:4px solid {action_color};">
                #         <p style="font-style:italic;">{reasoning}</p>
                #     </div>
                # </div>
                # """, unsafe_allow_html=True)

                # # 显示原始JSON结果（可折叠）
                # with st.expander("查看原始JSON结果", expanded=False):
                #     st.json(result)

                # 创建信号分析部分
                st.markdown("### 信号分析")

                # 添加调试信息
                if st.session_state.debug_mode:
                    st.markdown("#### 原始信号数据")
                    st.code(f"agent_signals: {agent_signals}")

                # 创建信号表格
                signal_data = []
                for signal in agent_signals:
                    agent_name = signal.get("agent_name", "未知")
                    signal_value = signal.get("signal", "neutral")
                    signal_confidence = signal.get("confidence", 0.0)

                    if st.session_state.debug_mode:
                        st.markdown(f"信号数据: agent_name=`{agent_name}`, signal=`{signal_value}`, confidence=`{signal_confidence}`")

                    # 转换agent_name为中文
                    agent_name_map = {
                        "valuation_analysis": "估值分析",
                        "valuation": "估值分析",
                        "sentiment_analysis": "情绪分析",
                        "sentiment": "情绪分析",
                        "fundamental_analysis": "基本面分析",
                        "fundamental": "基本面分析",
                        "technical_analysis": "技术分析",
                        "technical": "技术分析"
                    }
                    agent_name_zh = agent_name_map.get(agent_name, agent_name)

                    # 转换signal为中文，保持与原始值一致
                    signal_map = {
                        "bullish": "看涨",
                        "bearish": "看跌",
                        "neutral": "中性"
                    }
                    signal_value_zh = signal_map.get(signal_value, signal_value)

                    # 设置信号颜色
                    signal_color = "#FF4136" if signal_value == "bullish" else "#2ECC40" if signal_value == "bearish" else "#FFC107"

                    signal_data.append({
                        "分析类型": agent_name_zh,
                        "信号": signal_value_zh,
                        "信号颜色": signal_color,
                        "置信度": signal_confidence
                    })

                # 创建2x2网格布局
                col1, col2 = st.columns(2)

                with col1:
                    # 决策摘要区域 - 使用更简单的方式显示
                    st.markdown(f"""
                    <div style="background-color:#f8f9fa; padding:20px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.1); margin-bottom:20px;">
                        <h3 style="color:#1E88E5; border-bottom:2px solid #1E88E5; padding-bottom:10px; margin-bottom:15px;">决策摘要</h3>
                        <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                            <div style="text-align:center; flex:1;">
                                <div style="font-size:1.8rem; font-weight:bold; color:{action_color};">{action_zh}</div>
                                <div style="color:#666; font-size:0.9rem;">交易行动</div>
                            </div>
                            <div style="text-align:center; flex:1;">
                                <div style="font-size:1.8rem; font-weight:bold;">{position_ratio}%</div>
                                <div style="color:#666; font-size:0.9rem;">建议仓位</div>
                            </div>
                            <div style="text-align:center; flex:1;">
                                <div style="font-size:1.8rem; font-weight:bold;">{confidence:.2f}</div>
                                <div style="color:#666; font-size:0.9rem;">置信度</div>
                            </div>
                        </div>
                        <div style="background-color:white; padding:15px; border-radius:5px; border-left:4px solid {action_color};">
                            <p style="margin:0; font-style:italic;">{reasoning}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 信号强度雷达图
                    st.markdown("""
                    <div style="background-color:#f8f9fa; padding:20px; border-radius:10px; height:100%; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                        <h3 style="color:#1E88E5; border-bottom:2px solid #1E88E5; padding-bottom:10px; margin-bottom:15px;">信号强度雷达图</h3>
                    """, unsafe_allow_html=True)

                    # 准备雷达图数据
                    categories = []
                    values = []

                    for signal in agent_signals:
                        agent_name = signal.get("agent_name", "未知")
                        agent_name_map = {
                            "valuation_analysis": "估值",
                            "valuation": "估值",
                            "sentiment_analysis": "情绪",
                            "sentiment": "情绪",
                            "fundamental_analysis": "基本面",
                            "fundamental": "基本面",
                            "technical_analysis": "技术",
                            "technical": "技术"
                        }
                        agent_name_zh = agent_name_map.get(agent_name, agent_name)

                        # 将信号转换为数值
                        signal_value = signal.get("signal", "neutral")
                        signal_map = {
                            "bullish": 1.0,
                            "bearish": -1.0,
                            "neutral": 0.0
                        }
                        signal_numeric = signal_map.get(signal_value, 0.0)

                        # 考虑置信度
                        signal_confidence = signal.get("confidence", 0.5)
                        weighted_signal = signal_numeric * signal_confidence

                        categories.append(agent_name_zh)
                        values.append(abs(weighted_signal))  # 使用绝对值表示强度

                    # 确保有数据
                    if categories and values:
                        # 添加第一个类别以闭合雷达图
                        categories.append(categories[0])
                        values.append(values[0])

                        # 创建雷达图
                        fig = go.Figure()

                        fig.add_trace(go.Scatterpolar(
                            r=values,
                            theta=categories,
                            fill='toself',
                            name='信号强度',
                            line=dict(color='rgba(32, 128, 255, 0.8)', width=2),
                            fillcolor='rgba(32, 128, 255, 0.3)'
                        ))

                        fig.update_layout(
                            polar=dict(
                                radialaxis=dict(
                                    visible=True,
                                    range=[0, 1]
                                )
                            ),
                            showlegend=False,
                            margin=dict(l=20, r=20, t=20, b=20),
                            height=300
                        )

                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("无足够数据生成雷达图")

                    st.markdown("</div>", unsafe_allow_html=True)

                with col2:
                    # 信号分析表格
                    st.markdown("""
                    <div style="background-color:#f8f9fa; padding:20px; border-radius:10px; height:100%; box-shadow:0 2px 5px rgba(0,0,0,0.1); margin-bottom:20px;">
                        <h3 style="color:#1E88E5; border-bottom:2px solid #1E88E5; padding-bottom:10px; margin-bottom:15px;">信号分析</h3>
                    """, unsafe_allow_html=True)

                    # 显示信号表格
                    if signal_data:
                        # 创建简单的表格
                        st.markdown("""
                        <style>
                        .dataframe {
                            width: 100%;
                            border-collapse: collapse;
                            font-family: Arial, sans-serif;
                            margin-bottom: 20px;
                        }
                        .dataframe th {
                            background-color: #1E88E5;
                            color: white;
                            padding: 10px;
                            text-align: left;
                            border-radius: 5px 5px 0 0;
                        }
                        .dataframe td {
                            padding: 10px;
                            border-bottom: 1px solid #f0f0f0;
                        }
                        .dataframe tr:nth-child(even) {
                            background-color: #f5f5f5;
                        }
                        .dataframe tr:hover {
                            background-color: #f0f0f0;
                        }
                        .signal-bullish {
                            color: #FF4136;  /* 红色 - 看涨 */
                            font-weight: bold;
                        }
                        .signal-bearish {
                            color: #2ECC40;  /* 绿色 - 看跌 */
                            font-weight: bold;
                        }
                        .signal-neutral {
                            color: #FFC107;  /* 黄色 - 中性 */
                            font-weight: bold;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                        # 创建表格数据
                        table_data = []
                        for signal in signal_data:
                            signal_text = signal["信号"]
                            signal_class = ""
                            if signal_text == "看涨":
                                signal_class = "signal-bullish"
                            elif signal_text == "看跌":
                                signal_class = "signal-bearish"
                            else:
                                signal_class = "signal-neutral"

                            table_data.append({
                                "分析类型": signal["分析类型"],
                                "信号": f'<span class="{signal_class}">{signal_text}</span>',
                                "置信度": f'{signal["置信度"]:.2f}'
                            })

                        # 创建DataFrame
                        df = pd.DataFrame(table_data)

                        # 显示表格
                        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
                    else:
                        st.info("无信号数据可显示")

                    st.markdown("</div>", unsafe_allow_html=True)

                    # 信号类型分布饼图
                    st.markdown("""
                    <div style="background-color:#f8f9fa; padding:20px; border-radius:10px; height:100%; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                        <h3 style="color:#1E88E5; border-bottom:2px solid #1E88E5; padding-bottom:10px; margin-bottom:15px;">信号类型分布</h3>
                    """, unsafe_allow_html=True)

                    # 统计不同类型的信号
                    signal_counts = {"看涨": 0, "看跌": 0, "中性": 0}

                    for signal in agent_signals:
                        signal_value = signal.get("signal", "neutral")
                        signal_map = {
                            "bullish": "看涨",
                            "bearish": "看跌",
                            "neutral": "中性"
                        }
                        signal_value_zh = signal_map.get(signal_value, "中性")
                        signal_counts[signal_value_zh] += 1

                    # 创建饼图
                    if sum(signal_counts.values()) > 0:
                        fig = go.Figure(data=[go.Pie(
                            labels=list(signal_counts.keys()),
                            values=list(signal_counts.values()),
                            hole=.3,
                            marker_colors=['#FF4136', '#2ECC40', '#FFC107'],
                            textinfo='label+percent',
                            textposition='outside',
                            pull=[0.1 if k == "看涨" else 0.1 if k == "看跌" else 0 for k in signal_counts.keys()]
                        )])

                        fig.update_layout(
                            showlegend=True,
                            margin=dict(l=20, r=20, t=20, b=20),
                            height=300
                        )

                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("无足够数据生成饼图")

                    st.markdown("</div>", unsafe_allow_html=True)

                # 添加详细分析折叠面板
                with st.expander("查看详细分析", expanded=False):
                    # 创建四个标签页
                    detail_tab1, detail_tab2, detail_tab3, detail_tab4 = st.tabs(["基本面分析", "技术分析", "情绪分析", "风险评估"])

                    # 预处理日志，按类型分组
                    analysis_content = {
                        "基本面分析": [],
                        "技术分析": [],
                        "情绪分析": [],
                        "风险评估": []
                    }

                    current_type = None
                    for line in st.session_state.log_output:
                        if "基本面分析" in line and ":" in line:
                            current_type = "基本面分析"
                            content = line.split(":", 1)[1].strip()
                            if content:  # 只添加非空内容
                                analysis_content[current_type].append(content)
                        elif "技术分析" in line and ":" in line:
                            current_type = "技术分析"
                            content = line.split(":", 1)[1].strip()
                            if content:
                                analysis_content[current_type].append(content)
                        elif "情绪分析" in line and ":" in line:
                            current_type = "情绪分析"
                            content = line.split(":", 1)[1].strip()
                            if content:
                                analysis_content[current_type].append(content)
                        elif ("风险管理" in line or "风险评估" in line) and ":" in line:
                            current_type = "风险评估"
                            content = line.split(":", 1)[1].strip()
                            if content:
                                analysis_content[current_type].append(content)
                        elif current_type and ":" in line and not any(x in line for x in ["基本面分析", "技术分析", "情绪分析", "风险管理", "风险评估"]):
                            # 这是前一个分析类型的继续内容
                            content = line.split(":", 1)[1].strip()
                            if content:
                                analysis_content[current_type].append(content)

                    with detail_tab1:
                        # 显示基本面分析信息
                        if analysis_content["基本面分析"]:
                            st.markdown("\n\n".join(analysis_content["基本面分析"]))
                        else:
                            st.info("未找到基本面分析信息")

                    with detail_tab2:
                        # 显示技术分析信息
                        if analysis_content["技术分析"]:
                            st.markdown("\n\n".join(analysis_content["技术分析"]))
                        else:
                            st.info("未找到技术分析信息")

                    with detail_tab3:
                        # 显示情绪分析信息
                        if analysis_content["情绪分析"]:
                            st.markdown("\n\n".join(analysis_content["情绪分析"]))
                        else:
                            st.info("未找到情绪分析信息")

                    with detail_tab4:
                        # 显示风险评估信息
                        if analysis_content["风险评估"]:
                            st.markdown("\n\n".join(analysis_content["风险评估"]))
                        else:
                            st.info("未找到风险评估信息")

                # 添加下载报告按钮
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    # 提取各部分分析内容
                    sections = {}
                    for section_type in ["基本面分析", "技术分析", "情绪分析", "风险管理"]:
                        content = ""
                        for line in st.session_state.log_output:
                            if section_type in line and ":" in line:
                                content += line.split(":", 1)[1].strip() + "\n\n"
                        if content:
                            sections[section_type] = content

                    # 生成HTML报告
                    html_report = generate_html_report(
                        ticker=ticker,
                        stock_name=stock_name,
                        action=action_raw,  # 使用action_raw代替action
                        quantity=position_ratio,  # 使用仓位比例代替数量
                        confidence=confidence,
                        reasoning=reasoning,
                        agent_signals=agent_signals,
                        sections=sections,
                        report_text="",
                        position_ratio=position_ratio,
                        holding_cost=holding_cost,
                        risk_tolerance=risk_tolerance,
                        investment_horizon=investment_horizon
                    )

                    # 添加下载按钮
                    st.download_button(
                        label="📊 导出分析报告",
                        data=html_report,
                        file_name=f"投资分析报告_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                        mime="text/html",
                        use_container_width=True
                    )

                # 保存分析历史
                if ticker not in [h['ticker'] for h in st.session_state.history]:
                    st.session_state.history.append({
                        'ticker': ticker,
                        'stock_name': stock_name,
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'action': action_zh,
                        'quantity': position_ratio,
                        'confidence': confidence
                    })

    except Exception as e:
        st.error(f"运行分析时出错: {str(e)}")
        # 即使出错也记录到历史
        if ticker not in [h['ticker'] for h in st.session_state.history]:
            st.session_state.history.append({
                'ticker': ticker,
                'stock_name': stock_name,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'action': '失败',
                'quantity': 0,
                'confidence': 0,
                'error': str(e)
            })

# 在侧边栏添加历史记录显示
with st.sidebar.expander("📜 历史分析记录", expanded=False):
    st.markdown('<div style="font-size: 1rem; font-weight: bold; margin-bottom: 15px; color: #1E88E5;">您的分析历史记录</div>', unsafe_allow_html=True)

    if st.session_state.history:
        for idx, record in enumerate(st.session_state.history):
            action = record.get('action', '未知')
            action_color = "#FF4136" if action == "买入" else "#2ECC40" if action == "卖出" else "#FFC107" if action == "持有" else "#9E9E9E"

            # 检查是否是失败记录
            if action == '失败':
                action_color = "#9E9E9E"
                error_msg = record.get('error', '未知错误')
                st.markdown(f"""
                <div style="margin-bottom:15px; padding:12px; border-radius:8px; background-color:#f8f9fa; border-left:3px solid {action_color};">
                    <div style="font-weight:bold;">{record['ticker']}</div>
                    <div style="font-size:0.8rem; color:#666;">{record['date']}</div>
                    <div style="margin-top:5px;">
                        <span style="color:{action_color}; font-weight:bold;">分析失败</span>
                        <div style="font-size:0.8rem; color:#F44336; margin-top:5px; word-break:break-word;">{error_msg[:50]}...</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="margin-bottom:15px; padding:12px; border-radius:8px; background-color:#f8f9fa; border-left:3px solid {action_color};">
                    <div style="font-weight:bold;">{record['ticker']} {record.get('stock_name', '')}</div>
                    <div style="font-size:0.8rem; color:#666;">{record['date']}</div>
                    <div style="margin-top:5px;">
                        <span style="color:{action_color}; font-weight:bold;">{action}</span>
                        <span style="margin-left:10px;">{record.get('quantity', 0)} 股</span>
                        <span style="margin-left:10px; font-size:0.8rem;">置信度: {record.get('confidence', 0):.2f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("暂无历史记录")

# 添加系统诊断功能
with st.sidebar.expander("🔍 系统诊断", expanded=False):
    st.markdown('<div style="font-size: 1rem; font-weight: bold; margin-bottom: 15px; color: #1E88E5;">系统状态检查</div>', unsafe_allow_html=True)

    if st.button("运行系统诊断", key="run_diagnostics", use_container_width=True, type="primary"):
        st.write("正在检查系统状态...")

        # 检查环境变量
        env_status = "✅ 已找到" if os.path.exists('.env') else "❌ 未找到"

        # 检查API密钥
        api_key_status = "❌ 未设置"
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                env_content = f.read()
                if 'OPENAI_API_KEY=' in env_content and 'OPENAI_API_KEY=your_api_key_here' not in env_content:
                    api_key_status = "✅ 已设置"

        # 检查日志目录
        logs_dir_status = "✅ 已找到" if os.path.exists('logs') else "❌ 未找到"

        # 显示系统状态
        st.markdown(f"""
        <div style="margin-top:15px; background-color:#f8f9fa; padding:15px; border-radius:8px; border-left:3px solid #1E88E5;">
            <div style="margin-bottom:8px;"><span style="font-weight:bold; color:#1E88E5;">环境文件:</span> {env_status}</div>
            <div style="margin-bottom:8px;"><span style="font-weight:bold; color:#1E88E5;">API密钥:</span> {api_key_status}</div>
            <div><span style="font-weight:bold; color:#1E88E5;">日志目录:</span> {logs_dir_status}</div>
        </div>
        """, unsafe_allow_html=True)

# 页脚
st.markdown("""
<div class="footer">
    <p>© 2025 智能投资决策系统 | 基于人工智能的A股投资分析工具</p>
    <p>免责声明：本系统提供的分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
</div>
""", unsafe_allow_html=True)