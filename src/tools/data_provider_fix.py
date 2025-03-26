import os
import pickle
import shutil
from datetime import datetime
import pandas as pd

# 定义缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# 缓存文件路径
STOCK_NAMES_CACHE_FILE = os.path.join(CACHE_DIR, "stock_names_cache.pkl")
HISTORICAL_DATA_CACHE_DIR = os.path.join(CACHE_DIR, "historical_data")
os.makedirs(HISTORICAL_DATA_CACHE_DIR, exist_ok=True)

def check_pickle_validity(cache_file):
    """
    检查pickle缓存文件是否有效

    Args:
        cache_file: 缓存文件路径

    Returns:
        bool: 文件是否有效
    """
    try:
        if not os.path.exists(cache_file):
            print(f"缓存文件 {cache_file} 不存在")
            return False

        with open(cache_file, 'rb') as f:
            data = pickle.load(f)

        # 对于股票名称缓存，检查是否为DataFrame且有必要的列
        if cache_file == STOCK_NAMES_CACHE_FILE:
            if not isinstance(data, pd.DataFrame):
                print(f"缓存文件 {cache_file} 内容不是DataFrame")
                return False

            if 'code' not in data.columns or 'name' not in data.columns:
                print(f"缓存文件 {cache_file} 中缺少必要列(code/name)")
                return False

            # 检查数据数量，A股通常有4000多只股票
            if len(data) < 1000:
                print(f"缓存文件 {cache_file} 包含的股票数量异常 ({len(data)})")
                return False

        return True
    except Exception as e:
        print(f"检查缓存文件 {cache_file} 时出错: {str(e)}")
        return False

def reset_cache():
    """
    重置所有缓存文件
    """
    try:
        # 创建备份目录
        backup_dir = os.path.join(CACHE_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(backup_dir, exist_ok=True)

        # 备份当前的缓存文件（如果存在）
        if os.path.exists(STOCK_NAMES_CACHE_FILE):
            shutil.copy2(STOCK_NAMES_CACHE_FILE, os.path.join(backup_dir, os.path.basename(STOCK_NAMES_CACHE_FILE)))

        # 备份历史数据缓存目录
        if os.path.exists(HISTORICAL_DATA_CACHE_DIR) and len(os.listdir(HISTORICAL_DATA_CACHE_DIR)) > 0:
            for file in os.listdir(HISTORICAL_DATA_CACHE_DIR):
                file_path = os.path.join(HISTORICAL_DATA_CACHE_DIR, file)
                if os.path.isfile(file_path):
                    shutil.copy2(file_path, os.path.join(backup_dir, file))

        # 删除缓存文件
        if os.path.exists(STOCK_NAMES_CACHE_FILE):
            os.remove(STOCK_NAMES_CACHE_FILE)

        # 清空历史数据缓存目录
        for file in os.listdir(HISTORICAL_DATA_CACHE_DIR):
            file_path = os.path.join(HISTORICAL_DATA_CACHE_DIR, file)
            if os.path.isfile(file_path):
                os.remove(file_path)

        print(f"已重置所有缓存文件，原始文件已备份到 {backup_dir}")
        return True
    except Exception as e:
        print(f"重置缓存时出错: {str(e)}")
        return False

def repair_stock_names_cache():
    """
    修复股票名称缓存
    """
    try:
        # 检查缓存文件
        if os.path.exists(STOCK_NAMES_CACHE_FILE):
            is_valid = check_pickle_validity(STOCK_NAMES_CACHE_FILE)
            if is_valid:
                print(f"股票名称缓存文件有效，无需修复")
                return True
            else:
                print(f"检测到无效的股票名称缓存文件，将进行删除")
                os.remove(STOCK_NAMES_CACHE_FILE)

        # 重新创建股票名称缓存
        print("正在重新获取股票名称数据...")
        try:
            import akshare as ak
            stock_info_df = ak.stock_info_a_code_name()

            # 检查数据有效性
            if stock_info_df is None or len(stock_info_df) < 1000:
                raise ValueError(f"获取的股票数据不完整，仅有 {0 if stock_info_df is None else len(stock_info_df)} 条记录")

            # 保存到本地文件
            with open(STOCK_NAMES_CACHE_FILE, 'wb') as f:
                pickle.dump(stock_info_df, f)

            print(f"成功重新获取并缓存股票数据，共 {len(stock_info_df)} 条记录")
            return True
        except Exception as inner_e:
            print(f"重新获取股票数据时出错: {str(inner_e)}")

            # 尝试使用备用方法构建基本的股票名称数据
            try:
                print("尝试使用备用方法构建基础股票名称数据...")

                # 创建一个基本的股票名称DataFrame
                codes = []
                names = []

                # 添加沪市主板股票代码 (600000-603999)
                for code in range(600000, 604000):
                    codes.append(str(code))
                    names.append(f"未知股票{code}")

                # 添加沪市科创板股票代码 (688000-689999)
                for code in range(688000, 690000):
                    codes.append(str(code))
                    names.append(f"未知股票{code}")

                # 添加深市主板股票代码 (000001-001999)
                for code in range(1, 2000):
                    codes.append(f"{code:06d}")
                    names.append(f"未知股票{code:06d}")

                # 添加深市创业板股票代码 (300000-301999)
                for code in range(300000, 302000):
                    codes.append(str(code))
                    names.append(f"未知股票{code}")

                # 创建DataFrame
                basic_df = pd.DataFrame({
                    'code': codes,
                    'name': names
                })

                # 保存到本地文件
                with open(STOCK_NAMES_CACHE_FILE, 'wb') as f:
                    pickle.dump(basic_df, f)

                print(f"成功创建基础股票名称数据，共 {len(basic_df)} 条记录（无实际名称）")
                print("注意：此数据仅包含代码，无实际股票名称，仅作为临时解决方案")
                return True
            except Exception as backup_e:
                print(f"创建基础股票名称数据时出错: {str(backup_e)}")
                return False
    except Exception as e:
        print(f"修复股票名称缓存时出错: {str(e)}")
        return False

def check_all_caches():
    """
    检查所有缓存文件的有效性
    """
    issues = []

    # 检查股票名称缓存
    if os.path.exists(STOCK_NAMES_CACHE_FILE):
        if not check_pickle_validity(STOCK_NAMES_CACHE_FILE):
            issues.append(f"股票名称缓存文件无效: {STOCK_NAMES_CACHE_FILE}")
    else:
        issues.append(f"股票名称缓存文件不存在: {STOCK_NAMES_CACHE_FILE}")

    # 检查历史数据缓存
    if os.path.exists(HISTORICAL_DATA_CACHE_DIR):
        for file in os.listdir(HISTORICAL_DATA_CACHE_DIR):
            file_path = os.path.join(HISTORICAL_DATA_CACHE_DIR, file)
            if os.path.isfile(file_path) and file.endswith('.pkl'):
                if not check_pickle_validity(file_path):
                    issues.append(f"历史数据缓存文件无效: {file_path}")
    else:
        issues.append(f"历史数据缓存目录不存在: {HISTORICAL_DATA_CACHE_DIR}")

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }

if __name__ == "__main__":
    print("开始检查缓存文件...")
    check_result = check_all_caches()

    if check_result["valid"]:
        print("所有缓存文件检查通过")
    else:
        print(f"发现 {len(check_result['issues'])} 个问题:")
        for issue in check_result["issues"]:
            print(f" - {issue}")

        print("\n是否需要修复问题? (y/n)")
        choice = input().lower()

        if choice == 'y' or choice == 'yes':
            print("\n正在修复股票名称缓存...")
            if repair_stock_names_cache():
                print("股票名称缓存修复成功")
            else:
                print("股票名称缓存修复失败")

            print("\n是否需要重置所有缓存? (y/n)")
            reset_choice = input().lower()

            if reset_choice == 'y' or reset_choice == 'yes':
                if reset_cache():
                    print("缓存重置成功")
                else:
                    print("缓存重置失败")
        else:
            print("已取消修复操作")