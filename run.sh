#!/bin/bash

# 激活虚拟环境
source venv/bin/activate

# 设置默认参数
TICKER="300857"
SHOW_REASONING="--show-reasoning"
POSITION_RATIO="30.0"
NUM_OF_NEWS="5"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --ticker)
      TICKER="$2"
      shift 2
      ;;
    --no-reasoning)
      SHOW_REASONING=""
      shift
      ;;
    --position-ratio)
      POSITION_RATIO="$2"
      shift 2
      ;;
    --num-of-news)
      NUM_OF_NEWS="$2"
      shift 2
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

# 运行项目
echo "正在运行 A 股投资 Agent..."
echo "股票代码: $TICKER"
echo "仓位比例: $POSITION_RATIO%"
echo "新闻数量: $NUM_OF_NEWS"
echo "显示推理过程: $([ -n "$SHOW_REASONING" ] && echo "是" || echo "否")"
echo "-----------------------------------"

python src/main.py --ticker $TICKER $SHOW_REASONING --position-ratio $POSITION_RATIO --num-of-news $NUM_OF_NEWS

# 退出虚拟环境
deactivate