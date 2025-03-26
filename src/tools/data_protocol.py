import pandas as pd
import numpy as np


class PriceDataProtocol:
    """价格数据协议，定义标准化的数据结构和转换方法"""

    # 定义标准列名和允许的简写
    STANDARD_COLUMNS = {
        'close': ['c', '收盘', 'Close', 'CLOSE'],
        'open': ['o', '开盘', 'Open', 'OPEN'],
        'high': ['h', '最高', 'High', 'HIGH'],
        'low': ['l', '最低', 'Low', 'LOW'],
        'volume': ['v', '成交量', 'Volume', 'VOL', 'VOLUME'],
        'date': ['dt', '日期', 'Date', 'DATE'],
        'amount': ['成交额', 'amt', 'Amount', 'AMOUNT'],
        'change_percent': ['涨跌幅', 'chg', 'pct_change', 'change', 'Change']
    }

    # 必需的列
    REQUIRED_COLUMNS = ['close', 'open', 'high', 'low', 'volume']

    @staticmethod
    def standardize(data):
        """将任何格式的价格数据转换为标准格式"""
        try:
            # 检查输入是否为空
            if data is None or (isinstance(data, (list, dict)) and len(data) == 0):
                print("警告：价格数据为空，返回空DataFrame")
                return pd.DataFrame(columns=PriceDataProtocol.REQUIRED_COLUMNS)

            if isinstance(data, pd.DataFrame):
                df = data.copy()
            else:
                df = pd.DataFrame(data)

            # 输出检查信息
            print(f"数据标准化：接收到的数据结构: {type(data)}, 列名: {list(df.columns) if not df.empty else '[]'}")

            # 映射列名
            for std_col, aliases in PriceDataProtocol.STANDARD_COLUMNS.items():
                if std_col not in df.columns:
                    for alias in aliases:
                        if alias in df.columns:
                            df[std_col] = df[alias]
                            print(f"已将列 '{alias}' 映射到标准列名 '{std_col}'")
                            break

            # 验证所需列
            missing = [col for col in PriceDataProtocol.REQUIRED_COLUMNS if col not in df.columns]
            if missing:
                print(f"警告：缺少必要的价格数据列: {', '.join(missing)}")
                print(f"现有列: {list(df.columns)}")
                raise ValueError(f"缺少必要的列: {', '.join(missing)}")

            # 数据类型验证和转换
            for col in ['close', 'open', 'high', 'low']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                if df[col].isna().any():
                    raise ValueError(f"'{col}'列包含无效的数值数据")
                if (df[col] <= 0).any():
                    raise ValueError(f"'{col}'列包含零或负值，这对价格数据无效")

            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            if df['volume'].isna().any():
                raise ValueError("'volume'列包含无效的数值数据")
            if (df['volume'] < 0).any():
                raise ValueError("'volume'列包含负值，这对成交量数据无效")

            return df
        except Exception as e:
            print(f"数据标准化时出错: {str(e)}")
            raise ValueError(f"价格数据标准化失败: {str(e)}")

    @staticmethod
    def compress(df):
        """将标准DataFrame压缩为紧凑格式，同时保留标准列名"""
        if df is None or df.empty:
            print("警告：要压缩的数据为空，返回空列表")
            return []

        compact_data = []
        for _, row in df.iterrows():
            entry = {}

            # 使用标准列名
            for col in PriceDataProtocol.REQUIRED_COLUMNS:
                if col in row:
                    entry[col] = float(row[col])

            # 日期处理
            if 'date' in row:
                entry['date'] = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])

            # 处理其他有用的列
            if 'pct_change' in row and not pd.isna(row['pct_change']):
                entry['pct_change'] = float(row['pct_change'])

            compact_data.append(entry)

        return compact_data

    @staticmethod
    def create_meta_data(data):
        """创建带有元数据的价格数据结构"""
        return {
            "meta": {
                "columns": {
                    "close": "收盘价",
                    "open": "开盘价",
                    "high": "最高价",
                    "low": "最低价",
                    "volume": "成交量",
                    "date": "日期（YYYY-MM-DD格式）",
                    "pct_change": "涨跌幅（百分比）"
                },
                "format": "使用标准列名以确保数据处理一致性",
                "required_columns": PriceDataProtocol.REQUIRED_COLUMNS
            },
            "data": data
        }