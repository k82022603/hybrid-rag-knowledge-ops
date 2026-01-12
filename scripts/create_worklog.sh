#!/bin/bash
# 작업 일지 생성 스크립트

# 날짜 설정
DATE=$(date +%Y-%m-%d)
YEAR=$(date +%Y)
MONTH=$(date +%m-%B)

# 경로 설정
WORKLOG_DIR="docs/work_logs/$YEAR/$MONTH"
WORKLOG_FILE="$WORKLOG_DIR/$DATE.md"

# 디렉토리 생성
mkdir -p "$WORKLOG_DIR"

# 이미 파일이 있으면 열기만
if [ -f "$WORKLOG_FILE" ]; then
    echo "📝 Opening existing worklog: $WORKLOG_FILE"
    code "$WORKLOG_FILE"  # VS Code로 열기
    exit 0
fi

# 템플릿 생성
cat > "$WORKLOG_FILE" << 'EOF'
# Work Log - DATE_PLACEHOLDER

## 📌 Today's Focus
- [ ] 주요 작업 1
- [ ] 주요 작업 2

## ✅ Completed Tasks
1. **작업명**
   - 상세 내용

## 💡 Key Decisions
-

## 🐛 Issues & Blockers
- (없음)

## 📚 Learnings
-

## 📅 Next Steps
- [ ] 내일 작업 1

## 📊 Time Spent
-

## 🔗 References
-
EOF

# 날짜 치환
sed -i "s/DATE_PLACEHOLDER/$DATE/g" "$WORKLOG_FILE"

echo "✅ Created worklog: $WORKLOG_FILE"
code "$WORKLOG_FILE"
