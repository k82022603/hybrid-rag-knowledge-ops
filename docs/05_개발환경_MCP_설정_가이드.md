# Claude Code MCP 설정 가이드

**Version**: 1.0
**Updated**: 2026-01-25
**Author**: 클로드

> **현행화 정보**
> - **최종 현행화**: 2026-02-20
> - **프로젝트 상태**: 종료 (2026-02-18)
> - **문서 상태**: 일부 outdated
> - **주요 변경사항**: 실제 `.claude/settings.json`은 jira, github, stitch MCP 서버를 직접 정의함. `.mcp.json`은 현재 미사용. Slack MCP는 `.mcp.json`이 아닌 별도 설정(`.claude/settings.local.json`)으로 활성화됨. stitch 모델이 `claude-opus-4-5-20251101` → 삭제됨.

---

## 1. 개요

Claude Code에서 MCP(Model Context Protocol) 서버 설정은 여러 위치에서 로드됩니다. 이 문서는 각 설정 파일의 역할과 차이점을 설명합니다.

---

## 2. 설정 파일 위치 및 역할

### 2.1 설정 파일 구조

```
~/.claude/
└── settings.json          # 전역 설정 (Global)

project-root/
├── .mcp.json              # 프로젝트 MCP 전용 (Deprecated)
└── .claude/
    ├── settings.json      # 프로젝트 설정 (Shared)
    └── settings.local.json # 프로젝트 로컬 설정 (Local)
```

### 2.2 각 파일의 역할

| 파일 | 범위 | Git 포함 | 용도 |
|------|------|----------|------|
| `~/.claude/settings.json` | 전역 | N/A | 모든 프로젝트에 적용되는 기본 설정 |
| `.claude/settings.json` | 프로젝트 | ✅ 권장 | 팀 공유용 MCP 설정 |
| `.claude/settings.local.json` | 프로젝트 로컬 | ❌ (.gitignore) | 개인 권한, 토큰, 로컬 설정 |
| `.mcp.json` | 프로젝트 | - | **Deprecated** (더 이상 권장하지 않음) |

---

## 3. 설정 파일 상세 비교

### 3.1 전역 설정 (`~/.claude/settings.json`)

**위치**: 사용자 홈 디렉토리
**범위**: 모든 Claude Code 세션에 적용
**용도**: 개인 API 토큰, 기본 MCP 서버

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**장점**:
- 한 번 설정하면 모든 프로젝트에서 사용
- 개인 토큰 중앙 관리

**단점**:
- 프로젝트별 커스터마이징 불가
- 팀원 간 공유 불가

---

### 3.2 프로젝트 설정 (`project/.claude/settings.json`)

**위치**: 프로젝트 `.claude/` 디렉토리
**범위**: 해당 프로젝트에만 적용
**Git**: 포함 권장 (팀 공유)

```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-jira"],
      "env": {
        "JIRA_HOST": "your-company.atlassian.net",
        "JIRA_EMAIL": "${JIRA_EMAIL}",
        "JIRA_API_TOKEN": "${JIRA_API_TOKEN}"
      }
    },
    "stitch": {
      "command": "npx",
      "args": ["-y", "@anthropic/stitch-mcp@latest"],
      "env": {
        "ANTHROPIC_MODEL": "claude-opus-4-5-20251101"
      }
    }

> ⚠️ **현행화 메모**: 실제 `.claude/settings.json`에서 stitch의 `ANTHROPIC_MODEL` 환경변수 설정은 제거됨. 또한 slack MCP 서버는 현재 `.claude/settings.json`에 포함되지 않고 별도 설정으로 활성화됨.
  }
}
```

**장점**:
- 프로젝트별 MCP 서버 정의
- Git으로 팀원 간 공유 가능
- 환경변수로 민감 정보 분리

**단점**:
- 프로젝트마다 설정 필요

---

### 3.3 프로젝트 로컬 설정 (`project/.claude/settings.local.json`)

**위치**: 프로젝트 `.claude/` 디렉토리
**범위**: 해당 프로젝트, 로컬 머신에만 적용
**Git**: 제외 권장 (.gitignore)

```json
{
  "permissions": {
    "allow": [
      "Bash(git commit:*)",
      "mcp__slack__slack_post_message",
      "mcp__jira__jira_update_issue"
    ]
  },
  "enabledMcpjsonServers": [
    "jira",
    "github",
    "slack"
  ],
  "hooks": {
    "SessionStart": [...],
    "SessionEnd": [...]
  }
}
```

**주요 설정**:
- `permissions.allow`: 자동 승인할 도구/명령어
- `enabledMcpjsonServers`: `.mcp.json`에서 활성화할 서버
- `hooks`: 세션 시작/종료 훅

**장점**:
- 개인 권한 설정
- 민감 토큰 로컬 저장
- Git에서 제외되어 안전

---

### 3.4 프로젝트 MCP 전용 (`.mcp.json`) - **Deprecated**

**위치**: 프로젝트 루트
**상태**: ⚠️ **더 이상 권장하지 않음**

```json
{
  "mcpServers": {
    "jira": { ... },
    "github": { ... },
    "slack": { ... }
  }
}
```

**Deprecated 이유**:
1. `.claude/settings.json`으로 통합됨
2. 중복 설정으로 혼란 야기
3. Claude Code 2.x에서 "invalid settings" 경고 발생

**마이그레이션 방법**:
```bash
# .mcp.json 내용을 .claude/settings.json으로 이동
# .mcp.json 삭제 또는 유지 (enabledMcpjsonServers로 활성화 가능)
```

---

## 4. 설정 로드 우선순위

Claude Code는 다음 순서로 설정을 로드합니다:

```
1. ~/.claude/settings.json (전역 기본값)
   ↓
2. project/.claude/settings.json (프로젝트 설정으로 덮어쓰기)
   ↓
3. project/.claude/settings.local.json (로컬 설정으로 덮어쓰기)
   ↓
4. project/.mcp.json (enabledMcpjsonServers가 있을 때만)
```

**동일한 MCP 서버가 여러 파일에 정의된 경우**: 나중에 로드된 설정이 우선

---

## 5. 권장 설정 방식

### 5.1 권장 구조

```
project-root/
└── .claude/
    ├── settings.json        # MCP 서버 정의 (Git 포함)
    └── settings.local.json  # 권한, 토큰 (Git 제외)
```

### 5.2 설정 분리 원칙

| 항목 | 위치 | Git |
|------|------|-----|
| MCP 서버 정의 (command, args) | `.claude/settings.json` | ✅ |
| API 토큰, 비밀번호 | 환경변수 (`${VAR}`) | ❌ |
| 개인 권한 (allow) | `.claude/settings.local.json` | ❌ |
| Hooks | `.claude/settings.local.json` | ❌ |

### 5.3 Best Practice

```json
// .claude/settings.json (Git 포함)
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-jira"],
      "env": {
        "JIRA_HOST": "company.atlassian.net",
        "JIRA_EMAIL": "${JIRA_EMAIL}",        // 환경변수 참조
        "JIRA_API_TOKEN": "${JIRA_API_TOKEN}" // 환경변수 참조
      }
    }
  }
}
```

```json
// .claude/settings.local.json (Git 제외)
{
  "permissions": {
    "allow": ["mcp__jira__*"]
  }
}
```

```bash
# .env 또는 shell 환경변수
export JIRA_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-secret-token"
```

---

## 6. 현재 프로젝트 설정 분석

### 6.1 현재 파일 상태

| 파일 | 존재 | 내용 |
|------|------|------|
| `~/.claude/settings.json` | ✅ | `{}` (비어있음) |
| `.claude/settings.json` | ✅ | jira, github, stitch |
| `.claude/settings.local.json` | ✅ | permissions, hooks, enabledMcpjsonServers |
| `.mcp.json` | ✅ | jira, github, slack |

> ⚠️ **현행화 메모**: 2026-02-20 기준 실제 `.claude/settings.json`에는 jira, github, stitch 3개 서버가 직접 정의되어 있음. slack MCP는 `.mcp.json` 또는 `.claude/settings.local.json`의 `enabledMcpjsonServers`로 활성화됨. `.mcp.json` 경고가 발생하지만 `enabledMcpjsonServers` 설정으로 여전히 동작 중.

### 6.2 현재 MCP 서버 출처

```
jira   → .mcp.json (enabledMcpjsonServers로 활성화)
github → .mcp.json (enabledMcpjsonServers로 활성화)
slack  → .mcp.json (enabledMcpjsonServers로 활성화)
stitch → .claude/settings.json (직접 정의, 현재 비활성)
```

> ⚠️ **현행화 메모**: 2026-02-20 기준 실제 설정은 jira/github/stitch가 `.claude/settings.json`에 직접 정의되어 있으며, slack은 별도 경로로 활성화됨. `.mcp.json`의 설정과 위 표가 일부 다를 수 있음.

### 6.3 경고 발생 이유

```
⚠ Found invalid settings files: .mcp.json. They will be ignored.
```

**이유**: Claude Code 2.x에서 `.mcp.json`은 deprecated 형식으로 경고가 발생하지만, `settings.local.json`의 `enabledMcpjsonServers` 설정으로 여전히 활성화됨.

---

## 7. 마이그레이션 권장사항

### 7.1 권장 조치

1. `.mcp.json` 내용을 `.claude/settings.json`으로 통합
2. `settings.local.json`에서 `enabledMcpjsonServers` 제거
3. `.mcp.json` 삭제

### 7.2 마이그레이션 후 구조

```json
// .claude/settings.json
{
  "mcpServers": {
    "jira": { /* .mcp.json에서 이동 */ },
    "github": { /* .mcp.json에서 이동 */ },
    "slack": { /* .mcp.json에서 이동 */ },
    "stitch": { /* 기존 유지 */ }
  }
}
```

---

## 8. 결론 및 권장 방식

### 가장 좋은 방식

| 순위 | 방식 | 이유 |
|------|------|------|
| **1위** | `.claude/settings.json` + 환경변수 | 표준, 팀 공유, 보안 |
| 2위 | 전역 `~/.claude/settings.json` | 개인 프로젝트에 적합 |
| 3위 | `.mcp.json` | ⚠️ Deprecated, 권장하지 않음 |

### 최종 권장

```
✅ .claude/settings.json   → MCP 서버 정의 (팀 공유)
✅ .claude/settings.local.json → 권한, 훅 (개인)
✅ 환경변수 (.env)          → API 토큰 (보안)
❌ .mcp.json               → 사용하지 않음
```

---

## 참고 자료

- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [MCP Server Configuration](https://modelcontextprotocol.io/)

---

## 현행화 이력

| 일자 | 작성자 | 내용 |
|------|--------|------|
| 2026-02-20 | Claude (doc-agent) | 프로젝트 종료 후 현행화 — 실제 `.claude/settings.json` 구성 반영 (jira/github/stitch 직접 정의, slack 별도 경로), stitch의 ANTHROPIC_MODEL 제거 사실 반영 |
