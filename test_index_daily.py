#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 akshare 库中的 stock_zh_index_daily_em 函数
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys

def test_stock_zh_index_daily_em(symbol):
    """测试 stock_zh_index_daily_em 函数"""
    print(f"\n===== 测试 stock_zh_index_daily_em 函数 (指数代码: {symbol}) =====")

    # 计算日期范围
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)
    end_date = yesterday  # 使用昨天作为结束日期
    start_date = yesterday - timedelta(days=365)  # 默认获取一年的数据

    print(f"开始日期: {start_date.strftime('%Y-%m-%d')}")
    print(f"结束日期: {end_date.strftime('%Y-%m-%d')}")

    try:
        # 查看函数签名
        import inspect
        print(f"函数签名: {inspect.signature(ak.stock_zh_index_daily_em)}")

        # 尝试获取历史数据
        print(f"正在获取指数 {symbol} 的历史行情数据...")
        df = ak.stock_zh_index_daily_em(symbol=symbol, start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"))

        if df is not None and not df.empty:
            print(f"✓ 成功获取数据，共 {len(df)} 条记录")
            print("\n数据示例:")
            print(df.head(5))
            print("\n数据列名:")
            print(df.columns.tolist())
            return df
        else:
            print(f"✗ 获取数据失败或数据为空")
            return pd.DataFrame()
    except Exception as e:
        print(f"✗ 测试出错: {str(e)}")
        return pd.DataFrame()

def main():
    # 测试多个指数代码
    test_indices = [
        "000001",  # 上证指数
        "399001",  # 深证成指
        "399006",  # 创业板指
        "000300",  # 沪深300
    ]

    for index in test_indices:
        test_stock_zh_index_daily_em(index)
        print("\n" + "="*50)

    print("\n测试完成！")

if __name__ == "__main__":
    main()