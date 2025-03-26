#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 akshare 库中获取股票历史行情数据的替代函数
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

def test_stock_zh_a_daily(ticker):
    """测试 stock_zh_a_daily 函数"""
    print(f"\n===== 测试 stock_zh_a_daily 函数 (股票代码: {ticker}) =====")

    try:
        # 尝试获取历史数据
        print(f"正在获取股票 {ticker} 的历史行情数据...")
        df = ak.stock_zh_a_daily(symbol=ticker, start_date="20240101", end_date="20250101", adjust="qfq")

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

def test_stock_zh_a_hist_163(ticker):
    """测试 stock_zh_a_hist_163 函数"""
    print(f"\n===== 测试 stock_zh_a_hist_163 函数 (股票代码: {ticker}) =====")

    try:
        # 尝试获取历史数据
        print(f"正在获取股票 {ticker} 的历史行情数据...")
        df = ak.stock_zh_a_hist_163(symbol=ticker, start_date="20240101", end_date="20250101", adjust="qfq")

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

def test_stock_zh_a_minute(ticker, period="1", adjust="qfq"):
    """测试 stock_zh_a_minute 函数"""
    print(f"\n===== 测试 stock_zh_a_minute 函数 (股票代码: {ticker}, 周期: {period}) =====")

    try:
        # 尝试获取分钟级数据
        print(f"正在获取股票 {ticker} 的分钟级行情数据...")
        df = ak.stock_zh_a_minute(symbol=ticker, period=period, adjust=adjust)

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

def test_stock_zh_ah_daily(ticker):
    """测试 stock_zh_ah_daily 函数"""
    print(f"\n===== 测试 stock_zh_ah_daily 函数 (股票代码: {ticker}) =====")

    try:
        # 尝试获取历史数据
        print(f"正在获取股票 {ticker} 的历史行情数据...")
        df = ak.stock_zh_ah_daily(symbol=ticker, start_year="2024", end_year="2025", adjust="qfq")

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

def test_all_alternatives(ticker):
    """测试所有替代函数"""
    print(f"\n{'='*20} 测试股票: {ticker} {'='*20}")

    # 测试各种替代函数
    test_stock_zh_a_daily(ticker)
    test_stock_zh_a_hist_163(ticker)
    test_stock_zh_a_minute(ticker)

    # 如果是 A+H 股，测试 A+H 股历史数据接口
    if ticker.startswith('6') or ticker.startswith('0') or ticker.startswith('3'):
        # 查询 A+H 股字典
        try:
            ah_name_df = ak.stock_zh_ah_name()
            if not ah_name_df.empty:
                # 检查是否是 A+H 股
                ah_stocks = ah_name_df['代码'].tolist()
                if ticker in ah_stocks:
                    test_stock_zh_ah_daily(ticker)
        except Exception as e:
            print(f"✗ 获取 A+H 股字典出错: {str(e)}")

def main():
    # 获取命令行参数
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        test_all_alternatives(ticker)
    else:
        # 测试多个常见股票代码
        test_stocks = [
            "600519",  # 贵州茅台 (上海)
            "000858",  # 五粮液 (深圳)
            "300059",  # 东方财富 (创业板)
            "300857",  # 协创数据 (创业板，原始错误代码)
        ]

        for stock in test_stocks:
            test_all_alternatives(stock)
            print("\n" + "="*50)

    print("\n测试完成！")

if __name__ == "__main__":
    main()