#!/bin/bash

# 激活虚拟环境
source venv/bin/activate

# 安装UI依赖
# pip install -r requirements-ui.txt

# 启动Streamlit应用
echo "正在启动智能投资决策系统前端..."
streamlit run app.py --server.port=8701

# 退出虚拟环境
deactivate