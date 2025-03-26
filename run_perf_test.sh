#!/bin/bash

# 打印开始信息
echo "=== 开始A股数据获取性能测试 ==="
echo "开始时间: $(date)"
echo

# 激活虚拟环境
echo "激活Python虚拟环境..."
source venv/bin/activate

# 运行性能测试
echo "开始运行性能测试..."
python -m src.tools.fast_api_demo

# 退出虚拟环境
deactivate

# 打印结束信息
echo
echo "=== 性能测试完成 ==="
echo "结束时间: $(date)"