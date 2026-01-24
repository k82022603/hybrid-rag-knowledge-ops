# Layered Architecture Enforcer Skill

계층형 아키텍처 원칙을 강제하여 AI 코드 생성 시 안티패턴을 방지합니다.

## 설치

```bash
# 프로젝트에 이미 포함됨
ls .claude/skills/layered-architecture-enforcer/
```

## 대상 에이전트

- `backend-developer` (Backend)
- `rag-engineer` (RAG)

## 방지하는 안티패턴

1. **Controller → Repository 직접 호출**
2. **Service에 RequestDTO 전달**
3. **Controller에 비즈니스 로직**

## 참고 문서

- [AI 시대에 더욱 중요해진 아키텍처 원칙](../../docs/technical_assessment/SubAgent%20%26%20AgentSkills/)

## 버전

- 1.0.0 (2026-01-24)
