#!/bin/bash

# 微信读书同步脚本
# 使用方法: ./run.sh 或 ./run.sh --all

cd "$(dirname "$0")"

# 激活虚拟环境
source venv/bin/activate

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "❌ 错误: .env 文件不存在"
    echo "请先创建 .env 文件并配置 WEREAD_COOKIE 和 NOTION_TOKEN"
    exit 1
fi

# 检查 NOTION_TOKEN
source .env
if [ -z "$NOTION_TOKEN" ] || [ "$NOTION_TOKEN" = "your_notion_token_here" ]; then
    echo "⚠️  警告: NOTION_TOKEN 未配置"
    echo "请编辑 .env 文件，设置 NOTION_TOKEN"
    echo ""
    echo "获取 Token 的步骤："
    echo "1. 访问 https://www.notion.so/my-integrations"
    echo "2. 创建新的 Integration"
    echo "3. 复制 Internal Integration Token"
    echo "4. 在 .env 文件中设置 NOTION_TOKEN=secret_你的token"
    echo ""
    read -p "是否继续运行？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 运行同步脚本
echo "🚀 开始同步..."
python scripts/weread.py "$@"

