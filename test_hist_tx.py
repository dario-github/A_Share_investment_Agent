#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 akshare 库中的 stock_zh_a_hist_tx 函数
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

def test_stock_zh_a_hist_tx(ticker):
    """测试 stock_zh_a_hist_tx 函数"""
    print(f"\n===== 测试 stock_zh_a_hist_tx 函数 (股票代码: {ticker}) =====")

    # 查看函数签名
    import inspect
    print(f"函数签名: {inspect.signature(ak.stock_zh_a_hist_tx)}")

    # 测试不同的参数组合
    test_cases = [
        {
            "name": "基本参数",
            "params": {
                "symbol": ticker,
                "start_date": "20240101",
                "end_date": "20250101",
                "adjust": "qfq"
            }
        },
        {
            "name": "不指定日期",
            "params": {
                "symbol": ticker,
                "adjust": "qfq"
            }
        },
        {
            "name": "不复权",
            "params": {
                "symbol": ticker,
                "start_date": "20240101",
                "end_date": "20250101",
                "adjust": ""
            }
        },
        {
            "name": "后复权",
            "params": {
                "symbol": ticker,
                "start_date": "20240101",
                "end_date": "20250101",
                "adjust": "hfq"
            }
        },
        {
            "name": "添加市场后缀",
            "params": {
                "symbol": f"{ticker}.{'SH' if ticker.startswith('6') else 'SZ'}",
                "start_date": "20240101",
                "end_date": "20250101",
                "adjust": "qfq"
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n测试 {test_case['name']}:")
        print(f"参数: {test_case['params']}")

        try:
            df = ak.stock_zh_a_hist_tx(**test_case['params'])

            if df is not None and not df.empty:
                print(f"✓ 成功获取数据，共 {len(df)} 条记录")
                print("\n数据示例:")
                print(df.head(3))
                print("\n数据列名:")
                print(df.columns.tolist())
                return df
            else:
                print(f"✗ 获取数据失败或数据为空")
        except Exception as e:
            print(f"✗ 测试出错: {str(e)}")

        # 添加延迟，避免频繁请求
        time.sleep(1)

    return pd.DataFrame()

def main():
    # 获取命令行参数
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        test_stock_zh_a_hist_tx(ticker)
    else:
        # 测试多个常见股票代码
        test_stocks = [
            "600519",  # 贵州茅台 (上海)
            "000858",  # 五粮液 (深圳)
            "300059",  # 东方财富 (创业板)
            "300857",  # 协创数据 (创业板，原始错误代码)
        ]

        for stock in test_stocks:
            test_stock_zh_a_hist_tx(stock)
            print("\n" + "="*50)

    print("\n测试完成！")

if __name__ == "__main__":
    main()