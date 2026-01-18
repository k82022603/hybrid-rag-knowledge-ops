#!/bin/bash
# scripts/seed-initial-data.sh
# Bootstrap: 프로젝트 문서를 운영 데이터 폴더로 복사
#
# 사용법: ./scripts/seed-initial-data.sh

set -e

KNOWLEDGE_DATA="./knowledge_data/documents"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_ROOT"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         초기 데이터 시딩 스크립트 v1.0                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 1. 대상 폴더 확인/생성
echo "1️⃣ 대상 폴더 준비..."
mkdir -p "$KNOWLEDGE_DATA/technical"
mkdir -p "$KNOWLEDGE_DATA/guides"
mkdir -p "$KNOWLEDGE_DATA/policies"
mkdir -p "$KNOWLEDGE_DATA/standards"
mkdir -p "$KNOWLEDGE_DATA/presentations"
echo "   ✅ 폴더 구조 생성 완료"

# 2. 기술 문서 복사 → technical/
echo ""
echo "2️⃣ 기술 문서 복사 (technical/)..."
if [ -d "knowledge_service/docs/01_planning" ]; then
    cp -v knowledge_service/docs/01_planning/*.md "$KNOWLEDGE_DATA/technical/" 2>/dev/null || true
fi
if [ -d "knowledge_service/docs/02_design" ]; then
    # 최상위 md 파일만 복사 (하위 폴더 제외)
    find knowledge_service/docs/02_design -maxdepth 1 -name "*.md" -exec cp -v {} "$KNOWLEDGE_DATA/technical/" \;
fi
echo "   ✅ 기술 문서 복사 완료"

# 3. ALM 가이드 복사 → guides/
echo ""
echo "3️⃣ ALM 가이드 복사 (guides/)..."
if [ -d "docs/claude_code_virtual_team_alm_guide" ]; then
    cp -v docs/claude_code_virtual_team_alm_guide/*.md "$KNOWLEDGE_DATA/guides/" 2>/dev/null || true
fi
echo "   ✅ 가이드 문서 복사 완료"

# 4. 발표자료 복사 → presentations/
echo ""
echo "4️⃣ 발표자료 복사 (presentations/)..."
if [ -d "docs/presentations" ]; then
    cp -v docs/presentations/*.pptx "$KNOWLEDGE_DATA/presentations/" 2>/dev/null || true
fi
echo "   ✅ 발표자료 복사 완료"

# 5. 결과 요약
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 시딩 결과:"
echo ""
echo "   technical/      : $(find "$KNOWLEDGE_DATA/technical" -name "*.md" 2>/dev/null | wc -l) 파일"
echo "   guides/         : $(find "$KNOWLEDGE_DATA/guides" -name "*.md" 2>/dev/null | wc -l) 파일"
echo "   policies/       : $(find "$KNOWLEDGE_DATA/policies" -name "*.md" 2>/dev/null | wc -l) 파일"
echo "   standards/      : $(find "$KNOWLEDGE_DATA/standards" -name "*.md" 2>/dev/null | wc -l) 파일"
echo "   presentations/  : $(find "$KNOWLEDGE_DATA/presentations" -name "*.pptx" 2>/dev/null | wc -l) 파일"
echo ""
TOTAL=$(find "$KNOWLEDGE_DATA" -type f \( -name "*.md" -o -name "*.pptx" \) 2>/dev/null | wc -l)
echo "   총 파일 수: $TOTAL"
echo ""
echo "✅ 초기 데이터 시딩 완료!"
echo ""
echo "다음 단계: ./scripts/load-initial-data.sh"
