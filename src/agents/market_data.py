from langchain_core.messages import HumanMessage
from src.tools.openrouter_config import get_chat_completion

from src.agents.state import AgentState
from src.tools.api import get_financial_metrics, get_financial_statements, get_market_data, get_price_history

from datetime import datetime, timedelta
import pandas as pd


def market_data_agent(state: AgentState):
    """Responsible for gathering and preprocessing market data"""
    messages = state["messages"]
    data = state["data"]

    # Set default dates
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)
    end_date = data["end_date"] or yesterday.strftime('%Y-%m-%d')

    # Ensure end_date is not in the future
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    if end_date_obj > yesterday:
        end_date = yesterday.strftime('%Y-%m-%d')
        end_date_obj = yesterday

    if not data["start_date"]:
        # Calculate 1 year before end_date
        start_date = end_date_obj - timedelta(days=365)  # 默认获取一年的数据
        start_date = start_date.strftime('%Y-%m-%d')
    else:
        start_date = data["start_date"]

    # Get all required data
    ticker = data["ticker"]

    # 获取价格数据并验证
    prices_df = get_price_history(ticker, start_date, end_date)
    if prices_df is None or prices_df.empty:
        print(f"警告：无法获取{ticker}的价格数据，将使用空数据继续")
        prices_df = pd.DataFrame(
            columns=['close', 'open', 'high', 'low', 'volume'])

    # 获取财务指标
    try:
        financial_metrics = get_financial_metrics(ticker)
    except Exception as e:
        print(f"获取财务指标失败: {str(e)}")
        financial_metrics = {}

    # 获取财务报表
    try:
        financial_line_items = get_financial_statements(ticker)
    except Exception as e:
        print(f"获取财务报表失败: {str(e)}")
        financial_line_items = {}

    # 获取市场数据
    try:
        market_data = get_market_data(ticker)
    except Exception as e:
        print(f"获取市场数据失败: {str(e)}")
        market_data = {"market_cap": 0}

    # 确保数据格式正确
    if not isinstance(prices_df, pd.DataFrame):
        prices_df = pd.DataFrame(
            columns=['close', 'open', 'high', 'low', 'volume'])

    # 优化价格数据，减少重复信息
    # 1. 只保留必要的列
    essential_columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'pct_change']
    technical_columns = ['momentum_1m', 'momentum_3m', 'momentum_6m', 'historical_volatility',
                        'volume_momentum', 'atr_ratio']

    # 2. 创建精简版价格数据
    compact_prices = []
    if not prices_df.empty:
        # 保留所有列但转换为更紧凑的格式
        for _, row in prices_df.iterrows():
            price_entry = {}

            # 基本价格数据 - 使用更短的键名
            if 'date' in row:
                price_entry['dt'] = row['date'].strftime('%Y-%m-%d')

            for col in ['open', 'close', 'high', 'low']:
                if col in row:
                    # 保留两位小数，减少数据量
                    price_entry[col[0]] = round(float(row[col]), 2)

            # 成交量使用缩写并转换为整数
            if 'volume' in row:
                price_entry['v'] = int(row['volume'])

            # 涨跌幅保留两位小数
            if 'pct_change' in row:
                price_entry['chg'] = round(float(row['pct_change']), 2)

            # 只添加非空的技术指标
            for col in technical_columns:
                if col in row and not pd.isna(row[col]):
                    # 使用缩写并保留三位小数
                    short_name = ''.join([c for c in col if c.isupper() or c.isdigit()]) or col[:3]
                    price_entry[short_name] = round(float(row[col]), 3)

            compact_prices.append(price_entry)

    # 优化财务指标数据
    compact_financials = {}
    if financial_metrics and isinstance(financial_metrics, list) and financial_metrics[0]:
        metrics = financial_metrics[0]
        # 使用缩写键名
        mapping = {
            'return_on_equity': 'roe',
            'net_margin': 'nm',
            'operating_margin': 'om',
            'revenue_growth': 'rg',
            'earnings_growth': 'eg',
            'book_value_growth': 'bvg',
            'current_ratio': 'cr',
            'debt_to_equity': 'de',
            'free_cash_flow_per_share': 'fcfps',
            'earnings_per_share': 'eps',
            'pe_ratio': 'pe',
            'price_to_book': 'pb',
            'price_to_sales': 'ps',
            'data_date': 'date',
            'expected_latest_date': 'exp_date'
        }

        for key, short_key in mapping.items():
            if key in metrics:
                # 数值型指标保留三位小数
                if isinstance(metrics[key], (int, float)):
                    compact_financials[short_key] = round(float(metrics[key]), 3)
                else:
                    compact_financials[short_key] = metrics[key]

    # 优化财务报表数据
    compact_statements = []
    if financial_line_items and isinstance(financial_line_items, list):
        for item in financial_line_items[:2]:  # 只保留最新的两期
            if not item:
                continue

            compact_item = {}
            # 使用缩写键名
            mapping = {
                'net_income': 'ni',
                'operating_revenue': 'rev',
                'operating_profit': 'op',
                'working_capital': 'wc',
                'depreciation_and_amortization': 'da',
                'capital_expenditure': 'capex',
                'free_cash_flow': 'fcf'
            }

            for key, short_key in mapping.items():
                if key in item:
                    # 大数值四舍五入到百万
                    if isinstance(item[key], (int, float)) and abs(item[key]) > 1000000:
                        compact_item[short_key] = round(item[key] / 1000000, 2)
                        if 'unit' not in compact_item:
                            compact_item['unit'] = 'M'  # 百万单位
                    elif isinstance(item[key], (int, float)):
                        compact_item[short_key] = round(item[key], 2)
                    else:
                        compact_item[short_key] = item[key]

            compact_statements.append(compact_item)

    # 优化市场数据
    compact_market = {}
    if market_data:
        # 使用缩写键名
        mapping = {
            'market_cap': 'mcap',
            'volume': 'vol',
            'average_volume': 'avg_vol',
            'fifty_two_week_high': '52h',
            'fifty_two_week_low': '52l'
        }

        for key, short_key in mapping.items():
            if key in market_data:
                # 大数值四舍五入到百万
                if isinstance(market_data[key], (int, float)) and abs(market_data[key]) > 1000000:
                    compact_market[short_key] = round(market_data[key] / 1000000, 2)
                    if 'unit' not in compact_market:
                        compact_market['unit'] = 'M'  # 百万单位
                elif isinstance(market_data[key], (int, float)):
                    compact_market[short_key] = round(market_data[key], 2)
                else:
                    compact_market[short_key] = market_data[key]

    return {
        "messages": messages,
        "data": {
            **data,
            "prices": compact_prices,
            "start_date": start_date,
            "end_date": end_date,
            "financials": compact_financials,
            "statements": compact_statements,
            "market": compact_market,
            # 保留原始数据的引用，以便其他代理可能需要
            "financial_metrics": financial_metrics,
            "financial_line_items": financial_line_items,
            "market_data": market_data,
        }
    }
