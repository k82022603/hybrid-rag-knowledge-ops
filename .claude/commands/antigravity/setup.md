---
description: Antigravity Claude Proxy 초기 설정 (개인 실험용)
model: claude-sonnet-4-1
---

Antigravity Claude Proxy 초기 설정을 도와드립니다.

> **중요**: 이 스킬은 **개인 실험/학습 용도**로만 사용하세요.
> 기업/팀 환경에서는 권장하지 않습니다. (ToS 위반 가능성)

## Setup Process

### Step 1: 사전 요구사항 확인

```bash
# Node.js 버전 확인 (18+ 필요)
node --version

# Claude Code 확인
claude --version
```

### Step 2: Antigravity Proxy 설치 및 시작

```bash
# npx로 바로 실행 (권장)
npx antigravity-claude-proxy@latest start

# 또는 전역 설치
npm install -g antigravity-claude-proxy@latest
antigravity-claude-proxy start
```

### Step 3: 계정 연결

**웹 대시보드 (권장)**:
1. 브라우저에서 `http://localhost:8080` 접속
2. **Accounts** 탭 클릭
3. **Add Account** 버튼 클릭
4. Google 계정으로 로그인
5. 권한 승인

**CLI 방식**:
```bash
antigravity-claude-proxy accounts add
# 또는 브라우저 없이
antigravity-claude-proxy accounts add --no-browser
```

### Step 4: 환경 변수 설정

**macOS/Linux (zsh)**:
```bash
# ~/.zshrc 또는 ~/.bashrc에 추가
export ANTHROPIC_BASE_URL="http://localhost:8080"
export ANTHROPIC_AUTH_TOKEN="test"

# 적용
source ~/.zshrc
```

**Windows PowerShell**:
```powershell
$env:ANTHROPIC_BASE_URL = "http://localhost:8080"
$env:ANTHROPIC_AUTH_TOKEN = "test"
```

### Step 5: Claude Code 설정

`~/.claude/settings.json` 파일 수정:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:8080",
    "ANTHROPIC_AUTH_TOKEN": "test",
    "ANTHROPIC_MODEL": "claude-opus-4-5-thinking",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gemini-2.5-flash-lite[1m]",
    "ENABLE_EXPERIMENTAL_MCP_CLI": "true"
  }
}
```

## 사용 가능한 모델

| 모델 ID | 설명 | 추천 용도 |
|---------|------|----------|
| `claude-opus-4-5-thinking` | Claude Opus 4.5 (사고 확장) | 복잡한 작업 |
| `claude-sonnet-4-5-thinking` | Claude Sonnet 4.5 | 일반 작업 |
| `gemini-3-pro-high` | Gemini 3 Pro | 고성능 |
| `gemini-3-flash` | Gemini 3 Flash | 빠른 응답 |
| `gemini-2.5-flash-lite[1m]` | Gemini 2.5 Flash Lite | Haiku 대체 |

## 모니터링

```bash
# 계정 상태 확인
curl "http://localhost:8080/account-limits?format=table"

# 웹 대시보드
open http://localhost:8080  # macOS
```

## 원래 설정 복원

Antigravity 사용 후 공식 Anthropic API로 돌아가려면:

```bash
# 환경 변수 제거
unset ANTHROPIC_BASE_URL
unset ANTHROPIC_AUTH_TOKEN

# 또는 ~/.claude/settings.json에서 env 섹션 제거/주석 처리
```

## 관련 문서

- [Antigravity 설정 가이드 (상세)](../../docs/08_Antigravity_설정_가이드.md)
- [검토 결과 문서](../../docs/technical_assessment/Guides/검토결과_05_Antigravity_Claude_Proxy.md)

$ARGUMENTS
