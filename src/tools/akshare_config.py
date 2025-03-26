#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置akshare库的全局设置
"""

import akshare as ak
import requests
import inspect
import functools
import time
import random

def configure_akshare_timeout(timeout=30):
    """
    配置akshare的请求超时时间

    Args:
        timeout: 超时时间（秒），默认30秒
    """
    try:
        # 修改akshare内部使用的requests库的默认超时设置
        # akshare大部分网络请求都是通过requests库实现的
        if hasattr(ak, 'requests') and ak.requests:
            ak.requests.DEFAULT_TIMEOUT = timeout
            print(f"已将akshare的默认超时时间设置为 {timeout} 秒")
        else:
            # 如果无法直接访问ak.requests，则修改全局requests库的设置
            # 这可能会影响其他使用requests库的代码
            old_request = requests.Session.request

            def new_request(self, method, url, **kwargs):
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = timeout
                return old_request(self, method, url, **kwargs)

            requests.Session.request = new_request
            print(f"已将requests库的默认超时时间设置为 {timeout} 秒")

        # 直接修改requests库的get和post方法，而不是修改akshare的函数
        patch_requests_timeout(timeout)

        # 直接修补akshare中的关键函数
        patch_akshare_functions(timeout)

        return True
    except Exception as e:
        print(f"设置akshare超时时间时出错: {e}")
        return False

def patch_requests_timeout(timeout=30):
    """
    修改requests库的get和post方法，添加默认超时参数

    Args:
        timeout: 超时时间（秒），默认30秒
    """
    try:
        # 保存原始方法
        original_get = requests.get
        original_post = requests.post

        # 创建新的方法，添加默认超时参数
        @functools.wraps(original_get)
        def new_get(url, **kwargs):
            if 'timeout' not in kwargs:
                kwargs['timeout'] = timeout
            return original_get(url, **kwargs)

        @functools.wraps(original_post)
        def new_post(url, **kwargs):
            if 'timeout' not in kwargs:
                kwargs['timeout'] = timeout
            return original_post(url, **kwargs)

        # 替换requests库的方法
        requests.get = new_get
        requests.post = new_post

        print(f"成功修改requests库的get和post方法，添加了 {timeout} 秒的默认超时设置")
    except Exception as e:
        print(f"修改requests库方法时出错: {e}")

def patch_akshare_functions(timeout=30):
    """
    直接修补akshare中的关键函数，确保它们使用正确的超时设置

    Args:
        timeout: 超时时间（秒），默认30秒
    """
    try:
        # 修补stock_zh_a_hist函数
        if hasattr(ak, 'stock_zh_a_hist'):
            original_stock_zh_a_hist = ak.stock_zh_a_hist

            @functools.wraps(original_stock_zh_a_hist)
            def patched_stock_zh_a_hist(*args, **kwargs):
                # 添加重试逻辑
                max_retries = 3
                retry_delay = 2

                for retry in range(max_retries):
                    try:
                        return original_stock_zh_a_hist(*args, **kwargs)
                    except Exception as e:
                        if retry < max_retries - 1:
                            # 添加随机抖动避免同时重试
                            jitter = random.uniform(0.8, 1.2)
                            sleep_time = retry_delay * (2 ** retry) * jitter
                            print(f"获取历史数据失败: {e}, {sleep_time:.2f}秒后重试 ({retry+1}/{max_retries})...")
                            time.sleep(sleep_time)
                        else:
                            print(f"获取历史数据失败，已达到最大重试次数: {e}")
                            raise

            # 替换原始函数
            ak.stock_zh_a_hist = patched_stock_zh_a_hist
            print("成功修补 stock_zh_a_hist 函数，添加了重试逻辑")

        # 修补stock_zh_a_spot_em函数
        if hasattr(ak, 'stock_zh_a_spot_em'):
            original_stock_zh_a_spot_em = ak.stock_zh_a_spot_em

            @functools.wraps(original_stock_zh_a_spot_em)
            def patched_stock_zh_a_spot_em(*args, **kwargs):
                # 添加重试逻辑
                max_retries = 3
                retry_delay = 2

                for retry in range(max_retries):
                    try:
                        return original_stock_zh_a_spot_em(*args, **kwargs)
                    except Exception as e:
                        if retry < max_retries - 1:
                            # 添加随机抖动避免同时重试
                            jitter = random.uniform(0.8, 1.2)
                            sleep_time = retry_delay * (2 ** retry) * jitter
                            print(f"获取实时行情失败: {e}, {sleep_time:.2f}秒后重试 ({retry+1}/{max_retries})...")
                            time.sleep(sleep_time)
                        else:
                            print(f"获取实时行情失败，已达到最大重试次数: {e}")
                            raise

            # 替换原始函数
            ak.stock_zh_a_spot_em = patched_stock_zh_a_spot_em
            print("成功修补 stock_zh_a_spot_em 函数，添加了重试逻辑")

        print(f"成功修补akshare关键函数，添加了超时设置和重试逻辑")
    except Exception as e:
        print(f"修补akshare函数时出错: {e}")

# 默认在导入时配置30秒的超时时间
configure_akshare_timeout(30)