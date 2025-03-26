import pandas as pd
from typing import Dict, Any, List, Tuple, Callable, Optional
from datetime import datetime, timedelta
import time

from src.tools.parallel_fetcher import ParallelDataFetcher
from src.tools.api import (
    get_price_history,
    validate_price_data,
    ak
)
from src.tools.data_protocol import PriceDataProtocol

# 设置全局缓存
_price_history_cache = {}
_price_cache_expiry = {}
_market_data_cache = {}
_market_cache_expiry = {}

# 缓存过期时间（按数据类型区分）
CACHE_EXPIRY = {
    'market_data': timedelta(minutes=5),  # 当日行情数据5分钟过期
    'price_history': timedelta(hours=6),  # 历史价格数据6小时过期
}

# 创建并行数据获取器实例
fetcher = ParallelDataFetcher(timeout=15, max_workers=3)


# 定义数据获取函数
def get_data_from_eastmoney(symbol: str) -> Dict[str, Any]:
    """从东方财富获取市场数据"""
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


def get_data_from_sina(symbol: str) -> Dict[str, Any]:
    """从新浪财经获取市场数据"""
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


def get_data_from_tencent(symbol: str) -> Dict[str, Any]:
    """从腾讯财经获取市场数据"""
    try:
        # 判断股票代码前缀
        prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
        realtime_data = ak.stock_zh_a_daily(symbol=f"{prefix}{symbol}", adjust="")

        if realtime_data is None or realtime_data.empty:
            return None

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

        return result
    except Exception as e:
        print(f"处理腾讯数据时出错: {e}")
        return None


def get_data_from_akshare(symbol: str, start_date, end_date) -> pd.DataFrame:
    """从akshare获取历史价格数据"""
    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.strftime("%Y%m%d") if isinstance(start_date, datetime) else start_date,
            end_date=end_date.strftime("%Y%m%d") if isinstance(end_date, datetime) else end_date,
            adjust="qfq"
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


def get_data_from_netease(symbol: str, start_date, end_date) -> pd.DataFrame:
    """从网易财经获取历史价格数据"""
    try:
        # 使用可替代的API，原先的stock_zh_a_hist_163在akshare中不存在
        # 使用腾讯的API作为替代
        prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
        df = ak.stock_zh_a_daily(
            symbol=f"{prefix}{symbol}",
            start_date=start_date.strftime("%Y%m%d") if isinstance(start_date, datetime) else start_date,
            end_date=end_date.strftime("%Y%m%d") if isinstance(end_date, datetime) else end_date,
            adjust="qfq"
        )

        if df is None or df.empty:
            return pd.DataFrame()

        # 确保日期列为datetime类型
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception as e:
        print(f"从网易财经(替代API)获取数据时出错: {str(e)}")
        return pd.DataFrame()


def get_data_from_sina_hist(symbol: str, start_date, end_date) -> pd.DataFrame:
    """从新浪财经获取历史价格数据"""
    try:
        # 判断股票代码前缀
        prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
        df = ak.stock_zh_a_daily(
            symbol=f"{prefix}{symbol}",
            start_date=start_date.strftime("%Y%m%d") if isinstance(start_date, datetime) else start_date,
            end_date=end_date.strftime("%Y%m%d") if isinstance(end_date, datetime) else end_date,
            adjust="qfq"
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


def get_market_data_fast(symbol: str) -> Dict[str, Any]:
    """
    快速获取市场数据（使用并行获取）

    Args:
        symbol: 股票代码

    Returns:
        市场数据字典
    """
    # 检查缓存
    cache_key = f"market_data_{symbol}"
    current_time = datetime.now()

    # 如果缓存存在且未过期，直接返回缓存数据
    if (cache_key in _market_data_cache and
        _market_cache_expiry.get(cache_key, datetime.min) > current_time):
        print(f"使用缓存的市场数据 (symbol={symbol})")
        return _market_data_cache[cache_key]

    # 先尝试最快的单个数据源
    start_time = time.time()
    try:
        print(f"直接获取 {symbol} 的市场数据...")
        result = get_data_from_tencent(symbol)
        if result is not None:
            elapsed = time.time() - start_time
            print(f"直接获取成功，耗时 {elapsed:.2f} 秒")
            _market_data_cache[cache_key] = result
            _market_cache_expiry[cache_key] = current_time + CACHE_EXPIRY['market_data']
            return result
    except Exception as e:
        print(f"直接获取失败: {e}，尝试并行获取...")

    # 如果直接获取失败，尝试并行获取
    # 定义数据源列表（腾讯最快放在首位）
    data_sources = [
        ("腾讯财经", get_data_from_tencent),
        ("东方财富", get_data_from_eastmoney),
        ("新浪财经", get_data_from_sina)
    ]

    # 使用超短超时的并行获取器
    ultra_quick_fetcher = ParallelDataFetcher(timeout=2, max_workers=3)

    # 并行获取数据，先尝试快速获取
    print(f"并行获取 {symbol} 的市场数据...")
    result = ultra_quick_fetcher.fetch_market_data(symbol, data_sources)

    # 如果获取成功，更新缓存
    if result is not None:
        _market_data_cache[cache_key] = result
        _market_cache_expiry[cache_key] = current_time + CACHE_EXPIRY['market_data']
        print(f"市场数据获取成功，耗时 {time.time() - start_time:.2f} 秒")
        return result

    # 如果快速并行获取失败，使用标准超时重试
    if result is None:
        print(f"快速获取失败，使用标准超时重试...")
        result = fetcher.fetch_market_data(symbol, data_sources)
        if result is not None:
            _market_data_cache[cache_key] = result
            _market_cache_expiry[cache_key] = current_time + CACHE_EXPIRY['market_data']
            print(f"标准超时重试成功，耗时 {time.time() - start_time:.2f} 秒")
            return result

    # 如果当前获取失败，但有过期缓存数据，则使用过期缓存
    if cache_key in _market_data_cache:
        print(f"所有数据源获取失败，使用过期的缓存数据 (symbol={symbol})")
        # 标记为使用过期数据
        cached_data = _market_data_cache[cache_key].copy()
        cached_data["is_expired_cache"] = True
        return cached_data

    # 如果没有缓存数据且获取失败，返回空数据
    print(f"无法获取市场数据，且没有缓存数据 (symbol={symbol})")
    return {"market_cap": 0, "volume": 0, "error": "无法获取市场数据"}


def get_price_history_fast(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adjust: str = "qfq",
    compute_indicators: bool = False
) -> pd.DataFrame:
    """
    快速获取历史价格数据（使用并行获取）

    Args:
        symbol: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD，如果为None则默认获取过去一年的数据
        end_date: 结束日期，格式：YYYY-MM-DD，如果为None则使用昨天作为结束日期
        adjust: 复权类型
        compute_indicators: 是否计算技术指标

    Returns:
        包含价格数据的DataFrame
    """
    # 处理日期参数
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)

    # 如果没有提供日期，默认使用昨天作为结束日期
    if not end_date:
        end_date_obj = yesterday
    else:
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        # 确保end_date不会超过昨天
        if end_date_obj > yesterday:
            end_date_obj = yesterday

    end_date = end_date_obj.strftime("%Y-%m-%d")

    if not start_date:
        # 默认获取一年的数据
        start_date_obj = end_date_obj - timedelta(days=365)
        start_date = start_date_obj.strftime("%Y-%m-%d")
    else:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")

    # 构建缓存键
    cache_key = f"price_history_{symbol}_{start_date}_{end_date}_{adjust}"

    # 检查缓存
    if (cache_key in _price_history_cache and
        _price_cache_expiry.get(cache_key, datetime.min) > current_date):
        print(f"使用缓存的历史价格数据 (symbol={symbol})")
        df = _price_history_cache[cache_key]

        # 如果需要计算技术指标且缓存数据没有指标
        if compute_indicators and 'momentum_1m' not in df.columns:
            print("缓存数据中没有技术指标，计算技术指标...")
            compute_technical_indicators(df)
            # 更新缓存
            _price_history_cache[cache_key] = df

        return df

    # 最简单的方式：直接尝试新浪的API (通常最稳定)
    start_time = time.time()
    try:
        # 先尝试直接使用新浪API，这通常是最快的方式
        print(f"直接获取 {symbol} 的历史价格数据...")
        df = get_data_from_sina_hist(symbol, start_date, end_date)
        if df is not None and not df.empty and len(df) >= 5:
            print(f"直接获取成功，共 {len(df)} 条记录，耗时 {time.time() - start_time:.2f} 秒")
            df = PriceDataProtocol.standardize(df)

            # 计算技术指标
            if compute_indicators:
                print("计算技术指标...")
                compute_technical_indicators(df)

            # 更新缓存
            _price_history_cache[cache_key] = df
            _price_cache_expiry[cache_key] = current_date + CACHE_EXPIRY['price_history']

            return df
    except Exception as e:
        print(f"直接获取失败: {str(e)}，尝试并行获取...")

    # 如果直接获取失败，尝试并行获取
    print(f"使用并行方式获取历史价格数据...")

    # 创建更简单的包装函数
    def wrapped_getter(func):
        def wrapper(symbol, start_date, end_date, adjust):
            try:
                return func(symbol, start_date, end_date)
            except Exception as e:
                print(f"获取数据出错: {str(e)}")
                return pd.DataFrame()
        return wrapper

    # 定义数据源列表（根据成功率排序）
    data_sources = [
        ("新浪财经", wrapped_getter(get_data_from_sina_hist)),
        ("网易财经", wrapped_getter(get_data_from_netease)),
        ("东方财富", wrapped_getter(get_data_from_akshare))
    ]

    # 使用超快速的并行获取器（超时时间短）
    quick_fetcher = ParallelDataFetcher(timeout=3, max_workers=3)
    df = quick_fetcher.fetch_price_history(symbol, start_date, end_date, data_sources, adjust)

    # 验证获取到的数据
    if df is not None and not df.empty:
        # 使用数据协议进行标准化
        try:
            df = PriceDataProtocol.standardize(df)

            # 如果需要计算技术指标
            if compute_indicators:
                print("计算技术指标...")
                compute_technical_indicators(df)

            # 更新缓存
            _price_history_cache[cache_key] = df
            _price_cache_expiry[cache_key] = current_date + CACHE_EXPIRY['price_history']

            print(f"历史价格数据获取和处理成功，总耗时 {time.time() - start_time:.2f} 秒")
            return df
        except Exception as e:
            print(f"数据标准化或处理失败: {str(e)}")

    # 如果获取失败，但有过期缓存
    if cache_key in _price_history_cache:
        print(f"所有数据源获取失败，使用过期的缓存数据 (symbol={symbol})")
        return _price_history_cache[cache_key]

    # 所有方法都失败，返回空DataFrame
    print(f"无法获取历史价格数据 (symbol={symbol})")
    return pd.DataFrame(columns=['close', 'open', 'high', 'low', 'volume', 'date'])


def compute_technical_indicators(df: pd.DataFrame) -> None:
    """
    计算技术指标，直接修改传入的DataFrame

    Args:
        df: 包含价格数据的DataFrame
    """
    if df is None or df.empty or len(df) < 20:
        print("数据不足，无法计算技术指标")
        return

    try:
        # 确保数据按日期排序
        if 'date' in df.columns:
            df.sort_values('date', inplace=True)

        # 简化的技术指标集合，仅计算最常用的指标

        # 1. 计算动量指标
        df["momentum_1m"] = df["close"].pct_change(periods=20)  # 20个交易日约等于1个月
        df["momentum_3m"] = df["close"].pct_change(periods=60)  # 60个交易日约等于3个月

        # 2. 计算成交量动量
        df["volume_ma20"] = df["volume"].rolling(window=20).mean()
        df["volume_momentum"] = df["volume"] / df["volume_ma20"]

        # 3. 历史波动率 (20日)
        returns = df["close"].pct_change()
        df["historical_volatility"] = returns.rolling(window=20).std() * (252**0.5)  # 年化

        # 4. ATR计算（真实波动幅度）
        tr = pd.DataFrame()
        tr["h-l"] = df["high"] - df["low"]
        tr["h-pc"] = abs(df["high"] - df["close"].shift(1))
        tr["l-pc"] = abs(df["low"] - df["close"].shift(1))
        tr["tr"] = tr[["h-l", "h-pc", "l-pc"]].max(axis=1)
        df["atr"] = tr["tr"].rolling(window=14).mean()
        df["atr_ratio"] = df["atr"] / df["close"]

        print(f"计算了 {len(df)} 条记录的技术指标")
    except Exception as e:
        print(f"计算技术指标时出错: {str(e)}")