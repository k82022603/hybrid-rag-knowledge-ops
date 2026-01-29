# ADR-001: API 응답 직렬화 전략 (camelCase 통일)

## 상태
Accepted

## 일자
2026-01-29

## 컨텍스트

Sprint 04 Day 3 Docker E2E 테스트에서 19건 중 14건이 **LoginResponse 직렬화 불일치**로 실패했습니다 (SCRUM-57).

### 문제 상황

| 계층 | 언어 | 기본 네이밍 컨벤션 |
|------|------|-------------------|
| Backend (Spring) | Java/Kotlin | camelCase |
| AI Service | Python | snake_case |
| Frontend | TypeScript | camelCase |

Backend의 `LoginResponse` DTO가 Java 기본 camelCase(`accessToken`)로 직렬화되었으나, 테스트 코드에서는 `access_token`(snake_case)을 기대하여 14건의 E2E 테스트가 실패했습니다.

```java
// Backend LoginResponse.java (기존)
public record LoginResponse(
    String accessToken,    // Java는 camelCase
    String refreshToken,
    String tokenType,
    Long expiresIn
) {}
```

```typescript
// Frontend 기대값
interface LoginResponse {
    accessToken: string;    // TypeScript도 camelCase 선호
    refreshToken: string;
    tokenType: string;
    expiresIn: number;
}
```

```python
# E2E 테스트 (잘못된 기대)
response_data["access_token"]  # snake_case 기대 → 실패
```

## 결정

**모든 API 응답은 camelCase로 통일합니다.**

### 상세 규칙

| 적용 대상 | 규칙 | 예시 |
|----------|------|------|
| REST API 응답 (JSON) | camelCase | `accessToken`, `userId`, `createdAt` |
| 요청 Body (JSON) | camelCase | `userEmail`, `pageSize` |
| URL 경로/쿼리 파라미터 | kebab-case 또는 snake_case | `/api/v1/auth/login`, `page_size=10` |
| 내부 Python 코드 | snake_case (PEP8) | `access_token`, `user_id` |
| 내부 Java 코드 | camelCase (Java 표준) | `accessToken`, `userId` |

### 구현 방법

#### Backend (Spring Boot)
```java
// LoginResponse.java - @JsonProperty 명시적 지정
public record LoginResponse(
    @JsonProperty("accessToken") String accessToken,
    @JsonProperty("refreshToken") String refreshToken,
    @JsonProperty("tokenType") String tokenType,
    @JsonProperty("expiresIn") Long expiresIn
) {}
```

#### AI Service (FastAPI/Pydantic)
```python
# response_models.py
from pydantic import BaseModel, Field

class TokenResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    
    class Config:
        populate_by_name = True  # alias와 field name 둘 다 허용
        by_alias = True          # 응답 시 alias(camelCase) 사용
```

## 근거

1. **JavaScript/TypeScript 친화적**: Frontend가 주요 API 소비자이며 camelCase가 표준
2. **일관성**: 단일 규칙으로 모든 API 응답 통일
3. **최소 변경**: Java는 이미 camelCase, Python만 alias 설정 추가
4. **14건 테스트 연쇄 해결**: SCRUM-57 해결 시 14/19 실패 케이스 동시 해결

## 결과

### 긍정적 영향
- E2E 테스트 14건 연쇄 해결 (도미노 효과)
- Frontend 개발자 생산성 향상 (타입 변환 불필요)
- API 문서와 실제 응답 일치

### 부정적 영향
- Python 서비스에서 Pydantic alias 설정 필요
- 기존 Python 테스트 코드 수정 필요

### 마이그레이션

| 단계 | 작업 | 담당 |
|------|------|------|
| 1 | Backend LoginResponse @JsonProperty 추가 | Backend |
| 2 | AI Service Pydantic 모델 alias 설정 | RAG |
| 3 | E2E 테스트 코드 camelCase로 수정 | QA |
| 4 | 전체 Docker E2E 재검증 | QA |

## 관련 이슈

- **SCRUM-57**: LoginResponse camelCase vs snake_case 불일치 (14건 실패)
- **Sprint 04 Day 3**: Docker E2E 실패 근본원인 분석

## 참고 자료

- [Google JSON Style Guide](https://google.github.io/styleguide/jsoncstyleguide.xml) - camelCase 권장
- [Pydantic Field Aliases](https://docs.pydantic.dev/latest/concepts/fields/#field-aliases)
- [Spring @JsonProperty](https://fasterxml.github.io/jackson-annotations/javadoc/2.13/com/fasterxml/jackson/annotation/JsonProperty.html)
