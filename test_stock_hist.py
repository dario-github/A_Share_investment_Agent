#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
专门测试 akshare 库中 stock_zh_a_hist 函数的功能
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

def test_stock_hist_function(ticker, verbose=True):
    """测试 stock_zh_a_hist 函数的各种参数组合"""
    print(f"\n===== 测试 stock_zh_a_hist 函数 (股票代码: {ticker}) =====")

    # 计算日期范围
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)
    last_year = current_date - timedelta(days=365)

    # 测试不同的参数组合
    test_cases = [
        {
            "name": "基本参数",
            "params": {
                "symbol": ticker,
                "period": "daily",
                "adjust": "qfq"
            }
        },
        {
            "name": "指定日期范围",
            "params": {
                "symbol": ticker,
                "period": "daily",
                "start_date": last_year.strftime("%Y%m%d"),
                "end_date": yesterday.strftime("%Y%m%d"),
                "adjust": "qfq"
            }
        },
        {
            "name": "不复权",
            "params": {
                "symbol": ticker,
                "period": "daily",
                "adjust": ""
            }
        },
        {
            "name": "后复权",
            "params": {
                "symbol": ticker,
                "period": "daily",
                "adjust": "hfq"
            }
        },
        {
            "name": "周期数据",
            "params": {
                "symbol": ticker,
                "period": "weekly",
                "adjust": "qfq"
            }
        },
        {
            "name": "月度数据",
            "params": {
                "symbol": ticker,
                "period": "monthly",
                "adjust": "qfq"
            }
        }
    ]

    # 如果股票代码以6开头，测试上海市场代码格式
    if ticker.startswith('6'):
        test_cases.append({
            "name": "上海市场代码格式",
            "params": {
                "symbol": f"{ticker}.SH",
                "period": "daily",
                "adjust": "qfq"
            }
        })
    # 如果股票代码以0或3开头，测试深圳市场代码格式
    elif ticker.startswith('0') or ticker.startswith('3'):
        test_cases.append({
            "name": "深圳市场代码格式",
            "params": {
                "symbol": f"{ticker}.SZ",
                "period": "daily",
                "adjust": "qfq"
            }
        })

    results = []

    # 执行测试
    for test_case in test_cases:
        print(f"\n测试 {test_case['name']}:")
        print(f"参数: {test_case['params']}")

        start_time = time.time()
        try:
            df = ak.stock_zh_a_hist(**test_case['params'])
            end_time = time.time()
            duration = end_time - start_time

            if df is not None and not df.empty:
                print(f"✓ 成功获取数据，共 {len(df)} 条记录，耗时 {duration:.2f} 秒")
                if verbose:
                    print("\n数据示例:")
                    print(df.head(3))

                results.append({
                    "test_case": test_case['name'],
                    "success": True,
                    "records": len(df),
                    "duration": duration,
                    "error": None
                })
            else:
                print(f"✗ 获取数据失败或数据为空，耗时 {duration:.2f} 秒")
                results.append({
                    "test_case": test_case['name'],
                    "success": False,
                    "records": 0,
                    "duration": duration,
                    "error": "数据为空"
                })
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"✗ 测试出错: {str(e)}，耗时 {duration:.2f} 秒")
            results.append({
                "test_case": test_case['name'],
                "success": False,
                "records": 0,
                "duration": duration,
                "error": str(e)
            })

        # 添加延迟，避免频繁请求
        time.sleep(1)

    # 打印测试结果摘要
    print("\n===== 测试结果摘要 =====")
    success_count = sum(1 for r in results if r['success'])
    print(f"总测试用例: {len(results)}")
    print(f"成功用例: {success_count}")
    print(f"失败用例: {len(results) - success_count}")

    if len(results) - success_count > 0:
        print("\n失败用例详情:")
        for r in results:
            if not r['success']:
                print(f"- {r['test_case']}: {r['error']}")

    return results

def test_multiple_stocks():
    """测试多个常见股票代码"""
    test_stocks = [
        "600519",  # 贵州茅台 (上海)
        "000858",  # 五粮液 (深圳)
        "300059",  # 东方财富 (创业板)
        "300857",  # 协创数据 (创业板，原始错误代码)
    ]

    all_results = {}
    for stock in test_stocks:
        print(f"\n{'='*20} 测试股票: {stock} {'='*20}")
        results = test_stock_hist_function(stock, verbose=False)
        all_results[stock] = results

    # 打印总体结果
    print("\n\n===== 总体测试结果 =====")
    for stock, results in all_results.items():
        success_count = sum(1 for r in results if r['success'])
        print(f"股票 {stock}: 成功 {success_count}/{len(results)} 用例")

def main():
    # 获取命令行参数
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        test_stock_hist_function(ticker)
    else:
        print("测试多个常见股票代码...")
        test_multiple_stocks()

    print("\n测试完成！")

if __name__ == "__main__":
    main()