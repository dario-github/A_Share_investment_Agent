#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 akshare 库中的 stock_zh_a_daily 函数
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys

def test_stock_zh_a_daily(ticker):
    """测试 stock_zh_a_daily 函数"""
    print(f"\n===== 测试 stock_zh_a_daily 函数 (股票代码: {ticker}) =====")

    # 计算日期范围
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)
    end_date = yesterday  # 使用昨天作为结束日期
    start_date = yesterday - timedelta(days=365)  # 默认获取一年的数据

    print(f"开始日期: {start_date.strftime('%Y-%m-%d')}")
    print(f"结束日期: {end_date.strftime('%Y-%m-%d')}")

    try:
        # 尝试获取历史数据
        print(f"正在获取股票 {ticker} 的历史行情数据...")

        # 查看函数签名
        import inspect
        print(f"函数签名: {inspect.signature(ak.stock_zh_a_daily)}")

        # 尝试获取数据
        df = ak.stock_zh_a_daily(symbol=ticker, start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"), adjust="qfq")

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

        # 尝试不同的参数组合
        print("\n尝试不同的参数组合...")
        try:
            print("尝试不指定日期范围...")
            df = ak.stock_zh_a_daily(symbol=ticker, adjust="qfq")
            if df is not None and not df.empty:
                print(f"✓ 成功获取数据，共 {len(df)} 条记录")
                print("\n数据示例:")
                print(df.head(5))
                print("\n数据列名:")
                print(df.columns.tolist())
                return df
            else:
                print(f"✗ 获取数据失败或数据为空")
        except Exception as e2:
            print(f"✗ 再次尝试失败: {str(e2)}")

        return pd.DataFrame()

def main():
    # 获取命令行参数
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        test_stock_zh_a_daily(ticker)
    else:
        # 测试多个常见股票代码
        test_stocks = [
            "600519",  # 贵州茅台 (上海)
            "000858",  # 五粮液 (深圳)
            "300059",  # 东方财富 (创业板)
            "300857",  # 协创数据 (创业板，原始错误代码)
        ]

        for stock in test_stocks:
            test_stock_zh_a_daily(stock)
            print("\n" + "="*50)

    print("\n测试完成！")

if __name__ == "__main__":
    main()