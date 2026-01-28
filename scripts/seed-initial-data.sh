#!/bin/bash
# scripts/seed-initial-data.sh
# Bootstrap: 프로젝트 문서를 운영 데이터 폴더로 복사
#
# STORY-045: 초기 데이터 ETL 파이프라인 - 데이터 시딩
#
# 사용법: ./scripts/seed-initial-data.sh [--clean]
#   --clean: 기존 데이터를 삭제하고 새로 시딩

set -e

KNOWLEDGE_DATA="./knowledge_data/documents"
PROCESSED_DIR="./knowledge_data/processed"
EXPORTS_DIR="./knowledge_data/exports"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_ROOT"

echo "============================================================"
echo "  초기 데이터 시딩 스크립트 v2.0 (STORY-045)"
echo "============================================================"
echo ""

# 옵션 처리
CLEAN_MODE=false
if [ "$1" = "--clean" ]; then
    CLEAN_MODE=true
    echo "[INFO] Clean 모드: 기존 데이터를 삭제하고 새로 시딩합니다."
    echo ""
fi

# 0. Clean 모드 시 기존 데이터 삭제
if [ "$CLEAN_MODE" = true ] && [ -d "$KNOWLEDGE_DATA" ]; then
    echo "[STEP 0] 기존 데이터 삭제..."
    rm -rf "$KNOWLEDGE_DATA"
    rm -rf "$PROCESSED_DIR"
    echo "  - 기존 데이터 삭제 완료"
    echo ""
fi

# 1. 대상 폴더 확인/생성
echo "[STEP 1] 대상 폴더 준비..."
mkdir -p "$KNOWLEDGE_DATA/technical"
mkdir -p "$KNOWLEDGE_DATA/guides"
mkdir -p "$KNOWLEDGE_DATA/policies"
mkdir -p "$KNOWLEDGE_DATA/standards"
mkdir -p "$KNOWLEDGE_DATA/presentations"
mkdir -p "$PROCESSED_DIR"
mkdir -p "$EXPORTS_DIR"
echo "  - 폴더 구조 생성 완료"

# 2. 기술 문서 복사 -> technical/
echo ""
echo "[STEP 2] 기술 문서 복사 (technical/)..."
TECH_COUNT=0

if [ -d "knowledge_service/docs/01_planning" ]; then
    for f in knowledge_service/docs/01_planning/*.md; do
        [ -f "$f" ] && cp -v "$f" "$KNOWLEDGE_DATA/technical/" && TECH_COUNT=$((TECH_COUNT + 1))
    done
fi

if [ -d "knowledge_service/docs/02_design" ]; then
    # 최상위 md 파일만 복사 (하위 폴더 제외)
    find knowledge_service/docs/02_design -maxdepth 1 -name "*.md" -exec cp -v {} "$KNOWLEDGE_DATA/technical/" \;
    TECH_COUNT=$((TECH_COUNT + $(find knowledge_service/docs/02_design -maxdepth 1 -name "*.md" | wc -l)))
fi

if [ -d "knowledge_service/docs/03_implementation" ]; then
    for f in knowledge_service/docs/03_implementation/*.md; do
        [ -f "$f" ] && cp -v "$f" "$KNOWLEDGE_DATA/technical/" && TECH_COUNT=$((TECH_COUNT + 1))
    done
fi

if [ -d "knowledge_service/docs/04_testing" ]; then
    for f in knowledge_service/docs/04_testing/*.md; do
        [ -f "$f" ] && cp -v "$f" "$KNOWLEDGE_DATA/technical/" && TECH_COUNT=$((TECH_COUNT + 1))
    done
fi
echo "  - 기술 문서 ${TECH_COUNT}개 복사 완료"

# 3. 개발 가이드 복사 -> guides/
echo ""
echo "[STEP 3] 개발 가이드 복사 (guides/)..."
GUIDE_COUNT=0

if [ -d "knowledge_service/docs/05_development" ]; then
    for f in knowledge_service/docs/05_development/*.md; do
        [ -f "$f" ] && cp -v "$f" "$KNOWLEDGE_DATA/guides/" && GUIDE_COUNT=$((GUIDE_COUNT + 1))
    done
fi

if [ -d "knowledge_service/docs/07_maintenance" ]; then
    for f in knowledge_service/docs/07_maintenance/*.md; do
        [ -f "$f" ] && cp -v "$f" "$KNOWLEDGE_DATA/guides/" && GUIDE_COUNT=$((GUIDE_COUNT + 1))
    done
fi

if [ -d "docs/claude_code_virtual_team_alm_guide" ]; then
    for f in docs/claude_code_virtual_team_alm_guide/*.md; do
        [ -f "$f" ] && cp -v "$f" "$KNOWLEDGE_DATA/guides/" && GUIDE_COUNT=$((GUIDE_COUNT + 1))
    done
fi
echo "  - 가이드 ${GUIDE_COUNT}개 복사 완료"

# 4. 발표자료 복사 -> presentations/
echo ""
echo "[STEP 4] 발표자료 복사 (presentations/)..."
PRES_COUNT=0

if [ -d "docs/presentations" ]; then
    for f in docs/presentations/*.pptx; do
        [ -f "$f" ] && cp -v "$f" "$KNOWLEDGE_DATA/presentations/" && PRES_COUNT=$((PRES_COUNT + 1))
    done
fi
echo "  - 발표자료 ${PRES_COUNT}개 복사 완료"

# 5. 프로젝트 루트 문서 복사 -> technical/
echo ""
echo "[STEP 5] 프로젝트 루트 문서 복사..."
ROOT_COUNT=0
for f in CLAUDE.md README.md PLAN.md; do
    if [ -f "$f" ]; then
        cp -v "$f" "$KNOWLEDGE_DATA/technical/" && ROOT_COUNT=$((ROOT_COUNT + 1))
    fi
done
echo "  - 루트 문서 ${ROOT_COUNT}개 복사 완료"

# 6. 결과 요약
echo ""
echo "============================================================"
echo "  시딩 결과 요약"
echo "============================================================"
echo ""
echo "  technical/      : $(find "$KNOWLEDGE_DATA/technical" -type f -name "*.md" 2>/dev/null | wc -l) 파일"
echo "  guides/         : $(find "$KNOWLEDGE_DATA/guides" -type f -name "*.md" 2>/dev/null | wc -l) 파일"
echo "  policies/       : $(find "$KNOWLEDGE_DATA/policies" -type f -name "*.md" 2>/dev/null | wc -l) 파일"
echo "  standards/      : $(find "$KNOWLEDGE_DATA/standards" -type f -name "*.md" 2>/dev/null | wc -l) 파일"
echo "  presentations/  : $(find "$KNOWLEDGE_DATA/presentations" -type f -name "*.pptx" 2>/dev/null | wc -l) 파일"
echo ""

TOTAL_MD=$(find "$KNOWLEDGE_DATA" -type f -name "*.md" 2>/dev/null | wc -l)
TOTAL_PPTX=$(find "$KNOWLEDGE_DATA" -type f -name "*.pptx" 2>/dev/null | wc -l)
TOTAL=$((TOTAL_MD + TOTAL_PPTX))

echo "  Markdown 파일: ${TOTAL_MD}개"
echo "  PPTX 파일:     ${TOTAL_PPTX}개"
echo "  -------------------------"
echo "  총 파일 수:     ${TOTAL}개"
echo ""
echo "[DONE] 초기 데이터 시딩 완료!"
echo ""
echo "다음 단계: ./scripts/load-initial-data.sh"
