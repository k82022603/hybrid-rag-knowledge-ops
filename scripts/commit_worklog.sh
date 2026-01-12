#!/bin/bash
# 작업 일지 커밋 스크립트

DATE=$(date +%Y-%m-%d)
MESSAGE="[DOCS] Work log for $DATE"

echo "📝 Committing work logs..."

# 작업 일지 추가
git add docs/work_logs/

# 변경사항 확인
if [ -z "$(git status --porcelain docs/work_logs/)" ]; then
    echo "⚠️  No changes to commit in work logs"
    exit 0
fi

# 커밋
git commit -m "$MESSAGE"

if [ $? -eq 0 ]; then
    echo "✅ Successfully committed work logs"
    echo "   Message: $MESSAGE"
else
    echo "❌ Failed to commit"
    exit 1
fi
