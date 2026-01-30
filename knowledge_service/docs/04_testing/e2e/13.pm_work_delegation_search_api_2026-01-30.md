# PM 작업 위임서: Search API E2E 테스트 블로커 해결

**작성일**: 2026-01-30
**작성자**: PM Agent
**상태**: Open
**마감일**: 2026-01-31

---

## 1. 배경

QA Docker 환경 테스트 결과, 11개 테스트 중 9개 실패. 주요 원인 분석 완료.

### 1.1 테스트 결과 요약

| 테스트 유형 | 결과 | 원인 |
|------------|------|------|
| Login API | 2/3 Pass | Vite proxy 타임아웃 |
| Search API | 0/3 Pass | API 형식 불일치 |
| Dashboard API | 0/2 Pass | 로그인 후 리다이렉트 실패 |
| Navigation | 1/1 Pass | - |
| Response Time | 1/2 Pass | Search API 호출 실패 |

### 1.2 근본 원인

1. **Frontend-Backend API 형식 불일치**
2. **Vite proxy 환경에서 waitForResponse 타임아웃**
3. **Docker 환경 라우팅 이슈**

---

## 2. API 형식 불일치 상세

### 2.1 Frontend SearchQuery (src/services/searchService.ts)

```typescript
interface SearchQuery {
  query: string;
  filters?: {
    documentType?: string;    // 단수
    projectName?: string;     // 단수
    dateFrom?: string;
    dateTo?: string;
  };
  page?: number;
  pageSize?: number;
}
```

### 2.2 Backend SearchRequest (SearchRequest.java)

```java
public class SearchRequest {
    private String query;              // OK
    private Integer topK = 10;         // Frontend: pageSize
    private Boolean useGraph = true;   // Frontend에 없음
    private Boolean useVector = true;  // Frontend에 없음
    private List<String> documentTypes; // Frontend: documentType (단수)
    private List<String> projectNames;  // Frontend: projectName (단수)
    private Map<String, Object> filters;
}
```

### 2.3 불일치 항목

| Frontend 필드 | Backend 필드 | 상태 |
|--------------|-------------|------|
| `query` | `query` | OK |
| `pageSize` | `topK` | 불일치 |
| `filters.documentType` | `documentTypes` | 불일치 (단수 vs 복수) |
| `filters.projectName` | `projectNames` | 불일치 (단수 vs 복수) |
| `page` | - | Frontend only |
| `filters.dateFrom/dateTo` | - | Frontend only |
| - | `useGraph/useVector` | Backend only |

---

## 3. 작업 위임

### 3.1 Backend Developer (P0 - 즉시)

**작업명**: Search API 요청 형식 호환성 개선

**요구사항**:
1. `SearchRequest.java`에 Frontend 호환 필드 추가:
   - `page` (Integer) - 페이지 번호
   - `pageSize` (Integer) - `topK` 대신 또는 alias로
   - `documentType` (String) - `documentTypes` alias
   - `projectName` (String) - `projectNames` alias
   - `dateFrom` (String) - 날짜 필터
   - `dateTo` (String) - 날짜 필터

2. `SearchService.java`에서 양쪽 형식 모두 처리하도록 로직 수정

3. 또는 Frontend와 협의하여 한쪽으로 통일

**마감**: 2026-01-31

### 3.2 Frontend Developer (P1 - 1일 이내)

**작업명**: Search API 요청 형식 Backend 호환성 확인

**요구사항**:
1. `searchService.ts`에서 Backend 요구 형식으로 변환:
   - `pageSize` -> `topK`
   - `documentType` -> `documentTypes` (배열로)
   - `projectName` -> `projectNames` (배열로)

2. 또는 Backend와 협의하여 한쪽으로 통일

**마감**: 2026-01-31

### 3.3 QA Engineer (P1 - 1일 이내)

**작업명**: E2E 테스트 Vite proxy 환경 호환성 개선

**요구사항**:
1. `waitForResponse()` 타임아웃 증가 (15s -> 30s)
2. Vite proxy 환경에서 URL 패턴 조정
3. Docker 환경 변수 명확화 (`TEST_ENV=docker`)

**마감**: 2026-01-31

---

## 4. 협업 방식

### 4.1 권장 접근 (Backend 주도)

Backend에서 Frontend 형식을 수용하는 것이 더 간단합니다:

```java
// SearchRequest.java에 추가
@JsonAlias({"pageSize"})
private Integer topK = 10;

// 단일 값도 List로 변환
@JsonSetter("documentType")
public void setDocumentType(String type) {
    this.documentTypes = List.of(type);
}
```

### 4.2 대안 (Frontend 수정)

Frontend에서 Backend 형식으로 변환:

```typescript
const params = {
  query: searchQuery.query,
  topK: searchQuery.pageSize ?? 10,
  documentTypes: searchQuery.filters?.documentType
    ? [searchQuery.filters.documentType] : undefined,
  // ...
};
```

---

## 5. 검증 방법

### 5.1 로컬 테스트

```bash
# Backend 직접 호출 테스트
curl -X POST http://localhost:8081/api/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "RAG pipeline",
    "pageSize": 10,
    "filters": {
      "documentType": "document"
    }
  }'
```

### 5.2 E2E 테스트

```bash
TEST_ENV=docker npx playwright test ui-api-verification.spec.ts --reporter=list
```

---

## 6. 참고 자료

- [Docker 환경 테스트 결과](./12.docker-env-test-result_2026-01-30.md)
- [QA 테스트 이슈 보고서](./09.qa_test_issue_report_2026-01-30.md)
- [Backend SearchController](../../../backend/src/main/java/com/knowledge/backend/api/controller/SearchController.java)
- [Frontend searchService](../../frontend/src/services/searchService.ts)

---

## 7. 담당자 및 일정

| 작업 | 담당 Agent | 우선순위 | 마감 |
|------|-----------|----------|------|
| Search API 호환성 개선 | Backend | P0 | 2026-01-31 |
| Frontend 형식 조정 | Frontend | P1 | 2026-01-31 |
| E2E 테스트 개선 | QA | P1 | 2026-01-31 |

---

**PM 승인**: PM Agent
**작성일**: 2026-01-30

---

*이 작업 위임서는 PM Agent가 작성했습니다. 담당 Agent는 작업 완료 후 Slack으로 보고해주세요.*
