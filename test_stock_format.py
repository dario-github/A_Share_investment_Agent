#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试不同格式的股票代码在 akshare 中的使用
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys

def test_stock_code_format(ticker):
    """测试不同格式的股票代码"""
    print(f"\n===== 测试股票代码 {ticker} 的格式 =====")

    # 测试原始代码
    print(f"\n1. 测试原始代码: {ticker}")
    test_with_code(ticker)

    # 测试添加市场后缀的代码
    if ticker.startswith('6'):
        # 上海市场
        formatted_ticker = f"{ticker}.SH"
        print(f"\n2. 测试上海市场代码: {formatted_ticker}")
        test_with_code(formatted_ticker)
    elif ticker.startswith('0') or ticker.startswith('3'):
        # 深圳市场
        formatted_ticker = f"{ticker}.SZ"
        print(f"\n2. 测试深圳市场代码: {formatted_ticker}")
        test_with_code(formatted_ticker)

    # 测试添加前导零的代码
    if len(ticker) < 6:
        padded_ticker = ticker.zfill(6)
        print(f"\n3. 测试添加前导零的代码: {padded_ticker}")
        test_with_code(padded_ticker)

def test_with_code(code):
    """使用指定的代码测试 akshare 功能"""
    try:
        # 尝试获取股票信息
        print(f"尝试获取股票 {code} 的基本信息...")
        stock_df = ak.stock_zh_a_spot_em()

        # 对于带后缀的代码，需要去掉后缀再查询
        search_code = code.split('.')[0] if '.' in code else code

        stock_info = stock_df[stock_df['代码'] == search_code]
        if not stock_info.empty:
            print(f"✓ 成功找到股票信息: {stock_info['名称'].values[0]}")
        else:
            print(f"✗ 未找到股票信息")

        # 尝试获取历史数据
        print(f"尝试获取股票 {code} 的历史行情数据...")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        last_year = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=last_year,
            end_date=yesterday,
            adjust="qfq"
        )

        if not df.empty:
            print(f"✓ 成功获取历史数据，共 {len(df)} 条记录")
        else:
            print(f"✗ 获取历史数据失败或数据为空")

    except Exception as e:
        print(f"✗ 测试出错: {str(e)}")

def test_multiple_stocks():
    """测试多个常见股票代码"""
    test_stocks = [
        "600519",  # 贵州茅台 (上海)
        "000858",  # 五粮液 (深圳)
        "300059",  # 东方财富 (创业板)
        "688981",  # 中芯国际 (科创板)
        "300857",  # 协创数据 (创业板，原始错误代码)
    ]

    for stock in test_stocks:
        test_stock_code_format(stock)
        print("\n" + "="*50)

def main():
    # 获取命令行参数
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        test_stock_code_format(ticker)
    else:
        print("测试多个常见股票代码...")
        test_multiple_stocks()

    print("\n测试完成！")

if __name__ == "__main__":
    main()