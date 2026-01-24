# Mermaid Diagrams Skill

Mermaid를 사용한 다이어그램 작성 표준을 제공합니다.

## 설치

```bash
# 프로젝트에 이미 포함됨
ls .claude/skills/mermaid-diagrams/
```

## 대상 에이전트

- 전체 에이전트 (문서 작성 시)
- `code-documenter` (Documenter) - 주 사용자
- `devops-engineer` (DevOps) - 인프라 다이어그램

## 주요 다이어그램 유형

| 유형 | 용도 |
|------|------|
| `flowchart` | 시스템 아키텍처, 플로우 |
| `sequenceDiagram` | API 호출, 인증 플로우 |
| `stateDiagram` | 상태 변화 |
| `classDiagram` | 도메인 모델 |
| `erDiagram` | DB 스키마 |
| `gantt` | 일정 계획 |

## 빠른 참조

```mermaid
flowchart LR
    A["시작"] --> B["처리"] --> C["끝"]
```

## 버전

- 1.0.0 (2026-01-24)
