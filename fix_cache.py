#!/usr/bin/env python3
import os
import sys
import argparse
from src.tools.data_provider_fix import check_all_caches, repair_stock_names_cache, reset_cache, check_pickle_validity

def main():
    """
    缓存检查和修复工具
    """
    parser = argparse.ArgumentParser(description='A股投资系统缓存检查和修复工具')
    parser.add_argument('--check', action='store_true', help='检查所有缓存文件')
    parser.add_argument('--repair', action='store_true', help='修复股票名称缓存')
    parser.add_argument('--reset', action='store_true', help='重置所有缓存文件（会先备份）')
    parser.add_argument('--force', action='store_true', help='强制执行，不询问确认')

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    if args.check:
        print("\n=========== 缓存文件检查 ===========")
        check_result = check_all_caches()

        if check_result["valid"]:
            print("✅ 所有缓存文件检查通过")
        else:
            print(f"❌ 发现 {len(check_result['issues'])} 个问题:")
            for issue in check_result["issues"]:
                print(f" - {issue}")

            if not args.repair and not args.reset and not args.force:
                print("\n是否需要修复问题? (y/n)")
                choice = input().lower()
                if choice == 'y' or choice == 'yes':
                    args.repair = True

    if args.repair:
        print("\n=========== 修复股票名称缓存 ===========")
        if repair_stock_names_cache():
            print("✅ 股票名称缓存修复成功")
        else:
            print("❌ 股票名称缓存修复失败")

    if args.reset:
        print("\n=========== 重置所有缓存 ===========")
        if not args.force:
            print("⚠️ 警告：此操作将删除所有缓存文件，但会先创建备份")
            print("是否确定要继续? (y/n)")
            choice = input().lower()
            if choice != 'y' and choice != 'yes':
                print("已取消重置操作")
                return

        if reset_cache():
            print("✅ 所有缓存已重置")
        else:
            print("❌ 缓存重置失败")

    if args.check and args.repair:
        print("\n=========== 再次检查缓存 ===========")
        check_result = check_all_caches()

        if check_result["valid"]:
            print("✅ 所有缓存文件检查通过")
        else:
            print(f"❌ 仍然存在 {len(check_result['issues'])} 个问题:")
            for issue in check_result["issues"]:
                print(f" - {issue}")

    print("\n完成！")

if __name__ == "__main__":
    main()