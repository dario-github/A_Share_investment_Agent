import concurrent.futures
import time
import random
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, Any, List, Tuple, Callable

class ParallelDataFetcher:
    """并行数据获取器，用于同时从多个数据源获取数据"""

    def __init__(self, timeout=10, max_workers=3):
        """
        初始化并行数据获取器

        Args:
            timeout: 整体超时时间（秒）
            max_workers: 最大并行工作线程数
        """
        self.timeout = timeout
        self.max_workers = max_workers

    def fetch_market_data(self, symbol: str, data_sources: List[Tuple[str, Callable]]) -> Dict[str, Any]:
        """
        并行获取市场数据

        Args:
            symbol: 股票代码
            data_sources: 数据源列表，每项为(数据源名称, 获取函数)的元组

        Returns:
            从最快返回有效结果的数据源获取的数据
        """
        start_time = time.time()
        print(f"开始并行获取 {symbol} 的市场数据...")

        # 使用线程池并发执行所有数据源请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_source = {
                executor.submit(self._fetch_with_timeout, get_data_func, symbol): source_name
                for source_name, get_data_func in data_sources
            }

            # 获取最快返回有效结果的数据源
            results = []

            # 使用as_completed获取结果，这样可以处理最快返回的结果
            for future in concurrent.futures.as_completed(future_to_source, timeout=self.timeout):
                source_name = future_to_source[future]
                try:
                    data = future.result()
                    if data is not None and self._is_valid_data(data):
                        elapsed = time.time() - start_time
                        print(f"成功从 {source_name} 获取数据，耗时 {elapsed:.2f} 秒")
                        results.append((source_name, data, elapsed))
                except Exception as e:
                    print(f"从 {source_name} 获取数据时出错: {str(e)}")

                # 如果已经获取到足够的有效结果，可以提前退出
                if len(results) > 0:
                    # 注意：这里不取消其他任务，因为它们可能已经发出请求
                    # 取消可能不会节省太多时间，且可能导致资源泄漏
                    break

        # 根据速度排序结果，优先使用最快返回的有效数据
        if results:
            results.sort(key=lambda x: x[2])  # 按耗时排序
            source_name, data, elapsed = results[0]
            print(f"选择使用 {source_name} 的数据，总耗时 {elapsed:.2f} 秒")
            return data

        # 如果所有数据源都失败
        print(f"警告：所有数据源获取 {symbol} 数据失败，总耗时 {time.time() - start_time:.2f} 秒")
        return None

    def fetch_price_history(self, symbol: str, start_date: str, end_date: str,
                           data_sources: List[Tuple[str, Callable]], adjust: str = "qfq") -> pd.DataFrame:
        """
        并行获取历史价格数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            data_sources: 数据源列表，每项为(数据源名称, 获取函数)的元组
            adjust: 复权类型

        Returns:
            价格历史数据DataFrame
        """
        start_time = time.time()
        print(f"开始并行获取 {symbol} 的历史行情数据...")

        # 使用线程池并发执行所有数据源请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_source = {
                executor.submit(
                    self._fetch_price_with_timeout,
                    get_data_func,
                    symbol,
                    start_date,
                    end_date,
                    adjust
                ): source_name
                for source_name, get_data_func in data_sources
            }

            # 使用as_completed获取最快的有效结果
            results = []
            try:
                # 设置较短的总超时时间
                total_timeout = min(self.timeout, 5)
                for future in concurrent.futures.as_completed(future_to_source, timeout=total_timeout):
                    source_name = future_to_source[future]
                    try:
                        df = future.result(timeout=1.0)  # 单个结果等待时间短，快速失败
                        if df is not None and not df.empty and self._is_valid_price_data(df):
                            elapsed = time.time() - start_time
                            print(f"成功从 {source_name} 获取数据，记录数: {len(df)}，耗时 {elapsed:.2f} 秒")
                            results.append((source_name, df, elapsed, len(df)))

                            # 一旦有一个可用结果，就不再等待其他结果（针对单股票优化）
                            if len(results) >= 1:
                                break
                    except Exception as e:
                        print(f"从 {source_name} 获取数据时出错: {str(e)}")
            except concurrent.futures.TimeoutError:
                # 总体超时，但可能已经有结果了
                print(f"获取历史数据总体超时")

            # 选择数据量最大且速度最快的结果
            if results:
                # 首先按数据量排序（降序），然后按速度排序（升序）
                results.sort(key=lambda x: (-x[3], x[2]))
                source_name, df, elapsed, count = results[0]
                print(f"选择使用 {source_name} 的数据，{count} 条记录，总耗时 {elapsed:.2f} 秒")
                return df

        # 如果所有数据源都失败
        print(f"警告：所有数据源获取 {symbol} 历史数据失败，总耗时 {time.time() - start_time:.2f} 秒")
        return pd.DataFrame()

    def _fetch_with_timeout(self, fetch_func, symbol):
        """带超时的数据获取函数包装器"""
        try:
            return fetch_func(symbol)
        except Exception as e:
            print(f"数据获取超时或出错: {str(e)}")
            return None

    def _fetch_price_with_timeout(self, fetch_func, symbol, start_date, end_date, adjust):
        """带超时的价格数据获取函数包装器"""
        try:
            return fetch_func(symbol, start_date, end_date, adjust)
        except Exception as e:
            print(f"价格数据获取超时或出错: {str(e)}")
            return None

    def _is_valid_data(self, data):
        """检查市场数据是否有效"""
        if data is None:
            return False

        # 基本验证：检查是否为字典类型且包含必要字段
        if not isinstance(data, dict):
            return False

        # 简单验证，可根据实际数据结构调整
        required_fields = ["market_cap", "volume"]
        for field in required_fields:
            if field not in data:
                return False

        return True

    def _is_valid_price_data(self, df):
        """检查价格数据是否有效"""
        if df is None or df.empty:
            return False

        # 检查必要列是否存在（放宽要求，只需要close列）
        if "close" not in df.columns:
            return False

        # 检查记录数是否足够
        if len(df) < 5:  # 至少需要5条记录
            return False

        return True