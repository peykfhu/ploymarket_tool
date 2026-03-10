
#!/bin/bash

# 一键推送服务器代码到 GitHub（ploymarket_tool）



cd ~/ploymarket_tool



echo "🚀 开始一键推送..."



# 先拉取最新代码（防止冲突）

git pull origin main --rebase || true



# 添加所有改动

git add -A



# 如果没有改动就退出

if git diff --cached --quiet; then

    echo "✅ 没有文件改动，无需推送"

    exit 0

fi



# 提交（自动带时间戳）

git commit -m "服务器更新 $(date '+%Y-%m-%d %H:%M:%S')"



# 推送

git push origin main



echo "🎉 推送完成！GitHub 已更新 → https://github.com/peykfhu/ploymarket_tool"

