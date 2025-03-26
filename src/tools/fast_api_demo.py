import time
import pandas as pd
from datetime import datetime, timedelta

# 导入旧的API函数
from src.tools.api import get_market_data, get_price_history

# 导入新的快速API函数
from src.tools.fast_api import get_market_data_fast, get_price_history_fast

def test_market_data_performance(symbols: list, repeat: int = 1):
    """
    测试市场数据获取性能

    Args:
        symbols: 要测试的股票代码列表
        repeat: 重复测试次数
    """
    print(f"===== 测试市场数据获取性能 (股票: {symbols}, 重复次数: {repeat}) =====")

    # 记录总时间
    old_api_total_time = 0
    new_api_total_time = 0

    for i in range(repeat):
        print(f"\n测试轮次 {i+1}/{repeat}")

        # 测试原有API
        print("\n使用原有API获取市场数据:")
        old_api_start = time.time()

        for symbol in symbols:
            print(f"  获取 {symbol} 的市场数据...")
            symbol_start = time.time()
            data = get_market_data(symbol)
            symbol_time = time.time() - symbol_start
            print(f"  完成，耗时: {symbol_time:.2f} 秒")

        old_api_time = time.time() - old_api_start
        old_api_total_time += old_api_time
        print(f"原有API总耗时: {old_api_time:.2f} 秒")

        # 等待一段时间，避免API限制
        time.sleep(2)

        # 测试新API
        print("\n使用并行API获取市场数据:")
        new_api_start = time.time()

        for symbol in symbols:
            print(f"  获取 {symbol} 的市场数据...")
            symbol_start = time.time()
            data = get_market_data_fast(symbol)
            symbol_time = time.time() - symbol_start
            print(f"  完成，耗时: {symbol_time:.2f} 秒")

        new_api_time = time.time() - new_api_start
        new_api_total_time += new_api_time
        print(f"并行API总耗时: {new_api_time:.2f} 秒")

        # 计算加速比
        speedup = old_api_time / new_api_time if new_api_time > 0 else float('inf')
        print(f"\n本轮加速比: {speedup:.2f}x")

    # 计算平均时间
    old_api_avg = old_api_total_time / repeat
    new_api_avg = new_api_total_time / repeat
    avg_speedup = old_api_avg / new_api_avg if new_api_avg > 0 else float('inf')

    print(f"\n===== 性能测试结果 =====")
    print(f"原有API平均耗时: {old_api_avg:.2f} 秒")
    print(f"并行API平均耗时: {new_api_avg:.2f} 秒")
    print(f"平均加速比: {avg_speedup:.2f}x")


def test_price_history_performance(symbols: list, days: int = 365, repeat: int = 1):
    """
    测试历史价格数据获取性能

    Args:
        symbols: 要测试的股票代码列表
        days: 获取多少天的历史数据
        repeat: 重复测试次数
    """
    print(f"===== 测试历史价格数据获取性能 (股票: {symbols}, 天数: {days}, 重复次数: {repeat}) =====")

    # 设置日期范围
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days)

    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    print(f"日期范围: {start_date_str} 至 {end_date_str}")

    # 记录总时间
    old_api_total_time = 0
    new_api_total_time = 0

    for i in range(repeat):
        print(f"\n测试轮次 {i+1}/{repeat}")

        # 测试原有API
        print("\n使用原有API获取历史价格数据:")
        old_api_start = time.time()

        for symbol in symbols:
            print(f"  获取 {symbol} 的历史价格数据...")
            symbol_start = time.time()
            df = get_price_history(symbol, start_date_str, end_date_str)
            records = len(df) if df is not None and not df.empty else 0
            symbol_time = time.time() - symbol_start
            print(f"  完成，获取 {records} 条记录，耗时: {symbol_time:.2f} 秒")

        old_api_time = time.time() - old_api_start
        old_api_total_time += old_api_time
        print(f"原有API总耗时: {old_api_time:.2f} 秒")

        # 等待一段时间，避免API限制
        time.sleep(5)

        # 测试新API
        print("\n使用并行API获取历史价格数据:")
        new_api_start = time.time()

        for symbol in symbols:
            print(f"  获取 {symbol} 的历史价格数据...")
            symbol_start = time.time()
            df = get_price_history_fast(symbol, start_date_str, end_date_str, compute_indicators=False)
            records = len(df) if df is not None and not df.empty else 0
            symbol_time = time.time() - symbol_start
            print(f"  完成，获取 {records} 条记录，耗时: {symbol_time:.2f} 秒")

        new_api_time = time.time() - new_api_start
        new_api_total_time += new_api_time
        print(f"并行API总耗时: {new_api_time:.2f} 秒")

        # 计算加速比
        speedup = old_api_time / new_api_time if new_api_time > 0 else float('inf')
        print(f"\n本轮加速比: {speedup:.2f}x")

    # 计算平均时间
    old_api_avg = old_api_total_time / repeat
    new_api_avg = new_api_total_time / repeat
    avg_speedup = old_api_avg / new_api_avg if new_api_avg > 0 else float('inf')

    print(f"\n===== 性能测试结果 =====")
    print(f"原有API平均耗时: {old_api_avg:.2f} 秒")
    print(f"并行API平均耗时: {new_api_avg:.2f} 秒")
    print(f"平均加速比: {avg_speedup:.2f}x")


if __name__ == "__main__":
    # 定义要测试的股票
    test_symbols = ["000001", "600036", "601318"]

    # 测试市场数据获取性能
    test_market_data_performance(test_symbols, repeat=1)

    # 测试历史价格数据获取性能
    test_price_history_performance(test_symbols, days=365, repeat=1)