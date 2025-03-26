#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 akshare 库中的新函数
"""

import akshare as ak
import pandas as pd
import sys
import time

def test_stock_zh_a_hist_tx(ticker):
    """测试 stock_zh_a_hist_tx 函数"""
    print(f"\n===== 测试 stock_zh_a_hist_tx 函数 (股票代码: {ticker}) =====")

    try:
        # 尝试获取历史数据
        print(f"正在获取股票 {ticker} 的历史行情数据...")
        df = ak.stock_zh_a_hist_tx(symbol=ticker, start_date="20240101", end_date="20250101", adjust="qfq")

        if df is not None and not df.empty:
            print(f"✓ 成功获取数据，共 {len(df)} 条记录")
            print("\n数据示例:")
            print(df.head(3))
            return df
        else:
            print(f"✗ 获取数据失败或数据为空")
            return pd.DataFrame()
    except Exception as e:
        print(f"✗ 测试出错: {str(e)}")
        return pd.DataFrame()

def test_stock_zh_a_hist_min_em(ticker):
    """测试 stock_zh_a_hist_min_em 函数"""
    print(f"\n===== 测试 stock_zh_a_hist_min_em 函数 (股票代码: {ticker}) =====")

    try:
        # 尝试获取分钟级历史数据
        print(f"正在获取股票 {ticker} 的分钟级历史行情数据...")
        df = ak.stock_zh_a_hist_min_em(symbol=ticker, period="1", adjust="qfq", start_date="2024-01-01 09:30:00", end_date="2025-01-01 15:00:00")

        if df is not None and not df.empty:
            print(f"✓ 成功获取数据，共 {len(df)} 条记录")
            print("\n数据示例:")
            print(df.head(3))
            return df
        else:
            print(f"✗ 获取数据失败或数据为空")
            return pd.DataFrame()
    except Exception as e:
        print(f"✗ 测试出错: {str(e)}")
        return pd.DataFrame()

def test_stock_zh_a_hist_pre_min_em(ticker):
    """测试 stock_zh_a_hist_pre_min_em 函数"""
    print(f"\n===== 测试 stock_zh_a_hist_pre_min_em 函数 (股票代码: {ticker}) =====")

    try:
        # 尝试获取盘前分钟级历史数据
        print(f"正在获取股票 {ticker} 的盘前分钟级历史行情数据...")
        df = ak.stock_zh_a_hist_pre_min_em(symbol=ticker)

        if df is not None and not df.empty:
            print(f"✓ 成功获取数据，共 {len(df)} 条记录")
            print("\n数据示例:")
            print(df.head(3))
            return df
        else:
            print(f"✗ 获取数据失败或数据为空")
            return pd.DataFrame()
    except Exception as e:
        print(f"✗ 测试出错: {str(e)}")
        return pd.DataFrame()

def test_rv_from_stock_zh_a_hist_min_em(ticker):
    """测试 rv_from_stock_zh_a_hist_min_em 函数"""
    print(f"\n===== 测试 rv_from_stock_zh_a_hist_min_em 函数 (股票代码: {ticker}) =====")

    try:
        # 尝试获取历史波动率数据
        print(f"正在获取股票 {ticker} 的历史波动率数据...")
        # 查看函数签名
        import inspect
        print(f"函数签名: {inspect.signature(ak.rv_from_stock_zh_a_hist_min_em)}")

        # 尝试不同的参数组合
        df = ak.rv_from_stock_zh_a_hist_min_em(symbol=ticker, period="1")

        if df is not None and not df.empty:
            print(f"✓ 成功获取数据，共 {len(df)} 条记录")
            print("\n数据示例:")
            print(df.head(3))
            return df
        else:
            print(f"✗ 获取数据失败或数据为空")
            return pd.DataFrame()
    except Exception as e:
        print(f"✗ 测试出错: {str(e)}")
        return pd.DataFrame()

def test_all_new_functions(ticker):
    """测试所有新函数"""
    print(f"\n{'='*20} 测试股票: {ticker} {'='*20}")

    # 测试各种新函数
    test_stock_zh_a_hist_tx(ticker)
    test_stock_zh_a_hist_min_em(ticker)
    test_stock_zh_a_hist_pre_min_em(ticker)
    test_rv_from_stock_zh_a_hist_min_em(ticker)

def main():
    # 获取命令行参数
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        test_all_new_functions(ticker)
    else:
        # 测试多个常见股票代码
        test_stocks = [
            "600519",  # 贵州茅台 (上海)
            "000858",  # 五粮液 (深圳)
            "300059",  # 东方财富 (创业板)
            "300857",  # 协创数据 (创业板，原始错误代码)
        ]

        for stock in test_stocks:
            test_all_new_functions(stock)
            print("\n" + "="*50)

    print("\n测试完成！")

if __name__ == "__main__":
    main()