#!/bin/bash

# 打印开始信息
echo "=== 开始A股单只股票数据获取速度测试 ==="
echo "开始时间: $(date)"
echo

# 激活虚拟环境
echo "激活Python虚拟环境..."
source venv/bin/activate

# 运行速度测试
echo "开始运行速度测试..."
python test_single_stock_speed.py

# 退出虚拟环境
deactivate

# 打印结束信息
echo
echo "=== 速度测试完成 ==="
echo "结束时间: $(date)"