#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 akshare 库中的 stock_zh_ah_daily 函数
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys

def test_stock_zh_ah_daily(ticker):
    """测试 stock_zh_ah_daily 函数"""
    print(f"\n===== 测试 stock_zh_ah_daily 函数 (股票代码: {ticker}) =====")

    try:
        # 首先获取 A+H 股票代码对应表
        print("获取 A+H 股票代码对应表...")
        ah_name_df = ak.stock_zh_ah_name()
        print(f"A+H 股票代码对应表共 {len(ah_name_df)} 条记录")

        # 检查股票是否在 A+H 股票列表中
        if ticker in ah_name_df['代码'].values:
            print(f"✓ 股票 {ticker} 在 A+H 股票列表中")

            # 获取对应的港股代码
            hk_code = ah_name_df[ah_name_df['代码'] == ticker]['港股代码'].values[0]
            print(f"对应的港股代码为: {hk_code}")

            # 尝试获取历史数据
            print(f"正在获取股票 {hk_code} 的历史行情数据...")

            # 查看函数签名
            import inspect
            print(f"函数签名: {inspect.signature(ak.stock_zh_ah_daily)}")

            # 尝试获取数据
            df = ak.stock_zh_ah_daily(symbol=hk_code, start_year="2024", end_year="2025", adjust="qfq")

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
        else:
            print(f"✗ 股票 {ticker} 不在 A+H 股票列表中")
            return pd.DataFrame()
    except Exception as e:
        print(f"✗ 测试出错: {str(e)}")
        return pd.DataFrame()

def main():
    # 获取命令行参数
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        test_stock_zh_ah_daily(ticker)
    else:
        # 测试多个常见股票代码
        test_stocks = [
            "600519",  # 贵州茅台 (上海)
            "000858",  # 五粮液 (深圳)
            "601857",  # 中国石油 (A+H股)
            "601398",  # 工商银行 (A+H股)
        ]

        for stock in test_stocks:
            test_stock_zh_ah_daily(stock)
            print("\n" + "="*50)

    print("\n测试完成！")

if __name__ == "__main__":
    main()