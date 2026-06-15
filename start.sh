#!/bin/bash
# Mac应用卸载工具启动脚本

cd "$(dirname "$0")"

# 激活虚拟环境
source venv/bin/activate

# 运行程序
python3 src/main.py