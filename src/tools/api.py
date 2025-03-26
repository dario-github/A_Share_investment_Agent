from typing import Dict, Any, List
import pandas as pd
import sys
import os
import concurrent.futures

# 导入akshare配置模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.tools.akshare_config import configure_akshare_timeout

# 设置akshare超时时间为30秒
configure_akshare_timeout(30)

import akshare as ak
from datetime import datetime, timedelta
import json
import numpy as np
import time
import functools
import random

# 引入数据协议类
from src.tools.data_protocol import PriceDataProtocol


def retry_on_exception(max_retries=3, initial_delay=1, backoff_factor=2, exceptions=(Exception,)):
    """
    装饰器：在遇到指定异常时进行重试

    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        backoff_factor: 退避因子，每次重试后延迟时间会乘以这个因子
        exceptions: 需要重试的异常类型

    Returns:
        装饰后的函数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for retry in range(max_retries + 1):
                try:
                    if retry > 0:
                        print(f"第 {retry} 次重试 {func.__name__}...")
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if retry < max_retries:
                        # 添加一些随机性，避免多个请求同时重试
                        jitter = random.uniform(0.8, 1.2)
                        sleep_time = delay * jitter
                        print(f"请求失败: {str(e)}，{sleep_time:.2f} 秒后重试...")
                        time.sleep(sleep_time)
                        delay *= backoff_factor
                    else:
                        print(f"达到最大重试次数 ({max_retries})，放弃重试")

            # 所有重试都失败，抛出最后一个异常
            raise last_exception

        return wrapper
    return decorator


# 财务指标数据缓存
_financial_metrics_cache = {}
_financial_cache_expiry = {}

def get_financial_metrics_from_sina(symbol: str) -> Dict[str, Any]:
    """从新浪财经获取财务指标数据"""
    try:
        # 判断股票代码前缀
        prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
        stock_code = f"{prefix}{symbol}"

        # 获取新浪财务指标
        financial_data = ak.stock_financial_analysis_indicator(
            symbol=symbol,
            start_year=str(datetime.now().year-2)
        )

        if financial_data is None or financial_data.empty:
            return [{}]

        # 按日期排序并获取最新的数据
        financial_data['日期'] = pd.to_datetime(financial_data['日期'])
        financial_data = financial_data.sort_values('日期', ascending=False)
        latest_financial = financial_data.iloc[0]

        # 获取实时行情
        realtime_data = ak.stock_zh_a_spot_em()
        if realtime_data is None or realtime_data.empty:
            return [{}]

        stock_data = realtime_data[realtime_data['代码'] == symbol]
        if stock_data.empty:
            return [{}]

        stock_data = stock_data.iloc[0]

        # 构建指标数据
        metrics = {
            "market_cap": float(stock_data.get("总市值", 0)),
            "float_market_cap": float(stock_data.get("流通市值", 0)),
            "return_on_equity": float(latest_financial.get("净资产收益率(%)", 0)) / 100.0,
            "net_margin": float(latest_financial.get("销售净利率(%)", 0)) / 100.0,
            "operating_margin": float(latest_financial.get("营业利润率(%)", 0)) / 100.0,
            "revenue_growth": float(latest_financial.get("主营业务收入增长率(%)", 0)) / 100.0,
            "earnings_growth": float(latest_financial.get("净利润增长率(%)", 0)) / 100.0,
            "book_value_growth": float(latest_financial.get("净资产增长率(%)", 0)) / 100.0,
            "current_ratio": float(latest_financial.get("流动比率", 0)),
            "debt_to_equity": float(latest_financial.get("资产负债率(%)", 0)) / 100.0,
            "free_cash_flow_per_share": float(latest_financial.get("每股经营性现金流(元)", 0)),
            "earnings_per_share": float(latest_financial.get("加权每股收益(元)", 0)),
            "pe_ratio": float(stock_data.get("市盈率-动态", 0)),
            "price_to_book": float(stock_data.get("市净率", 0)),
            "price_to_sales": float(stock_data.get("总市值", 0)) / float(latest_financial.get("主营业务收入", 1)) if float(latest_financial.get("主营业务收入", 0)) > 0 else 0,
            "data_date": latest_financial.get("日期").strftime("%Y-%m-%d"),
            "expected_latest_date": datetime.now().strftime("%Y-%m-%d")
        }

        return [metrics]

    except Exception as e:
        print(f"从新浪财经获取数据时出错：{e}")
        return [{}]

def get_financial_metrics_from_tencent(symbol: str) -> Dict[str, Any]:
    """从腾讯财经获取财务指标数据"""
    try:
        # 获取腾讯财经数据
        financial_data = ak.stock_financial_analysis_indicator(
            symbol=symbol,
            start_year=str(datetime.now().year-2)
        )

        if financial_data is None or financial_data.empty:
            return [{}]

        # 按日期排序并获取最新的数据
        financial_data['日期'] = pd.to_datetime(financial_data['日期'])
        financial_data = financial_data.sort_values('日期', ascending=False)
        latest_financial = financial_data.iloc[0]

        # 获取实时行情
        realtime_data = ak.stock_zh_a_spot_em()
        if realtime_data is None or realtime_data.empty:
            return [{}]

        stock_data = realtime_data[realtime_data['代码'] == symbol]
        if stock_data.empty:
            return [{}]

        stock_data = stock_data.iloc[0]

        # 构建指标数据
        metrics = {
            "market_cap": float(stock_data.get("总市值", 0)),
            "float_market_cap": float(stock_data.get("流通市值", 0)),
            "return_on_equity": float(latest_financial.get("净资产收益率(%)", 0)) / 100.0,
            "net_margin": float(latest_financial.get("销售净利率(%)", 0)) / 100.0,
            "operating_margin": float(latest_financial.get("营业利润率(%)", 0)) / 100.0,
            "revenue_growth": float(latest_financial.get("主营业务收入增长率(%)", 0)) / 100.0,
            "earnings_growth": float(latest_financial.get("净利润增长率(%)", 0)) / 100.0,
            "book_value_growth": float(latest_financial.get("净资产增长率(%)", 0)) / 100.0,
            "current_ratio": float(latest_financial.get("流动比率", 0)),
            "debt_to_equity": float(latest_financial.get("资产负债率(%)", 0)) / 100.0,
            "free_cash_flow_per_share": float(latest_financial.get("每股经营性现金流(元)", 0)),
            "earnings_per_share": float(latest_financial.get("加权每股收益(元)", 0)),
            "pe_ratio": float(stock_data.get("市盈率-动态", 0)),
            "price_to_book": float(stock_data.get("市净率", 0)),
            "price_to_sales": float(stock_data.get("总市值", 0)) / float(latest_financial.get("主营业务收入", 1)) if float(latest_financial.get("主营业务收入", 0)) > 0 else 0,
            "data_date": latest_financial.get("日期").strftime("%Y-%m-%d"),
            "expected_latest_date": datetime.now().strftime("%Y-%m-%d")
        }

        return [metrics]

    except Exception as e:
        print(f"从腾讯财经获取数据时出错：{e}")
        return [{}]

def get_financial_metrics_from_eastmoney(symbol: str) -> Dict[str, Any]:
    """从东方财富获取财务指标数据"""
    try:
        # 获取东方财富财务指标
        financial_data = ak.stock_financial_analysis_indicator(
            symbol=symbol,
            start_year=str(datetime.now().year-2)
        )

        if financial_data is None or financial_data.empty:
            return [{}]

        # 按日期排序并获取最新的数据
        financial_data['日期'] = pd.to_datetime(financial_data['日期'])
        financial_data = financial_data.sort_values('日期', ascending=False)
        latest_financial = financial_data.iloc[0]

        # 获取实时行情
        realtime_data = ak.stock_zh_a_spot_em()
        if realtime_data is None or realtime_data.empty:
            return [{}]

        stock_data = realtime_data[realtime_data['代码'] == symbol]
        if stock_data.empty:
            return [{}]

        stock_data = stock_data.iloc[0]

        # 构建指标数据
        metrics = {
            "market_cap": float(stock_data.get("总市值", 0)),
            "float_market_cap": float(stock_data.get("流通市值", 0)),
            "return_on_equity": float(latest_financial.get("净资产收益率(%)", 0)) / 100.0,
            "net_margin": float(latest_financial.get("销售净利率(%)", 0)) / 100.0,
            "operating_margin": float(latest_financial.get("营业利润率(%)", 0)) / 100.0,
            "revenue_growth": float(latest_financial.get("主营业务收入增长率(%)", 0)) / 100.0,
            "earnings_growth": float(latest_financial.get("净利润增长率(%)", 0)) / 100.0,
            "book_value_growth": float(latest_financial.get("净资产增长率(%)", 0)) / 100.0,
            "current_ratio": float(latest_financial.get("流动比率", 0)),
            "debt_to_equity": float(latest_financial.get("资产负债率(%)", 0)) / 100.0,
            "free_cash_flow_per_share": float(latest_financial.get("每股经营性现金流(元)", 0)),
            "earnings_per_share": float(latest_financial.get("加权每股收益(元)", 0)),
            "pe_ratio": float(stock_data.get("市盈率-动态", 0)),
            "price_to_book": float(stock_data.get("市净率", 0)),
            "price_to_sales": float(stock_data.get("总市值", 0)) / float(latest_financial.get("主营业务收入", 1)) if float(latest_financial.get("主营业务收入", 0)) > 0 else 0,
            "data_date": latest_financial.get("日期").strftime("%Y-%m-%d"),
            "expected_latest_date": datetime.now().strftime("%Y-%m-%d")
        }

        return [metrics]

    except Exception as e:
        print(f"从东方财富获取数据时出错：{e}")
        return [{}]

@retry_on_exception(max_retries=3, initial_delay=2, backoff_factor=2)
def get_financial_metrics(symbol: str) -> Dict[str, Any]:
    """获取财务指标数据，支持多个数据源"""
    try:
        # 检查缓存
        cache_key = f"financial_metrics_{symbol}"
        current_time = datetime.now()

        # 如果缓存存在且未过期（缓存12小时），则返回缓存数据
        if cache_key in _financial_metrics_cache and _financial_cache_expiry.get(cache_key, datetime.min) > current_time:
            print(f"使用缓存的财务指标数据 (symbol={symbol})")
            return _financial_metrics_cache[cache_key]

        print(f"\n正在获取 {symbol} 的财务指标数据...")

        # 尝试从不同数据源获取数据
        data_sources = [
            ("东方财富", lambda: get_financial_metrics_from_eastmoney(symbol)),
            ("新浪财经", lambda: get_financial_metrics_from_sina(symbol)),
            ("腾讯财经", lambda: get_financial_metrics_from_tencent(symbol))
        ]

        result = None
        for source_name, get_data_func in data_sources:
            try:
                print(f"尝试从{source_name}获取数据...")
                result = get_data_func()
                if result and result[0]:  # 如果成功获取到数据
                    print(f"成功从{source_name}获取数据")
                    break
            except Exception as e:
                print(f"从{source_name}获取数据失败：{e}")
                continue

        if not result or not result[0]:
            print("所有数据源都获取失败")
            # 如果有缓存但已过期，在出错时仍然返回过期的缓存数据
            if cache_key in _financial_metrics_cache:
                print(f"使用过期的缓存数据")
                return _financial_metrics_cache[cache_key]
            return [{}]

        # 更新缓存
        _financial_metrics_cache[cache_key] = result
        _financial_cache_expiry[cache_key] = current_time + timedelta(hours=12)

        return result

    except Exception as e:
        print(f"获取财务指标时出错：{e}")
        # 如果有缓存但已过期，在出错时仍然返回过期的缓存数据
        if cache_key in _financial_metrics_cache:
            print(f"使用过期的缓存数据")
            return _financial_metrics_cache[cache_key]
        return [{}]


# 财务报表数据缓存
_financial_statements_cache = {}
_statements_cache_expiry = {}

@retry_on_exception(max_retries=3, initial_delay=2, backoff_factor=2)
def get_financial_statements(symbol: str) -> Dict[str, Any]:
    """获取财务报表数据"""
    try:
        # 检查缓存
        cache_key = f"financial_statements_{symbol}"
        current_time = datetime.now()

        # 如果缓存存在且未过期（缓存24小时），则返回缓存数据
        if cache_key in _financial_statements_cache and _statements_cache_expiry.get(cache_key, datetime.min) > current_time:
            print(f"使用缓存的财务报表数据 (symbol={symbol})")
            return _financial_statements_cache[cache_key]

        print(f"\n正在获取 {symbol} 的财务报表数据...")

        # 获取资产负债表数据
        print("\n获取资产负债表数据...")
        try:
            # 判断股票代码前缀
            prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
            balance_sheet = ak.stock_financial_report_sina(
                stock=f"{prefix}{symbol}", symbol="资产负债表")
            if not balance_sheet.empty:
                latest_balance = balance_sheet.iloc[0]
                previous_balance = balance_sheet.iloc[1] if len(
                    balance_sheet) > 1 else balance_sheet.iloc[0]
                print("成功获取资产负债表数据")
            else:
                print("警告：无法获取资产负债表数据")
                latest_balance = pd.Series()
                previous_balance = pd.Series()
        except Exception as e:
            print(f"获取资产负债表数据时出错：{e}")
            latest_balance = pd.Series()
            previous_balance = pd.Series()

        # 获取利润表数据
        print("\n获取利润表数据...")
        try:
            income_statement = ak.stock_financial_report_sina(
                stock=f"{prefix}{symbol}", symbol="利润表")
            if not income_statement.empty:
                latest_income = income_statement.iloc[0]
                previous_income = income_statement.iloc[1] if len(
                    income_statement) > 1 else income_statement.iloc[0]
                print("成功获取利润表数据")
            else:
                print("警告：无法获取利润表数据")
                latest_income = pd.Series()
                previous_income = pd.Series()
        except Exception as e:
            print(f"获取利润表数据时出错：{e}")
            latest_income = pd.Series()
            previous_income = pd.Series()

        # 获取现金流量表数据
        print("\n获取现金流量表数据...")
        try:
            cash_flow = ak.stock_financial_report_sina(
                stock=f"{prefix}{symbol}", symbol="现金流量表")
            if not cash_flow.empty:
                latest_cash_flow = cash_flow.iloc[0]
                previous_cash_flow = cash_flow.iloc[1] if len(
                    cash_flow) > 1 else cash_flow.iloc[0]
                print("成功获取现金流量表数据")
            else:
                print("警告：无法获取现金流量表数据")
                latest_cash_flow = pd.Series()
                previous_cash_flow = pd.Series()
        except Exception as e:
            print(f"获取现金流量表数据时出错：{e}")
            latest_cash_flow = pd.Series()
            previous_cash_flow = pd.Series()

        # 构建财务数据
        line_items = []
        try:
            # 处理最新期间数据
            current_item = {
                # 从利润表获取
                "net_income": float(latest_income.get("净利润", 0)),
                "operating_revenue": float(latest_income.get("营业总收入", 0)),
                "operating_profit": float(latest_income.get("营业利润", 0)),

                # 从资产负债表计算营运资金
                "working_capital": float(latest_balance.get("流动资产合计", 0)) - float(latest_balance.get("流动负债合计", 0)),

                # 从现金流量表获取
                "depreciation_and_amortization": float(latest_cash_flow.get("固定资产折旧、油气资产折耗、生产性生物资产折旧", 0)),
                "capital_expenditure": abs(float(latest_cash_flow.get("购建固定资产、无形资产和其他长期资产支付的现金", 0))),
                "free_cash_flow": float(latest_cash_flow.get("经营活动产生的现金流量净额", 0)) - abs(float(latest_cash_flow.get("购建固定资产、无形资产和其他长期资产支付的现金", 0)))
            }
            line_items.append(current_item)
            print("成功处理最新期间数据")

            # 处理上一期间数据
            previous_item = {
                "net_income": float(previous_income.get("净利润", 0)),
                "operating_revenue": float(previous_income.get("营业总收入", 0)),
                "operating_profit": float(previous_income.get("营业利润", 0)),
                "working_capital": float(previous_balance.get("流动资产合计", 0)) - float(previous_balance.get("流动负债合计", 0)),
                "depreciation_and_amortization": float(previous_cash_flow.get("固定资产折旧、油气资产折耗、生产性生物资产折旧", 0)),
                "capital_expenditure": abs(float(previous_cash_flow.get("购建固定资产、无形资产和其他长期资产支付的现金", 0))),
                "free_cash_flow": float(previous_cash_flow.get("经营活动产生的现金流量净额", 0)) - abs(float(previous_cash_flow.get("购建固定资产、无形资产和其他长期资产支付的现金", 0)))
            }
            line_items.append(previous_item)
            print("成功处理上一期间数据")

        except Exception as e:
            print(f"处理财务数据时出错：{e}")
            default_item = {
                "net_income": 0,
                "operating_revenue": 0,
                "operating_profit": 0,
                "working_capital": 0,
                "depreciation_and_amortization": 0,
                "capital_expenditure": 0,
                "free_cash_flow": 0
            }
            line_items = [default_item, default_item]

        # 更新缓存
        _financial_statements_cache[cache_key] = line_items
        _statements_cache_expiry[cache_key] = current_time + timedelta(hours=24)

        return line_items

    except Exception as e:
        print(f"获取财务报表时出错：{e}")

        # 如果有缓存但已过期，在出错时仍然返回过期的缓存数据
        cache_key = f"financial_statements_{symbol}"
        if cache_key in _financial_statements_cache:
            print(f"使用过期的缓存数据")
            return _financial_statements_cache[cache_key]

        default_item = {
            "net_income": 0,
            "operating_revenue": 0,
            "operating_profit": 0,
            "working_capital": 0,
            "depreciation_and_amortization": 0,
            "capital_expenditure": 0,
            "free_cash_flow": 0
        }
        return [default_item, default_item]


# 简单的内存缓存
_market_data_cache = {}
_cache_expiry = {}

@retry_on_exception(max_retries=3, initial_delay=2, backoff_factor=2)
def get_market_data(symbol: str) -> Dict[str, Any]:
    """获取市场数据

    Args:
        symbol: 股票代码

    Returns:
        市场数据
    """
    # 检查缓存
    cache_key = f"market_data_{symbol}"
    current_time = datetime.now()

    # 如果缓存存在且未过期，直接返回缓存数据
    if (cache_key in _market_data_cache and
        _cache_expiry.get(cache_key, datetime.min) > current_time):
        print(f"使用缓存的市场数据 (symbol={symbol})")
        return _market_data_cache[cache_key]

    start_time = time.time()

    # 尝试直接获取（从最快的数据源）
    try:
        # 从腾讯财经直接获取（通常最快）
        print(f"直接获取 {symbol} 的市场数据...")
        # 判断股票代码前缀
        prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
        realtime_data = ak.stock_zh_a_daily(symbol=f"{prefix}{symbol}", adjust="")

        if realtime_data is not None and not realtime_data.empty:
            # 获取最新一天的数据
            latest_data = realtime_data.iloc[-1]

            # 获取52周最高最低价
            if len(realtime_data) >= 250:  # 约一年的交易日
                year_data = realtime_data.iloc[-250:]
                fifty_two_week_high = year_data['high'].max()
                fifty_two_week_low = year_data['low'].min()
            else:
                fifty_two_week_high = realtime_data['high'].max()
                fifty_two_week_low = realtime_data['low'].min()

            # 构建结果
            result = {
                "market_cap": 0,  # 腾讯数据没有市值信息
                "volume": float(latest_data.get("volume", 0)),
                "average_volume": float(realtime_data['volume'].mean()),
                "fifty_two_week_high": float(fifty_two_week_high),
                "fifty_two_week_low": float(fifty_two_week_low),
                "is_expired_cache": False,
                "data_source": "腾讯财经",
                "price": float(latest_data.get("close", 0))
            }

            elapsed = time.time() - start_time
            print(f"直接获取成功，耗时 {elapsed:.2f} 秒")

            # 更新缓存
            _market_data_cache[cache_key] = result
            # 缓存保留1小时
            _cache_expiry[cache_key] = current_time + timedelta(hours=1)

            return result
    except Exception as e:
        print(f"直接获取失败: {e}，尝试其他数据源...")

    # 如果直接获取失败，尝试通过定义的数据源获取
    # 使用原有的逻辑，但优化超时处理

    # 从东方财富获取数据
    def get_data_from_eastmoney():
        try:
            realtime_data = ak.stock_zh_a_spot_em()
            if realtime_data is None or realtime_data.empty:
                return None

            stock_data = realtime_data[realtime_data['代码'] == symbol]
            if stock_data.empty:
                return None

            stock_data = stock_data.iloc[0]

            # 构建结果
            result = {
                "market_cap": float(stock_data.get("总市值", 0)),
                "volume": float(stock_data.get("成交量", 0)),
                "average_volume": float(stock_data.get("成交量", 0)),  # A股没有平均成交量，暂用当日成交量
                "fifty_two_week_high": float(stock_data.get("52周最高", stock_data.get("最高", 0))),
                "fifty_two_week_low": float(stock_data.get("52周最低", stock_data.get("最低", 0))),
                "is_expired_cache": False,  # 标记为非过期数据
                "data_source": "东方财富"
            }

            return result
        except Exception as e:
            print(f"处理东方财富数据时出错: {e}")
            return None

    # 从新浪获取数据
    def get_data_from_sina():
        try:
            realtime_data = ak.stock_zh_a_spot()
            if realtime_data is None or realtime_data.empty:
                return None

            stock_data = realtime_data[realtime_data['代码'] == symbol]
            if stock_data.empty:
                return None

            stock_data = stock_data.iloc[0]

            # 构建结果
            result = {
                "market_cap": float(stock_data.get("总市值", 0)),
                "volume": float(stock_data.get("成交量", 0)),
                "average_volume": float(stock_data.get("成交量", 0)),
                "fifty_two_week_high": float(stock_data.get("最高", 0)),
                "fifty_two_week_low": float(stock_data.get("最低", 0)),
                "is_expired_cache": False,
                "data_source": "新浪财经"
            }

            return result
        except Exception as e:
            print(f"处理新浪数据时出错: {e}")
            return None

    # 更高效地获取和处理数据源
    data_sources = [
        ("东方财富", get_data_from_eastmoney),
        ("新浪财经", get_data_from_sina)
    ]

    # 并行获取数据
    result = None
    error_messages = []

    # 使用线程池并发执行请求
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # 提交所有任务
        future_to_source = {
            executor.submit(lambda func: func(), get_data_func): source_name
            for source_name, get_data_func in data_sources
        }

        # 获取最快返回的有效结果
        for future in concurrent.futures.as_completed(future_to_source, timeout=5):
            source_name = future_to_source[future]
            try:
                data = future.result(timeout=2)  # 单个结果超时设置为2秒
                if data is not None:
                    result = data
                    print(f"成功从{source_name}获取市场数据")
                    break  # 一旦获得一个有效结果就停止等待
                else:
                    error_messages.append(f"从{source_name}获取数据失败")
            except Exception as e:
                error_messages.append(f"从{source_name}获取数据出错: {str(e)}")

    # 如果所有数据源都失败，检查缓存
    if result is None:
        error_message = f"警告：未能从任何数据源获取到 {symbol} 的市场数据"
        print(error_message)
        error_messages.append(error_message)

        # 如果有缓存但已过期，在出错时仍然返回过期的缓存数据，但标记为过期
        if cache_key in _market_data_cache:
            print(f"使用过期的缓存数据 (symbol={symbol})")
            cached_data = _market_data_cache[cache_key].copy()
            cached_data["is_expired_cache"] = True
            cached_data["error_messages"] = error_messages
            return cached_data

        # 如果没有缓存，则抛出异常
        raise ValueError(f"无法获取市场数据: {'; '.join(error_messages)}")

    # 检查数据有效性
    if "market_cap" in result and result["market_cap"] <= 0:
        print(f"警告：股票 {symbol} 的市值数据无效或缺失")
        # 尝试从其他数据源补充市值数据
        for source_name, get_data_func in data_sources:
            if source_name != result["data_source"]:
                supplementary_data = get_data_func()
                if supplementary_data is not None and supplementary_data.get("market_cap", 0) > 0:
                    result["market_cap"] = supplementary_data["market_cap"]
                    print(f"使用{source_name}的市值数据进行补充")
                    break

    if "volume" in result and result["volume"] < 0:
        print(f"警告：股票 {symbol} 的成交量数据无效")
        result["volume"] = 0

    # 更新缓存
    _market_data_cache[cache_key] = result
    # 缓存保留较短时间（当日行情数据变化快）
    _cache_expiry[cache_key] = current_time + timedelta(minutes=30)

    print(f"成功获取 {symbol} 的市场数据，总耗时 {time.time() - start_time:.2f} 秒")
    return result


# 价格历史数据缓存
_price_history_cache = {}
_price_cache_expiry = {}

@retry_on_exception(max_retries=3, initial_delay=2, backoff_factor=2)
def get_price_history(symbol: str, start_date: str = None, end_date: str = None, adjust: str = "qfq") -> pd.DataFrame:
    """获取历史价格数据

    Args:
        symbol: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD，如果为None则默认获取过去一年的数据
        end_date: 结束日期，格式：YYYY-MM-DD，如果为None则使用昨天作为结束日期
        adjust: 复权类型，可选值：
               - "": 不复权
               - "qfq": 前复权（默认）
               - "hfq": 后复权

    Returns:
        包含价格数据和技术指标的DataFrame
    """
    try:
        # 获取当前日期和昨天的日期
        current_date = datetime.now()
        yesterday = current_date - timedelta(days=1)

        # 如果没有提供日期，默认使用昨天作为结束日期
        if not end_date:
            end_date = yesterday  # 使用昨天作为结束日期
        else:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            # 确保end_date不会超过昨天
            if end_date > yesterday:
                end_date = yesterday

        if not start_date:
            start_date = end_date - timedelta(days=365)  # 默认获取一年的数据
        else:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")

        # 构建缓存键
        cache_key = f"price_history_{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{adjust}"

        # 检查缓存
        if cache_key in _price_history_cache and _price_cache_expiry.get(cache_key, datetime.min) > current_date:
            print(f"使用缓存的历史价格数据 (symbol={symbol}, start={start_date.strftime('%Y-%m-%d')}, end={end_date.strftime('%Y-%m-%d')})")
            df = _price_history_cache[cache_key]

            # 验证缓存的数据
            if validate_price_data(df, symbol):
                return df
            else:
                print("缓存数据无效，重新获取")

        print(f"\n正在获取 {symbol} 的历史行情数据...")
        print(f"开始日期：{start_date.strftime('%Y-%m-%d')}")
        print(f"结束日期：{end_date.strftime('%Y-%m-%d')}")
        print("请耐心等待，这可能需要一些时间...")

        # 定义数据获取函数，支持多种数据源
        def get_data_from_source(source_name, get_data_func, start_date, end_date):
            """从指定数据源获取数据"""
            try:
                print(f"尝试从{source_name}获取数据...")
                start_time = time.time()
                df = get_data_func(start_date, end_date)
                elapsed_time = time.time() - start_time

                if df is not None and not df.empty:
                    print(f"成功从{source_name}获取数据，耗时 {elapsed_time:.2f} 秒")
                    return df
                else:
                    print(f"从{source_name}获取数据失败，返回空数据")
                    return pd.DataFrame()
            except Exception as e:
                print(f"从{source_name}获取数据时出错: {e}")
                return pd.DataFrame()

        def get_data_from_akshare(start_date, end_date):
            """从akshare获取数据"""
            try:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust=adjust
                )

                if df is None or df.empty:
                    return pd.DataFrame()

                # 重命名列以匹配技术分析代理的需求
                df = df.rename(columns={
                    "日期": "date",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "volume",
                    "成交额": "amount",
                    "振幅": "amplitude",
                    "涨跌幅": "pct_change",
                    "涨跌额": "change_amount",
                    "换手率": "turnover"
                })

                # 确保日期列为datetime类型
                df["date"] = pd.to_datetime(df["date"])
                return df
            except Exception as e:
                print(f"从akshare获取数据时出错: {e}")
                return pd.DataFrame()

        def get_data_from_netease(start_date, end_date):
            """从网易财经获取数据"""
            try:
                df = ak.stock_zh_a_hist_163(
                    symbol=symbol,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust=adjust
                )

                if df is None or df.empty:
                    return pd.DataFrame()

                # 重命名列以匹配技术分析代理的需求
                df = df.rename(columns={
                    "日期": "date",
                    "开盘价": "open",
                    "最高价": "high",
                    "最低价": "low",
                    "收盘价": "close",
                    "成交量": "volume",
                    "成交金额": "amount",
                    "涨跌幅": "pct_change"
                })

                # 确保日期列为datetime类型
                df["date"] = pd.to_datetime(df["date"])
                return df
            except Exception as e:
                print(f"从网易财经获取数据时出错: {e}")
                return pd.DataFrame()

        def get_data_from_sina(start_date, end_date):
            """从新浪财经获取数据"""
            try:
                # 判断股票代码前缀
                prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
                df = ak.stock_zh_a_daily(
                    symbol=f"{prefix}{symbol}",
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust=adjust
                )

                if df is None or df.empty:
                    return pd.DataFrame()

                # 重命名列以匹配技术分析代理的需求
                df = df.rename(columns={
                    "date": "date",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "volume": "volume"
                })

                # 确保日期列为datetime类型
                df["date"] = pd.to_datetime(df["date"])
                return df
            except Exception as e:
                print(f"从新浪财经获取数据时出错: {e}")
                return pd.DataFrame()

        # 尝试从不同数据源获取数据
        data_sources = [
            ("东方财富", get_data_from_akshare),
            ("网易财经", get_data_from_netease),
            ("新浪财经", get_data_from_sina)
        ]

        df = None
        for source_name, get_data_func in data_sources:
            df = get_data_from_source(source_name, get_data_func, start_date, end_date)
            if df is not None and not df.empty:
                print(f"成功从{source_name}获取数据，共 {len(df)} 条记录")
                break

        # 如果所有数据源都失败，检查缓存
        if df is None or df.empty:
            print(f"警告：未能从任何数据源获取到 {symbol} 的历史行情数据")

            # 如果有缓存但已过期，在出错时仍然返回过期的缓存数据
            if cache_key in _price_history_cache:
                print(f"使用过期的缓存数据")
                return _price_history_cache[cache_key]

            return pd.DataFrame()

        # 检查数据量是否足够
        min_required_days = 120  # 至少需要120个交易日的数据
        if len(df) < min_required_days:
            print(
                f"警告：获取到的数据量（{len(df)}条）不足以计算所有技术指标（需要至少{min_required_days}条）")
            print("尝试获取更长时间范围的数据...")

            # 扩大时间范围到2年
            extended_start_date = end_date - timedelta(days=730)

            # 尝试从不同数据源获取更长时间范围的数据
            extended_df = None
            for source_name, get_data_func in data_sources:
                extended_df = get_data_from_source(source_name, get_data_func, extended_start_date, end_date)
                if extended_df is not None and not extended_df.empty and len(extended_df) > len(df):
                    print(f"成功从{source_name}获取更长时间范围的数据，共 {len(extended_df)} 条记录")
                    df = extended_df
                    break

            if len(df) < min_required_days:
                print(f"警告：即使扩大时间范围，数据量（{len(df)}条）仍然不足")

        print(f"开始计算技术指标...")
        start_time = time.time()

        # 计算基本技术指标 - 使用向量化操作提高性能
        # 计算动量指标
        df["momentum_1m"] = df["close"].pct_change(periods=20)  # 20个交易日约等于1个月
        df["momentum_3m"] = df["close"].pct_change(periods=60)  # 60个交易日约等于3个月
        df["momentum_6m"] = df["close"].pct_change(periods=120)  # 120个交易日约等于6个月

        # 计算成交量动量（相对于20日平均成交量的变化）
        df["volume_ma20"] = df["volume"].rolling(window=20).mean()
        df["volume_momentum"] = df["volume"] / df["volume_ma20"]

        # 计算波动率指标
        # 1. 历史波动率 (20日)
        returns = df["close"].pct_change()
        df["historical_volatility"] = returns.rolling(window=20).std() * np.sqrt(252)  # 年化

        # 2. 波动率区间 (相对于过去120天的波动率的位置)
        # 使用更高效的方法计算
        if len(df) >= 120:
            volatility_120d = returns.rolling(window=120).std() * np.sqrt(252)
            vol_min = volatility_120d.rolling(window=120).min()
            vol_max = volatility_120d.rolling(window=120).max()
            vol_range = vol_max - vol_min
            df["volatility_regime"] = np.where(
                vol_range > 0,
                (df["historical_volatility"] - vol_min) / vol_range,
                0  # 当范围为0时返回0
            )

            # 3. 波动率Z分数
            vol_mean = df["historical_volatility"].rolling(window=120).mean()
            vol_std = df["historical_volatility"].rolling(window=120).std()
            df["volatility_z_score"] = (
                df["historical_volatility"] - vol_mean) / vol_std
        else:
            # 数据不足时使用简化计算
            df["volatility_regime"] = 0.5  # 默认中等波动率
            df["volatility_z_score"] = 0.0  # 默认均值

        # 4. ATR比率 - 使用更高效的计算方法
        tr = pd.DataFrame()
        tr["h-l"] = df["high"] - df["low"]
        tr["h-pc"] = abs(df["high"] - df["close"].shift(1))
        tr["l-pc"] = abs(df["low"] - df["close"].shift(1))
        tr["tr"] = tr[["h-l", "h-pc", "l-pc"]].max(axis=1)
        df["atr"] = tr["tr"].rolling(window=14).mean()
        df["atr_ratio"] = df["atr"] / df["close"]

        # 只有当数据足够时才计算高级指标
        if len(df) >= 120:
            # 计算统计套利指标
            # 1. 赫斯特指数 (使用过去120天的数据) - 使用优化版本
            def calculate_hurst(series):
                """
                计算Hurst指数。

                Args:
                    series: 价格序列

                Returns:
                    float: Hurst指数，或在计算失败时返回np.nan
                """
                try:
                    series = series.dropna()
                    if len(series) < 30:  # 降低最小数据点要求
                        return np.nan

                    # 使用对数收益率
                    log_returns = np.log(series / series.shift(1)).dropna()
                    if len(log_returns) < 30:  # 降低最小数据点要求
                        return np.nan

                    # 使用更小的lag范围，减少计算量
                    # 只使用3个关键点而不是整个范围
                    lags = [2, 5, 10]  # 只使用3个关键点

                    # 计算每个lag的标准差，使用向量化操作代替循环
                    tau = []
                    for lag in lags:
                        # 使用numpy操作代替pandas滚动窗口，提高性能
                        if len(log_returns) > lag:
                            # 使用numpy的std直接计算，避免创建临时Series
                            std_value = np.std(log_returns.values[lag:] - log_returns.values[:-lag])
                            tau.append(std_value)
                        else:
                            return np.nan  # 数据不足

                    # 基本的数值检查
                    if len(tau) < 3:  # 需要至少3个点进行回归
                        return np.nan

                    # 使用对数回归
                    lags_log = np.log(lags)
                    tau_log = np.log(tau)

                    # 计算回归系数
                    reg = np.polyfit(lags_log, tau_log, 1)
                    hurst = reg[0] / 2.0

                    # 只保留基本的数值检查
                    if np.isnan(hurst) or np.isinf(hurst):
                        return np.nan

                    # 限制Hurst指数在合理范围内
                    return max(0.0, min(1.0, hurst))

                except Exception as e:
                    return np.nan

            print("计算Hurst指数...")
            # 使用对数收益率计算Hurst指数，但减少计算频率
            # 只对每5行数据计算一次，然后填充其他行
            log_returns = np.log(df["close"] / df["close"].shift(1))

            # 创建一个空的Series来存储Hurst指数
            hurst_values = pd.Series(index=df.index, dtype=float)

            # 只对每5行数据计算一次Hurst指数
            for i in range(0, len(df), 5):
                if i >= 120:  # 确保有足够的数据
                    window_data = log_returns.iloc[max(0, i-120):i]
                    if len(window_data) >= 60:  # 要求至少60个数据点
                        hurst_values.iloc[i] = calculate_hurst(df["close"].iloc[max(0, i-120):i])

            # 向前填充NaN值
            df["hurst_exponent"] = hurst_values.fillna(method='ffill')

            print("计算偏度和峰度...")
            # 2. 偏度 (20日)
            df["skewness"] = returns.rolling(window=20).skew()

            # 3. 峰度 (20日)
            df["kurtosis"] = returns.rolling(window=20).kurt()
        else:
            # 数据不足时使用默认值
            df["hurst_exponent"] = 0.5  # 默认随机游走
            df["skewness"] = 0.0  # 默认对称分布
            df["kurtosis"] = 3.0  # 默认正态分布

        # 按日期升序排序
        df = df.sort_values("date")

        # 重置索引
        df = df.reset_index(drop=True)

        elapsed_time = time.time() - start_time
        print(f"技术指标计算完成，耗时 {elapsed_time:.2f} 秒")
        print(f"成功获取历史行情数据，共 {len(df)} 条记录")

        # 检查并报告NaN值
        nan_columns = df.isna().sum()
        if nan_columns.any():
            print("\n警告：以下指标存在NaN值：")
            for col, nan_count in nan_columns[nan_columns > 0].items():
                print(f"- {col}: {nan_count}条")

        # 在返回数据前进行验证
        final_elapsed_time = time.time() - start_time
        print(f"技术指标计算完成，耗时 {final_elapsed_time:.2f} 秒")

        # 验证最终数据
        if validate_price_data(df, symbol):
            # 更新缓存
            _price_history_cache[cache_key] = df
            _price_cache_expiry[cache_key] = current_date + timedelta(hours=12)  # 设置12小时过期

            return df
        else:
            print(f"警告：获取的价格数据不完整或格式不正确，请检查！")
            return pd.DataFrame(columns=['close', 'open', 'high', 'low', 'volume', 'date'])

    except Exception as e:
        print(f"获取历史价格数据时出错: {str(e)}")
        return pd.DataFrame()


def validate_price_data(df, symbol):
    """验证价格数据的完整性和格式"""
    try:
        if df is None or df.empty:
            print(f"警告: {symbol} 的价格数据为空")
            return False

        # 检查必要列是否存在
        required_columns = ['close', 'open', 'high', 'low', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            print(f"警告: {symbol} 的价格数据缺少必要列 {', '.join(missing_columns)}")
            print(f"现有列: {list(df.columns)}")
            return False

        # 检查数据类型
        for col in required_columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                print(f"警告: {symbol} 的价格数据列 '{col}' 不是数值类型")
                return False

        # 检查是否有无效值
        for col in required_columns:
            if df[col].isna().any():
                print(f"警告: {symbol} 的价格数据列 '{col}' 包含NaN值")
                df = df.dropna(subset=[col])
                if df.empty:
                    return False

        # 检查是否有有效的交易日数据
        min_required = 20
        if len(df) < min_required:
            print(f"警告: {symbol} 的价格数据记录数 ({len(df)}) 少于最小要求 ({min_required})")
            return False

        print(f"价格数据验证通过: {symbol}, 共 {len(df)} 条记录")
        return True
    except Exception as e:
        print(f"验证价格数据时出错: {str(e)}")
        return False


def prices_to_df(prices):
    """Convert price data to DataFrame with standardized column names"""
    try:
        # 使用数据协议类的标准化方法
        return PriceDataProtocol.standardize(prices)
    except Exception as e:
        print(f"转换价格数据时出错: {str(e)}")
        raise ValueError(f"价格数据处理失败: {str(e)}")


def get_price_data(
    ticker: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """获取股票价格数据

    Args:
        ticker: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD

    Returns:
        包含价格数据的DataFrame
    """
    return get_price_history(ticker, start_date, end_date)
