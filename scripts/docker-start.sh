#!/bin/bash
# =============================================================================
# Docker 환경 시작 스크립트
# =============================================================================
#
# 사용법:
#   ./scripts/docker-start.sh [command]
#
# Commands:
#   up      - 컨테이너 시작 (기본값)
#   down    - 컨테이너 중지
#   restart - 컨테이너 재시작
#   status  - 상태 확인
#   logs    - 로그 확인
#
# 환경 자동 감지:
#   - WSL2: docker-compose.wsl2.yml 자동 적용
#   - Linux: 기본 docker-compose.yml 사용
#   - macOS: 기본 docker-compose.yml 사용
#
# Created: 2026-01-25
# Related: INC-2026-01-25-001 (WSL2 권한 문제 재발 방지)
# =============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 스크립트 디렉토리 기준 프로젝트 루트 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/infrastructure/docker"

# =============================================================================
# 함수 정의
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 환경 감지
detect_environment() {
    if grep -qEi "(Microsoft|WSL)" /proc/version 2>/dev/null; then
        echo "wsl2"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Docker Compose 명령어 구성
get_compose_command() {
    local env=$(detect_environment)
    local compose_cmd="docker compose -f docker-compose.yml"

    case $env in
        wsl2)
            if [[ -f "$DOCKER_DIR/docker-compose.wsl2.yml" ]]; then
                compose_cmd="$compose_cmd -f docker-compose.wsl2.yml"
                log_info "WSL2 환경 감지 - WSL2 프로파일 적용"
            else
                log_warn "WSL2 환경이지만 docker-compose.wsl2.yml 파일이 없습니다"
            fi
            ;;
        macos)
            log_info "macOS 환경 감지 - 기본 설정 사용"
            ;;
        linux)
            log_info "Linux 환경 감지 - 기본 설정 사용"
            ;;
        *)
            log_warn "알 수 없는 환경 - 기본 설정 사용"
            ;;
    esac

    echo "$compose_cmd"
}

# 사전 검사
preflight_check() {
    log_info "사전 검사 수행 중..."

    # Docker 실행 확인
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker가 실행되고 있지 않습니다"
        exit 1
    fi
    log_success "Docker 실행 중"

    # docker-compose.yml 존재 확인
    if [[ ! -f "$DOCKER_DIR/docker-compose.yml" ]]; then
        log_error "docker-compose.yml 파일을 찾을 수 없습니다: $DOCKER_DIR"
        exit 1
    fi
    log_success "docker-compose.yml 확인"

    # .env 파일 확인
    if [[ ! -f "$DOCKER_DIR/.env" ]]; then
        if [[ -f "$DOCKER_DIR/.env.example" ]]; then
            log_warn ".env 파일이 없습니다. .env.example을 복사합니다"
            cp "$DOCKER_DIR/.env.example" "$DOCKER_DIR/.env"
            log_info ".env 파일을 확인하고 필요한 값을 설정하세요"
        else
            log_error ".env 파일이 없습니다"
            exit 1
        fi
    fi
    log_success ".env 파일 확인"

    # WSL2 환경에서 경로 확인
    local env=$(detect_environment)
    if [[ "$env" == "wsl2" ]]; then
        if [[ "$DOCKER_DIR" == /mnt/* ]]; then
            log_warn "Windows 파일시스템 경로 사용 중 (/mnt/...)"
            log_warn "성능 향상을 위해 WSL 내부 경로 사용을 권장합니다"
        fi
    fi

    echo ""
}

# 컨테이너 시작
cmd_up() {
    preflight_check

    cd "$DOCKER_DIR"
    local compose_cmd=$(get_compose_command)

    log_info "컨테이너 시작 중..."
    $compose_cmd up -d

    echo ""
    log_info "컨테이너 상태 확인 중..."
    sleep 5
    $compose_cmd ps --format "table {{.Name}}\t{{.Status}}"

    echo ""
    log_success "컨테이너 시작 완료"
    log_info "전체 상태 확인: $0 status"
    log_info "로그 확인: $0 logs [service]"
}

# 컨테이너 중지
cmd_down() {
    cd "$DOCKER_DIR"
    local compose_cmd=$(get_compose_command)

    log_info "컨테이너 중지 중..."
    $compose_cmd down

    log_success "컨테이너 중지 완료"
}

# 컨테이너 재시작
cmd_restart() {
    cmd_down
    echo ""
    cmd_up
}

# 상태 확인
cmd_status() {
    cd "$DOCKER_DIR"
    local compose_cmd=$(get_compose_command)

    echo "=== 환경 정보 ==="
    echo "환경: $(detect_environment)"
    echo "Docker 디렉토리: $DOCKER_DIR"
    echo ""

    echo "=== 컨테이너 상태 ==="
    $compose_cmd ps --format "table {{.Name}}\t{{.Status}}"

    echo ""
    echo "=== 리소스 사용량 ==="
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -20
}

# 로그 확인
cmd_logs() {
    cd "$DOCKER_DIR"
    local compose_cmd=$(get_compose_command)
    local service=${1:-}

    if [[ -n "$service" ]]; then
        $compose_cmd logs -f --tail=100 "$service"
    else
        $compose_cmd logs -f --tail=50
    fi
}

# 도움말
cmd_help() {
    echo "Docker 환경 시작 스크립트"
    echo ""
    echo "사용법: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  up        컨테이너 시작 (기본값)"
    echo "  down      컨테이너 중지"
    echo "  restart   컨테이너 재시작"
    echo "  status    상태 확인"
    echo "  logs      로그 확인 (logs [service])"
    echo "  help      도움말"
    echo ""
    echo "환경 자동 감지:"
    echo "  - WSL2: docker-compose.wsl2.yml 자동 적용"
    echo "  - Linux/macOS: 기본 docker-compose.yml 사용"
    echo ""
    echo "예시:"
    echo "  $0              # 컨테이너 시작"
    echo "  $0 up           # 컨테이너 시작"
    echo "  $0 down         # 컨테이너 중지"
    echo "  $0 logs backend # backend 로그 확인"
}

# =============================================================================
# 메인
# =============================================================================

COMMAND=${1:-up}

case $COMMAND in
    up)
        cmd_up
        ;;
    down)
        cmd_down
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "$2"
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        log_error "알 수 없는 명령어: $COMMAND"
        cmd_help
        exit 1
        ;;
esac
