#!/bin/bash
# ==============================================================================
# standup_all.sh - 9개 에이전트 스탠드업 인사말 일괄 전송
# ==============================================================================
# 사용법:
#   ./scripts/standup_all.sh
#
# 설명:
#   모든 AI 에이전트가 #proj-hrkp-standup 채널에 인사말을 보냅니다.
#   한 번의 실행으로 9개 메시지가 순차적으로 전송됩니다.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEND_SLACK="$SCRIPT_DIR/send_slack.sh"
CHANNEL="proj-hrkp-standup"

echo "🌅 스탠드업 미팅 시작 - 9개 에이전트 인사말 전송"
echo "================================================"

# 1. PM
$SEND_SLACK "$CHANNEL" "PM" "좋은 아침입니다! 오늘도 함께 성장하는 하루가 되길 바랍니다.
• 어제: Sprint 01 백로그 정리, 에이전트 설정 업데이트
• 오늘: Sprint 02 준비, 에이전트 작업 조율
• 블로커: 없음
• 한마디: 인프라 기반이 탄탄해졌습니다. 이제 핵심 기능 구현 시작!"

# 2. Backend
$SEND_SLACK "$CHANNEL" "Backend" "안녕하세요! 오늘도 견고한 API를 만들어봅시다.
• 어제: 프로젝트 스켈레톤 구성, 의존성 설정
• 오늘: Knowledge Service 엔드포인트 설계
• 블로커: 없음
• 한마디: WebFlux 비동기 처리로 응답시간 최적화 계획 중입니다!"

# 3. Frontend
$SEND_SLACK "$CHANNEL" "Frontend" "좋은 아침이에요! 오늘도 사용자를 위한 UI 만들어봐요!
• 어제: React 프로젝트 구조 설정, MUI 테마 구성
• 오늘: 검색 컴포넌트 설계, SSE 스트리밍 준비
• 블로커: 없음
• 한마디: 사용자가 3초 안에 원하는 걸 찾을 수 있게! UX가 곧 경쟁력입니다."

# 4. MLRag
$SEND_SLACK "$CHANNEL" "MLRag" "안녕하세요! 오늘도 지식의 연결고리를 찾아봅니다.
• 어제: AI Service 스켈레톤 구성, LangGraph 설정
• 오늘: VIP 파이프라인 설계, Hybrid Retriever 구조 잡기
• 블로커: 없음
• 한마디: Gleaning으로 Entity Recall +33% 기대됩니다. 품질이 생명!"

# 5. Data
$SEND_SLACK "$CHANNEL" "Data" "반갑습니다! 데이터가 흐르면 지식이 됩니다.
• 어제: PostgreSQL/Neo4j/ES 스키마 초기화 스크립트
• 오늘: ETL 파이프라인 구조 설계, Docling 연동 준비
• 블로커: 없음
• 한마디: 고아 노드 1% 미만 유지가 목표! 그래프 연결성이 핵심입니다."

# 6. Infra
$SEND_SLACK "$CHANNEL" "Infra" "안녕하세요! 안정적인 인프라가 서비스의 기반입니다.
• 어제: Docker Compose 18개 컨테이너 구성 완료
• 오늘: Health check 개선, 볼륨 백업 스크립트 작성
• 블로커: 없음
• 한마디: 12/18 컨테이너 healthy! 나머지도 곧 정상화됩니다."

# 7. DevOps
$SEND_SLACK "$CHANNEL" "DevOps" "안녕하세요! 자동화가 개발자를 자유롭게 합니다.
• 어제: Observability 스택 구성 (Prometheus/Grafana/Loki)
• 오늘: GitHub Actions CI/CD 파이프라인 설계
• 블로커: 없음
• 한마디: 빌드-테스트-배포 자동화로 생산성 극대화 목표!"

# 8. QA
$SEND_SLACK "$CHANNEL" "QA" "안녕하세요! 버그 없는 코드는 테스트된 코드입니다.
• 어제: 인프라 E2E 테스트 75개 작성, 40% 통과
• 오늘: 테스트 커버리지 개선, RAGAS 평가 프레임워크 준비
• 블로커: 없음
• 한마디: 커버리지 80% 목표! 품질 게이트를 통과해야 배포됩니다."

# 9. TechLead
$SEND_SLACK "$CHANNEL" "TechLead" "반갑습니다. 좋은 코드는 좋은 설계에서 시작됩니다.
• 어제: VIP 아키텍처 검토, 설계 문서 리뷰
• 오늘: Sprint 02 API 설계 리뷰, 코드 표준 점검
• 블로커: 없음
• 한마디: DRY보다 중요한 건 명확한 의도입니다. 읽기 좋은 코드 작성합시다!"

echo "================================================"
echo "✅ 스탠드업 완료! 9개 에이전트 인사말 전송됨"
