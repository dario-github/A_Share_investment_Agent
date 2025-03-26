#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 akshare 库获取股票数据的功能
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
import sys

def test_stock_info(ticker):
    """测试获取股票基本信息"""
    print(f"\n===== 测试获取股票 {ticker} 基本信息 =====")
    try:
        # 获取A股实时行情数据
        print(f"正在获取A股实时行情数据...")
        stock_df = ak.stock_zh_a_spot_em()
        print(f"成功获取A股实时行情数据，共 {len(stock_df)} 条记录")

        # 查找对应的股票
        stock_info = stock_df[stock_df['代码'] == ticker]
        if not stock_info.empty:
            print(f"股票代码: {ticker}")
            print(f"股票名称: {stock_info['名称'].values[0]}")
            print(f"当前价格: {stock_info['最新价'].values[0]}")
            print(f"涨跌幅: {stock_info['涨跌幅'].values[0]}%")
            print(f"成交量: {stock_info['成交量'].values[0]}")
            print(f"成交额: {stock_info['成交额'].values[0]}")
        else:
            print(f"未找到股票代码 {ticker} 的信息")
    except Exception as e:
        print(f"获取股票基本信息时出错: {str(e)}")

def test_stock_history(ticker, days=365):
    """测试获取股票历史行情数据"""
    print(f"\n===== 测试获取股票 {ticker} 历史行情数据 =====")

    # 计算日期范围
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)
    end_date = yesterday  # 使用昨天作为结束日期
    start_date = yesterday - timedelta(days=days)  # 默认获取一年的数据

    print(f"开始日期: {start_date.strftime('%Y-%m-%d')}")
    print(f"结束日期: {end_date.strftime('%Y-%m-%d')}")

    try:
        # 获取历史数据
        print(f"正在获取历史行情数据...")
        df = ak.stock_zh_a_hist(
            symbol=ticker,
            period="daily",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="qfq"
        )

        print(f"成功获取历史行情数据，共 {len(df)} 条记录")
        if not df.empty:
            print("\n最近5条数据:")
            print(df.head(5))
        return df
    except Exception as e:
        print(f"获取历史行情数据时出错: {str(e)}")

        # 尝试不指定日期范围获取数据
        print("\n尝试不指定日期范围获取数据...")
        try:
            df = ak.stock_zh_a_hist(
                symbol=ticker,
                period="daily",
                adjust="qfq"
            )
            print(f"成功获取历史行情数据，共 {len(df)} 条记录")
            if not df.empty:
                print("\n最近5条数据:")
                print(df.head(5))
            return df
        except Exception as e2:
            print(f"再次尝试获取历史数据失败: {str(e2)}")
            return pd.DataFrame()

def test_stock_financial(ticker):
    """测试获取股票财务数据"""
    print(f"\n===== 测试获取股票 {ticker} 财务数据 =====")

    try:
        # 获取资产负债表
        print("获取资产负债表数据...")
        balance_sheet = ak.stock_financial_report_sina(
            stock=ticker, symbol="资产负债表"
        )
        print(f"成功获取资产负债表数据，共 {len(balance_sheet)} 条记录")

        # 获取利润表
        print("\n获取利润表数据...")
        income_statement = ak.stock_financial_report_sina(
            stock=ticker, symbol="利润表"
        )
        print(f"成功获取利润表数据，共 {len(income_statement)} 条记录")

        # 获取现金流量表
        print("\n获取现金流量表数据...")
        cash_flow = ak.stock_financial_report_sina(
            stock=ticker, symbol="现金流量表"
        )
        print(f"成功获取现金流量表数据，共 {len(cash_flow)} 条记录")

    except Exception as e:
        print(f"获取财务数据时出错: {str(e)}")

def test_stock_news(ticker, count=5):
    """测试获取股票相关新闻"""
    print(f"\n===== 测试获取股票 {ticker} 相关新闻 =====")

    try:
        print(f"正在获取股票 {ticker} 的相关新闻...")
        news_df = ak.stock_news_em(symbol=ticker)
        print(f"成功获取新闻数据，共 {len(news_df)} 条记录")

        if not news_df.empty:
            print(f"\n最近 {min(count, len(news_df))} 条新闻:")
            for i, row in news_df.head(count).iterrows():
                print(f"标题: {row['新闻标题']}")
                print(f"时间: {row['发布时间']}")
                print(f"链接: {row['新闻链接']}")
                print("-" * 50)
    except Exception as e:
        print(f"获取新闻数据时出错: {str(e)}")

def main():
    # 获取命令行参数
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    else:
        ticker = "600519"  # 默认使用贵州茅台

    print(f"开始测试 akshare 库获取股票 {ticker} 的数据功能")

    # 测试获取股票基本信息
    test_stock_info(ticker)

    # 测试获取股票历史行情数据
    df = test_stock_history(ticker)

    # 测试获取股票财务数据
    test_stock_financial(ticker)

    # 测试获取股票相关新闻
    test_stock_news(ticker)

    print("\n测试完成！")

if __name__ == "__main__":
    main()