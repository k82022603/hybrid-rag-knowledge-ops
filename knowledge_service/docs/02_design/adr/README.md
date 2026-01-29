# Architecture Decision Records (ADR)

프로젝트의 주요 아키텍처 결정을 기록합니다.

## ADR 목록

| ADR | 제목 | 상태 | 일자 |
|-----|------|------|------|
| [ADR-001](./ADR-001-serialization-strategy.md) | API 응답 직렬화 전략 (camelCase 통일) | Accepted | 2026-01-29 |
| [ADR-002](./ADR-002-search-api-authentication.md) | 검색 API 인증 정책 (JWT 필수) | Accepted | 2026-01-29 |
| [ADR-003](./ADR-003-auth-endpoint-security.md) | Auth 엔드포인트 보안 정책 | Accepted | 2026-01-29 |

## ADR 상태 정의

| 상태 | 설명 |
|------|------|
| Proposed | 검토 중인 결정 |
| Accepted | 승인된 결정 (적용 중) |
| Deprecated | 더 이상 유효하지 않음 |
| Superseded | 다른 ADR로 대체됨 |

## ADR 작성 가이드

새로운 아키텍처 결정이 필요한 경우:

1. `ADR-XXX-title.md` 파일 생성
2. 템플릿 구조 준수
3. TechLead 리뷰 요청
4. README.md 목록 업데이트

### 템플릿

```markdown
# ADR-XXX: 제목

## 상태
Proposed / Accepted / Deprecated / Superseded

## 일자
YYYY-MM-DD

## 컨텍스트
[배경 설명 - 왜 이 결정이 필요한가?]

## 결정
[결정 내용]

## 근거
[결정 이유]

## 결과
[예상 결과 및 영향]

## 관련 이슈
- SCRUM-XX
```

## 관련 문서

- [Backend 상세 설계서](../backend_detailed_design.md)
- [API 통합 설계서](../api_integration_design.md)
- [인프라 설계서](../infrastructure_detailed_design.md)
