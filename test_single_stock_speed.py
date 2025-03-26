"""测试单只股票获取的速度"""

import time
from datetime import datetime, timedelta

# 导入常规API
from src.tools.api import get_market_data, get_price_history
# 导入优化后的API
from src.tools.fast_api import get_market_data_fast, get_price_history_fast

def test_single_stock():
    """测试单只股票的获取速度"""
    # 测试的股票代码 - 平安银行
    symbol = "000001"

    # 设置日期范围 - 最近30天
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"\n===== 测试单只股票 ({symbol}) 数据获取性能 =====")
    print(f"日期范围: {start_date} 至 {end_date}")

    # 测试市场数据
    print("\n--- 市场数据获取 ---")
    print("1. 使用原始API:")
    old_start = time.time()
    data1 = get_market_data(symbol)
    old_time = time.time() - old_start
    print(f"   耗时: {old_time:.2f} 秒")

    time.sleep(1)  # 稍作等待

    print("2. 使用优化API:")
    new_start = time.time()
    data2 = get_market_data_fast(symbol)
    new_time = time.time() - new_start
    print(f"   耗时: {new_time:.2f} 秒")

    if new_time > 0 and old_time > 0:
        speedup = old_time / new_time
        print(f"   加速比: {speedup:.2f}x")

    # 测试历史价格数据
    print("\n--- 历史价格数据获取 ---")
    print("1. 使用原始API:")
    old_start = time.time()
    df1 = get_price_history(symbol, start_date, end_date)
    old_time = time.time() - old_start
    print(f"   获取 {len(df1) if df1 is not None and not df1.empty else 0} 条记录，耗时: {old_time:.2f} 秒")

    time.sleep(1)  # 稍作等待

    print("2. 使用优化API:")
    new_start = time.time()
    df2 = get_price_history_fast(symbol, start_date, end_date)
    new_time = time.time() - new_start
    print(f"   获取 {len(df2) if df2 is not None and not df2.empty else 0} 条记录，耗时: {new_time:.2f} 秒")

    if new_time > 0 and old_time > 0:
        speedup = old_time / new_time
        print(f"   加速比: {speedup:.2f}x")

    print("\n===== 测试完成 =====")

if __name__ == "__main__":
    test_single_stock()