"""简单测试脚本，验证API修复是否有效"""

import time
from datetime import datetime, timedelta

# 导入我们的自定义API
from src.tools.fast_api import get_market_data_fast, get_price_history_fast

def test_market_data():
    """测试市场数据获取函数"""
    print("\n===== 测试市场数据获取 =====")
    symbols = ["000001", "600036"]

    for symbol in symbols:
        print(f"\n获取 {symbol} 的市场数据...")
        start_time = time.time()
        data = get_market_data_fast(symbol)
        elapsed = time.time() - start_time

        if data is not None:
            print(f"成功获取数据，耗时 {elapsed:.2f} 秒")
            print(f"数据样例: 市值={data.get('market_cap')}, 成交量={data.get('volume')}")
        else:
            print(f"获取数据失败，耗时 {elapsed:.2f} 秒")

def test_price_history():
    """测试历史价格数据获取函数"""
    print("\n===== 测试历史价格数据获取 =====")
    symbols = ["000001", "600036"]

    # 设置日期范围 - 最近30天
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"日期范围: {start_date} 至 {end_date}")

    for symbol in symbols:
        print(f"\n获取 {symbol} 的历史价格数据...")
        start_time = time.time()
        df = get_price_history_fast(symbol, start_date, end_date, compute_indicators=False)
        elapsed = time.time() - start_time

        if df is not None and not df.empty:
            print(f"成功获取数据，共 {len(df)} 条记录，耗时 {elapsed:.2f} 秒")
            print(f"数据样例: {df.head(1)}")
        else:
            print(f"获取数据失败，耗时 {elapsed:.2f} 秒")

if __name__ == "__main__":
    print("开始测试优化后的API...")

    # 测试市场数据获取
    test_market_data()

    # 测试历史价格数据获取
    test_price_history()

    print("\n测试完成!")