import os
import time
import pickle
import shutil
from datetime import datetime, timedelta
import pandas as pd
import akshare as ak
from functools import wraps
import threading
import concurrent.futures

# 定义缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# 缓存文件路径
MARKET_DATA_CACHE_FILE = os.path.join(CACHE_DIR, "market_data_cache.pkl")
STOCK_NAMES_CACHE_FILE = os.path.join(CACHE_DIR, "stock_names_cache.pkl")
HISTORICAL_DATA_CACHE_DIR = os.path.join(CACHE_DIR, "historical_data")
os.makedirs(HISTORICAL_DATA_CACHE_DIR, exist_ok=True)

# 缓存锁，防止多线程同时写入
_cache_lock = threading.Lock()

# 内存缓存
_market_data_cache = {}
_cache_expiry = {}
_stock_names_df = None

def log_data_operation(operation_type, details=""):
    """记录数据操作日志"""
    print(f"[数据提供层] {operation_type}: {details}")

def check_pickle_validity(cache_file):
    """
    检查pickle缓存文件是否有效

    Args:
        cache_file: 缓存文件路径

    Returns:
        bool: 文件是否有效
    """
    try:
        if not os.path.exists(cache_file):
            log_data_operation("警告", f"缓存文件 {cache_file} 不存在")
            return False

        with open(cache_file, 'rb') as f:
            data = pickle.load(f)

        # 对于股票名称缓存，检查是否为DataFrame且有必要的列
        if cache_file == STOCK_NAMES_CACHE_FILE:
            if not isinstance(data, pd.DataFrame):
                log_data_operation("警告", f"缓存文件 {cache_file} 内容不是DataFrame")
                return False

            if 'code' not in data.columns or 'name' not in data.columns:
                log_data_operation("警告", f"缓存文件 {cache_file} 中缺少必要列(code/name)")
                return False

            # 检查数据数量，A股通常有4000多只股票
            if len(data) < 1000:
                log_data_operation("警告", f"缓存文件 {cache_file} 包含的股票数量异常 ({len(data)})")
                return False

        return True
    except Exception as e:
        log_data_operation("错误", f"检查缓存文件 {cache_file} 时出错: {str(e)}")

        # 如果文件存在但无效，尝试创建备份并删除
        if os.path.exists(cache_file):
            try:
                # 创建备份目录
                backup_dir = os.path.join(CACHE_DIR, "corrupted_backups")
                os.makedirs(backup_dir, exist_ok=True)

                # 创建备份文件名
                backup_file = os.path.join(backup_dir, f"{os.path.basename(cache_file)}.corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}")

                # 备份损坏的文件
                shutil.copy2(cache_file, backup_file)
                log_data_operation("警告", f"已备份损坏的缓存文件到 {backup_file}")

                # 删除损坏的缓存文件
                os.remove(cache_file)
                log_data_operation("警告", f"已删除损坏的缓存文件 {cache_file}")
            except Exception as backup_err:
                log_data_operation("错误", f"备份/删除损坏的缓存文件时出错: {str(backup_err)}")

        return False

def retry_on_exception(max_retries=3, initial_delay=1, backoff_factor=2):
    """重试装饰器，用于网络请求等容易失败的操作"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for retry in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if retry == max_retries - 1:
                        # 最后一次重试失败，抛出异常
                        raise
                    log_data_operation("重试警告", f"函数 {func.__name__} 执行失败 (尝试 {retry+1}/{max_retries}): {str(e)}")
                    time.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator

def load_stock_names(force_refresh=False):
    """
    加载或获取股票代码和名称映射表

    Args:
        force_refresh: 是否强制刷新数据

    Returns:
        DataFrame: 包含股票代码和名称的DataFrame
    """
    global _stock_names_df

    # 如果内存中已有数据且不强制刷新，直接返回
    if _stock_names_df is not None and not force_refresh:
        return _stock_names_df

    try:
        # 检查缓存文件是否存在且有效
        if os.path.exists(STOCK_NAMES_CACHE_FILE) and not force_refresh:
            # 验证缓存文件有效性
            if not check_pickle_validity(STOCK_NAMES_CACHE_FILE):
                log_data_operation("警告", "股票名称缓存文件无效，将重新获取数据")
                if os.path.exists(STOCK_NAMES_CACHE_FILE):
                    os.remove(STOCK_NAMES_CACHE_FILE)
            else:
                # 检查文件修改时间
                file_time = datetime.fromtimestamp(os.path.getmtime(STOCK_NAMES_CACHE_FILE))
                current_time = datetime.now()
                # 如果文件修改时间不超过一周，直接加载
                if (current_time - file_time) < timedelta(days=7):
                    log_data_operation("股票名称", f"缓存文件有效期内 ({(current_time - file_time).days} 天)，直接使用")
                    try:
                        with open(STOCK_NAMES_CACHE_FILE, 'rb') as f:
                            _stock_names_df = pickle.load(f)
                        log_data_operation("股票名称", f"成功从缓存加载股票数据，共 {len(_stock_names_df)} 条记录")
                        return _stock_names_df
                    except Exception as load_e:
                        log_data_operation("错误", f"从缓存加载股票数据时出错: {str(load_e)}")
                        # 删除可能损坏的缓存文件
                        if os.path.exists(STOCK_NAMES_CACHE_FILE):
                            os.remove(STOCK_NAMES_CACHE_FILE)
                else:
                    log_data_operation("股票名称", f"缓存文件已过期 ({(current_time - file_time).days} 天)，重新获取数据")
        else:
            if force_refresh:
                log_data_operation("股票名称", "强制刷新数据")
            else:
                log_data_operation("股票名称", "未找到缓存文件，从API获取数据")

        # 获取新数据
        try:
            _stock_names_df = ak.stock_info_a_code_name()

            # 检查数据有效性
            if _stock_names_df is None or len(_stock_names_df) < 1000:
                raise ValueError(f"获取的股票数据不完整，仅有 {0 if _stock_names_df is None else len(_stock_names_df)} 条记录")

            # 保存到本地文件
            with _cache_lock:
                with open(STOCK_NAMES_CACHE_FILE, 'wb') as f:
                    pickle.dump(_stock_names_df, f)

            log_data_operation("股票名称", f"成功获取并缓存股票数据，共 {len(_stock_names_df)} 条记录")
            return _stock_names_df
        except Exception as api_e:
            log_data_operation("错误", f"从API获取股票数据时出错: {str(api_e)}")

            # 尝试使用备用方法构建基本的股票名称数据
            try:
                log_data_operation("股票名称", "尝试使用备用方法构建基础股票名称数据")

                # 创建一个基本的股票名称DataFrame
                codes = []
                names = []

                # 添加沪市主板股票代码 (600000-603999)
                for code in range(600000, 604000):
                    codes.append(str(code))
                    names.append(f"未知股票{code}")

                # 添加沪市科创板股票代码 (688000-689999)
                for code in range(688000, 690000):
                    codes.append(str(code))
                    names.append(f"未知股票{code}")

                # 添加深市主板股票代码 (000001-001999)
                for code in range(1, 2000):
                    codes.append(f"{code:06d}")
                    names.append(f"未知股票{code:06d}")

                # 添加深市创业板股票代码 (300000-301999)
                for code in range(300000, 302000):
                    codes.append(str(code))
                    names.append(f"未知股票{code}")

                # 创建DataFrame
                _stock_names_df = pd.DataFrame({
                    'code': codes,
                    'name': names
                })

                # 保存到本地文件
                with _cache_lock:
                    with open(STOCK_NAMES_CACHE_FILE, 'wb') as f:
                        pickle.dump(_stock_names_df, f)

                log_data_operation("股票名称", f"成功创建基础股票名称数据，共 {len(_stock_names_df)} 条记录（无实际名称）")
                log_data_operation("警告", "此数据仅包含代码，无实际股票名称，仅作为临时解决方案")
                return _stock_names_df
            except Exception as backup_e:
                log_data_operation("错误", f"创建基础股票名称数据时出错: {str(backup_e)}")
                # 返回空DataFrame
                _stock_names_df = pd.DataFrame(columns=["code", "name"])
                return _stock_names_df

    except Exception as e:
        log_data_operation("错误", f"加载股票名称数据时出错: {str(e)}")
        # 如果出错且内存中有数据，返回内存数据
        if _stock_names_df is not None:
            return _stock_names_df
        # 否则返回空DataFrame
        _stock_names_df = pd.DataFrame(columns=["code", "name"])
        return _stock_names_df

def get_stock_name(ticker):
    """
    根据股票代码获取股票名称

    Args:
        ticker: 股票代码，如"600519"

    Returns:
        str: 股票名称，如获取失败则返回"未知股票"
    """
    try:
        # 获取股票数据
        stock_df = load_stock_names()

        # 查找匹配的股票
        stock_info = stock_df[stock_df['code'] == ticker]
        if not stock_info.empty:
            return stock_info['name'].values[0]

        return "未知股票"
    except Exception as e:
        log_data_operation("错误", f"获取股票名称时出错: {str(e)}")
        return "未知股票"

@retry_on_exception(max_retries=3, initial_delay=2, backoff_factor=2)
def get_historical_data(symbol, start_date=None, end_date=None, use_cache=True):
    """
    获取股票历史数据

    Args:
        symbol: 股票代码
        start_date: 开始日期，格式为'YYYY-MM-DD'，如果为None则取一年前
        end_date: 结束日期，格式为'YYYY-MM-DD'，如果为None则取昨天
        use_cache: 是否使用缓存

    Returns:
        DataFrame: 包含历史数据的DataFrame
    """
    try:
        # 设置默认日期
        if end_date is None:
            current_date = datetime.now()
            yesterday = current_date - timedelta(days=1)
            end_date = yesterday.strftime('%Y-%m-%d')

        if start_date is None:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            start_datetime = end_datetime - timedelta(days=365)
            start_date = start_datetime.strftime('%Y-%m-%d')

        # 缓存文件路径
        cache_file = os.path.join(HISTORICAL_DATA_CACHE_DIR, f"{symbol}_{start_date}_{end_date}.pkl")

        # 如果使用缓存且缓存文件存在，直接加载
        if use_cache and os.path.exists(cache_file):
            # 验证缓存文件有效性
            if not check_pickle_validity(cache_file):
                log_data_operation("警告", f"历史数据缓存文件无效: {cache_file}，将重新获取数据")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            else:
                file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
                current_time = datetime.now()

                # 如果缓存文件不超过1天，直接使用
                if (current_time - file_time) < timedelta(days=1):
                    try:
                        log_data_operation("历史数据", f"使用缓存的历史数据 ({symbol}, {start_date} 至 {end_date})")
                        with open(cache_file, 'rb') as f:
                            return pickle.load(f)
                    except Exception as load_e:
                        log_data_operation("错误", f"从缓存加载历史数据时出错: {str(load_e)}")
                        # 删除可能损坏的缓存文件
                        if os.path.exists(cache_file):
                            os.remove(cache_file)

        log_data_operation("历史数据", f"获取历史数据 ({symbol}, {start_date} 至 {end_date})")

        # 判断股票代码前缀
        prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
        format_symbol = f"{prefix}{symbol}"

        # 转换日期格式为YYYYMMDD
        format_start_date = start_date.replace('-', '')
        format_end_date = end_date.replace('-', '')

        # 获取历史数据
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=format_start_date,
            end_date=format_end_date,
            adjust="qfq"
        )

        # 检查数据有效性
        if df is None or df.empty:
            log_data_operation("警告", f"获取 {symbol} 的历史数据为空，尝试不限日期获取")

            # 尝试不限制日期获取
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                adjust="qfq"
            )

        # 如果仍然没有数据，返回空DataFrame
        if df is None or df.empty:
            log_data_operation("错误", f"无法获取 {symbol} 的历史数据")
            return pd.DataFrame()

        # 处理列名
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change',
            '换手率': 'turnover'
        })

        # 保存到缓存
        try:
            with _cache_lock:
                with open(cache_file, 'wb') as f:
                    pickle.dump(df, f)
            log_data_operation("历史数据", f"成功缓存历史数据 ({symbol})")
        except Exception as cache_e:
            log_data_operation("警告", f"缓存历史数据时出错: {str(cache_e)}")

        log_data_operation("历史数据", f"成功获取 {symbol} 的历史数据，共 {len(df)} 条记录")
        return df

    except Exception as e:
        log_data_operation("错误", f"获取历史数据时出错: {str(e)}")
        return pd.DataFrame()

@retry_on_exception(max_retries=3, initial_delay=2, backoff_factor=2)
def get_market_data(symbol):
    """
    获取市场实时数据

    Args:
        symbol: 股票代码

    Returns:
        dict: 市场数据
    """
    # 检查缓存
    cache_key = f"market_data_{symbol}"
    current_time = datetime.now()

    # 如果缓存存在且未过期，直接返回缓存数据
    if (cache_key in _market_data_cache and
        _cache_expiry.get(cache_key, datetime.min) > current_time):
        log_data_operation("市场数据", f"使用缓存的市场数据 (symbol={symbol})")
        return _market_data_cache[cache_key]

    start_time = time.time()

    # 尝试直接获取（从最快的数据源）
    try:
        # 从腾讯财经直接获取（通常最快）
        log_data_operation("市场数据", f"直接获取 {symbol} 的市场数据...")
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
            log_data_operation("市场数据", f"直接获取成功，耗时 {elapsed:.2f} 秒")

            # 更新缓存
            _market_data_cache[cache_key] = result
            # 缓存保留1小时
            _cache_expiry[cache_key] = current_time + timedelta(hours=1)

            return result
    except Exception as e:
        log_data_operation("警告", f"直接获取市场数据失败: {e}，尝试其他数据源...")

    # 如果直接获取失败，尝试通过定义的数据源获取
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
                "average_volume": float(stock_data.get("成交量", 0)),
                "fifty_two_week_high": float(stock_data.get("52周最高", stock_data.get("最高", 0))),
                "fifty_two_week_low": float(stock_data.get("52周最低", stock_data.get("最低", 0))),
                "is_expired_cache": False,
                "data_source": "东方财富",
                "price": float(stock_data.get("最新价", 0))
            }

            return result
        except Exception as e:
            log_data_operation("警告", f"处理东方财富数据时出错: {e}")
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
                "data_source": "新浪财经",
                "price": float(stock_data.get("最新价", 0))
            }

            return result
        except Exception as e:
            log_data_operation("警告", f"处理新浪数据时出错: {e}")
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
                    log_data_operation("市场数据", f"成功从{source_name}获取市场数据")
                    break  # 一旦获得一个有效结果就停止等待
                else:
                    error_messages.append(f"从{source_name}获取数据失败")
            except Exception as e:
                error_messages.append(f"从{source_name}获取数据出错: {str(e)}")

    # 如果所有数据源都失败，检查缓存
    if result is None:
        error_message = f"警告：未能从任何数据源获取到 {symbol} 的市场数据"
        log_data_operation("警告", error_message)
        error_messages.append(error_message)

        # 如果有缓存但已过期，在出错时仍然返回过期的缓存数据，但标记为过期
        if cache_key in _market_data_cache:
            log_data_operation("市场数据", f"使用过期的缓存数据 (symbol={symbol})")
            cached_data = _market_data_cache[cache_key].copy()
            cached_data["is_expired_cache"] = True
            cached_data["error_messages"] = error_messages
            return cached_data

        # 如果没有缓存，则抛出异常
        raise ValueError(f"无法获取市场数据: {'; '.join(error_messages)}")

    # 检查数据有效性
    if "market_cap" in result and result["market_cap"] <= 0:
        log_data_operation("警告", f"股票 {symbol} 的市值数据无效或缺失")
        # 尝试从其他数据源补充市值数据
        for source_name, get_data_func in data_sources:
            if source_name != result["data_source"]:
                supplementary_data = get_data_func()
                if supplementary_data is not None and supplementary_data.get("market_cap", 0) > 0:
                    result["market_cap"] = supplementary_data["market_cap"]
                    log_data_operation("市场数据", f"使用{source_name}的市值数据进行补充")
                    break

    if "volume" in result and result["volume"] < 0:
        log_data_operation("警告", f"股票 {symbol} 的成交量数据无效")
        result["volume"] = 0

    # 更新缓存
    _market_data_cache[cache_key] = result
    # 缓存保留较短时间（当日行情数据变化快）
    _cache_expiry[cache_key] = current_time + timedelta(minutes=30)

    log_data_operation("市场数据", f"成功获取 {symbol} 的市场数据，总耗时 {time.time() - start_time:.2f} 秒")
    return result

# 批量获取市场数据
def get_market_data_batch(symbols, max_workers=5):
    """
    批量获取多个股票的市场数据

    Args:
        symbols: 股票代码列表
        max_workers: 最大并行获取数量

    Returns:
        dict: 股票代码到市场数据的映射
    """
    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_symbol = {executor.submit(get_market_data, symbol): symbol for symbol in symbols}

        # 获取结果
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                data = future.result()
                results[symbol] = data
            except Exception as e:
                log_data_operation("错误", f"获取 {symbol} 的市场数据失败: {str(e)}")
                # 添加错误信息
                results[symbol] = {"error": str(e), "is_error": True}

    return results

# 初始化时预加载股票名称数据
load_stock_names()