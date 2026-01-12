# 사내 지식 검색 시스템 프론트엔드 구축계획서
## React 기반 Knowledge Discovery Platform

---

## 1. 프로젝트 개요

### 1.1 프로젝트 목적

사내 지식 검색 시스템의 프론트엔드는 사용자와 Graph RAG 기반 지능형 검색 엔진을 연결하는 핵심 인터페이스입니다. 단순한 검색 창을 넘어서 지식의 생성, 관리, 탐색, 시각화를 통합적으로 지원하는 플랫폼을 구축합니다. 사용자들이 직관적으로 지식을 등록하고, 대화형 인터페이스를 통해 필요한 정보를 빠르게 찾으며, 검색 결과를 다양한 형태로 활용할 수 있는 환경을 제공합니다.

본 프론트엔드는 백엔드의 강력한 Graph RAG 엔진과 시간 인식 추론 기능을 최대한 활용하면서도, 사용자가 이러한 복잡성을 느끼지 않고 자연스럽게 사용할 수 있도록 설계됩니다. 특히 검색 결과의 시각화, 지식 간의 연결 관계 표현, 개인화된 추천 등을 통해 단순한 검색 도구가 아닌 지식 발견 플랫폼으로서의 역할을 수행합니다.

### 1.2 핵심 가치 제안

사용자들은 본 시스템을 통해 세 가지 핵심 가치를 경험하게 됩니다. 첫째, 지식 관리의 간편화입니다. 복잡한 분류 체계나 메타데이터 입력 없이도 자연어로 지식을 등록하면, AI가 자동으로 관련 엔티티를 추출하고 적절한 카테고리로 분류합니다. 둘째, 지능형 검색 경험입니다. 단순 키워드 매칭이 아닌 의도를 이해하는 검색을 통해 원하는 정보를 정확하게 찾을 수 있습니다. 채팅 모드에서는 자연스러운 대화로 질문하고, 검색 모드에서는 다양한 필터와 정렬 옵션으로 정교한 탐색이 가능합니다. 셋째, 다양한 형태의 결과 활용입니다. 검색 결과를 그대로 읽는 것을 넘어서 마크다운으로 편집하거나, 차트로 시각화하거나, 엑셀/PPT/PDF로 변환하여 보고서에 즉시 활용할 수 있습니다.

### 1.3 기술적 특징

본 프론트엔드는 최신 웹 기술 스택을 활용하여 성능, 확장성, 유지보수성을 모두 확보합니다. React 18의 Concurrent Features를 활용하여 대량의 검색 결과도 부드럽게 렌더링하며, TypeScript를 통해 타입 안정성을 보장합니다. SpringBoot/SpringCloud 백엔드와의 통신은 RESTful API와 WebSocket을 병행하여 실시간성이 요구되는 채팅 기능과 일반적인 CRUD 작업을 모두 효율적으로 처리합니다.

OAuth 2.0 기반 인증 체계를 통해 기업의 기존 SSO와 통합되며, JWT 토큰을 활용한 stateless 인증으로 확장성을 확보합니다. Docker Compose를 통한 컨테이너화로 개발 환경과 프로덕션 환경의 일관성을 유지하며, Google Antigravity IDE와 Claude Code를 함께 활용하여 AI 기반 개발 생산성을 극대화합니다.

---

## 2. 기술 스택 및 아키텍처

### 2.1 프론트엔드 기술 스택

#### 2.1.1 코어 프레임워크

React 18을 기반으로 하는 본 애플리케이션은 최신 웹 개발 패러다임을 적극 활용합니다. React 18의 Concurrent Rendering을 통해 검색 결과가 대량으로 반환되더라도 UI가 멈추지 않고 부드럽게 동작합니다. Suspense와 Error Boundary를 활용하여 로딩 상태와 에러 상태를 우아하게 처리합니다.

TypeScript 5.x를 전면 적용하여 타입 안정성을 확보합니다. 백엔드 API의 응답 타입을 정의하고, 컴포넌트 props와 state의 타입을 명시하여 런타임 에러를 컴파일 타임에 사전 방지합니다. 특히 복잡한 지식 객체의 구조를 타입으로 정의하여 개발자 경험을 향상시킵니다.

상태 관리는 Redux Toolkit을 메인으로 사용하되, 서버 상태 관리는 React Query(TanStack Query)를 병행합니다. 로컬 상태는 Redux가 관리하고, 서버에서 가져오는 검색 결과, 지식 목록 등은 React Query가 캐싱과 동기화를 담당하여 네트워크 요청을 최소화합니다.

#### 2.1.2 UI 프레임워크 및 라이브러리

Material-UI (MUI) v5를 주요 컴포넌트 라이브러리로 채택하여 일관된 디자인 시스템을 구축합니다. MUI의 테마 시스템을 커스터마이징하여 기업 브랜드 아이덴티티를 반영하고, 다크모드를 지원하여 사용자 선호도에 맞춥니다.

마크다운 렌더링을 위해 react-markdown을 사용하며, 코드 하이라이팅은 Prism.js로 처리합니다. 수식 표현이 필요한 경우 KaTeX를 통합하여 LaTeX 문법을 지원합니다. Chart 렌더링은 Recharts를 기본으로 하되, 복잡한 시각화가 필요한 경우 D3.js를 직접 활용합니다. SVG는 자체 렌더링 엔진을 구현하고, Mermaid 다이어그램은 mermaid.js 라이브러리를 통합합니다.

문서 변환 기능을 위해 여러 라이브러리를 조합합니다. 엑셀 변환은 SheetJS(xlsx) 라이브러리로 처리하며, PDF 생성은 jsPDF와 html2canvas를 결합하여 화면의 HTML을 PDF로 변환합니다. PPT 생성은 PptxGenJS를 활용하여 프로그래매틱하게 슬라이드를 생성합니다.

#### 2.1.3 개발 도구 및 빌드 시스템

Vite를 빌드 도구로 사용하여 빠른 개발 서버 시작과 HMR(Hot Module Replacement)을 경험합니다. Webpack보다 훨씬 빠른 빌드 속도로 개발 생산성을 높입니다. ESLint와 Prettier를 통해 코드 품질과 일관성을 유지하며, Husky와 lint-staged를 활용하여 커밋 전 자동 검사를 수행합니다.

테스트는 Vitest와 React Testing Library를 조합하여 단위 테스트와 통합 테스트를 작성합니다. E2E 테스트는 Playwright를 사용하여 실제 사용자 시나리오를 검증합니다. Storybook을 도입하여 컴포넌트를 독립적으로 개발하고 문서화합니다.

### 2.2 백엔드 연동 아키텍처

#### 2.2.1 SpringBoot/SpringCloud 통합

백엔드는 SpringBoot 3.x 기반의 마이크로서비스 아키텍처로 구성됩니다. Spring Cloud Gateway가 API Gateway 역할을 수행하며, 프론트엔드의 모든 요청은 이 Gateway를 통해 라우팅됩니다. 인증/인가, 로깅, 모니터링 등의 공통 관심사는 Gateway 레벨에서 처리됩니다.

주요 마이크로서비스는 다음과 같이 구성됩니다. Knowledge Service는 지식의 CRUD를 담당하며, PostgreSQL과 Neo4j에 데이터를 저장합니다. Search Service는 Graph RAG 엔진과 통신하여 검색을 수행하며, Elasticsearch와 연동됩니다. User Service는 사용자 정보와 권한을 관리하며, OAuth Provider와 통합됩니다. Analytics Service는 사용자 행동을 추적하고 인기 지식, 추천 등의 데이터를 생성합니다.

프론트엔드는 이러한 서비스들과 RESTful API로 통신하며, 실시간 채팅 기능은 WebSocket(STOMP over WebSocket)을 활용합니다. Spring Cloud의 Service Discovery(Eureka)와 Load Balancing(Ribbon)을 통해 서비스 간 통신의 탄력성을 확보합니다.

#### 2.2.2 API 설계 원칙

모든 API는 RESTful 원칙을 따르며, 버전 관리를 위해 URL에 버전을 명시합니다(`/api/v1/knowledge`). 응답 형식은 일관된 구조를 유지하여 프론트엔드에서 예측 가능하게 처리할 수 있도록 합니다.

성공 응답은 다음 구조를 따릅니다:
```json
{
  "success": true,
  "data": { /* 실제 데이터 */ },
  "message": "성공 메시지",
  "timestamp": "2026-01-09T12:00:00Z"
}
```

에러 응답은 다음 구조를 따릅니다:
```json
{
  "success": false,
  "error": {
    "code": "KNOWLEDGE_NOT_FOUND",
    "message": "지식을 찾을 수 없습니다",
    "details": { /* 추가 정보 */ }
  },
  "timestamp": "2026-01-09T12:00:00Z"
}
```

페이지네이션이 필요한 API는 cursor-based pagination을 기본으로 하되, offset-based pagination도 선택적으로 지원합니다. 정렬, 필터링 등의 쿼리 파라미터는 표준화된 형식을 사용합니다.

### 2.3 인증/인가 아키텍처

OAuth 2.0 Authorization Code Flow를 사용하여 엔터프라이즈 SSO와 통합됩니다. 사용자가 로그인을 시도하면 OAuth Provider(예: Keycloak, Okta, Azure AD)로 리다이렉트되고, 인증 후 Authorization Code를 받아 백엔드에서 Access Token과 Refresh Token을 획득합니다.

Access Token은 JWT 형태로 발급되며, 프론트엔드는 이를 메모리에 저장하고 모든 API 요청의 Authorization 헤더에 포함시킵니다. Token의 만료 시간이 가까워지면 자동으로 Refresh Token을 사용하여 갱신합니다. PKCE(Proof Key for Code Exchange)를 적용하여 보안을 강화합니다.

권한 관리는 RBAC(Role-Based Access Control) 방식을 채택합니다. 사용자의 역할(Role)에 따라 접근 가능한 기능과 데이터가 결정됩니다. 일반 사용자(User), 지식 관리자(Knowledge Manager), 시스템 관리자(Admin) 등의 역할이 정의되며, 각 역할에 대한 권한은 백엔드에서 중앙 집중식으로 관리됩니다.

프론트엔드는 사용자의 권한 정보를 바탕으로 UI 요소를 조건부로 렌더링합니다. 예를 들어 일반 사용자는 지식 삭제 버튼을 볼 수 없고, 지식 관리자만 볼 수 있습니다. 그러나 이는 UX 개선을 위한 것일 뿐, 실제 권한 검증은 백엔드에서 수행됩니다.

---

## 3. 기능 명세서

### 3.1 지식 관리 (Knowledge Management)

#### 3.1.1 지식 등록 (Create Knowledge)

**기능 개요**
사용자가 새로운 지식을 시스템에 등록하는 기능입니다. 단순한 텍스트 입력뿐만 아니라 파일 첨부, 태그 설정, 프로젝트 연결 등 다양한 메타데이터를 함께 입력할 수 있습니다.

**상세 기능**

| 항목 | 설명 |
|------|------|
| **제목 입력** | 지식의 제목을 입력합니다. 최대 500자, 필수 입력 항목입니다. |
| **본문 입력** | 마크다운 에디터를 통해 본문을 작성합니다. 이미지 삽입, 표 작성, 코드 블록 등을 지원합니다. |
| **파일 첨부** | 관련 파일을 첨부할 수 있습니다. PDF, Word, Excel, PPT 등 최대 10MB까지 업로드 가능합니다. |
| **태그 설정** | 자동 추천 태그와 사용자 정의 태그를 설정할 수 있습니다. AI가 본문을 분석하여 관련 태그를 추천합니다. |
| **프로젝트 연결** | 특정 프로젝트와 연결할 수 있습니다. 프로젝트 검색 기능을 통해 쉽게 찾을 수 있습니다. |
| **카테고리 선택** | 대분류/중분류/소분류 형태의 카테고리를 선택합니다. AI가 자동으로 적절한 카테고리를 제안합니다. |
| **유효기간 설정** | 지식의 유효 시작일과 종료일을 설정할 수 있습니다. 정책이나 규정 문서에 유용합니다. |
| **공개 범위 설정** | 전체 공개, 부서 공개, 특정 사용자 공개 등을 선택할 수 있습니다. |
| **미리보기** | 작성 중인 지식을 실시간으로 미리보기할 수 있습니다. |
| **임시 저장** | 작성 중인 내용을 임시 저장하여 나중에 이어서 작성할 수 있습니다. |

**입력 검증**
- 제목: 1-500자, 특수문자 제한
- 본문: 최대 100,000자
- 파일: 허용된 확장자, 크기 제한 검증
- 태그: 최대 20개, 각 태그는 50자 이내

**백엔드 API**
```
POST /api/v1/knowledge
Content-Type: multipart/form-data

{
  "title": "지식 제목",
  "content": "마크다운 본문",
  "tags": ["태그1", "태그2"],
  "projectId": "프로젝트 ID",
  "categoryId": "카테고리 ID",
  "validFrom": "2026-01-09",
  "validTo": "2027-01-09",
  "visibility": "PUBLIC",
  "files": [파일 객체들]
}
```

**UI/UX 요구사항**
- 마크다운 에디터는 실시간 미리보기를 제공해야 합니다
- 태그 입력 시 자동완성 기능을 제공해야 합니다
- 파일 업로드는 드래그 앤 드롭을 지원해야 합니다
- 작성 중 네트워크 오류 시 자동 임시 저장이 작동해야 합니다
- 등록 완료 후 해당 지식 상세 페이지로 자동 이동합니다

#### 3.1.2 지식 수정 (Update Knowledge)

**기능 개요**
기존 지식의 내용을 수정하는 기능입니다. 수정 이력이 자동으로 기록되며, 이전 버전과 비교할 수 있습니다.

**상세 기능**

| 항목 | 설명 |
|------|------|
| **내용 수정** | 제목, 본문, 태그 등 모든 항목을 수정할 수 있습니다. |
| **버전 관리** | 수정 시마다 새로운 버전이 생성됩니다. 이전 버전 조회 및 복원이 가능합니다. |
| **변경 사항 표시** | 이전 버전과의 차이(diff)를 하이라이트로 표시합니다. |
| **수정 사유 입력** | 왜 수정했는지 사유를 선택적으로 입력할 수 있습니다. |
| **권한 확인** | 작성자 본인 또는 관리자만 수정 가능합니다. |

**백엔드 API**
```
PUT /api/v1/knowledge/{knowledgeId}
Content-Type: application/json

{
  "title": "수정된 제목",
  "content": "수정된 본문",
  "reason": "정보 업데이트"
}
```

**UI/UX 요구사항**
- 수정 페이지는 등록 페이지와 동일한 UI를 사용하되, 기존 내용이 미리 채워져 있어야 합니다
- "변경 사항 비교" 버튼을 통해 이전 버전과의 차이를 모달로 표시합니다
- 수정 권한이 없는 사용자에게는 수정 버튼이 표시되지 않습니다
- 수정 완료 후 성공 메시지를 표시하고 지식 상세 페이지를 새로고침합니다

#### 3.1.3 지식 삭제 (Delete Knowledge)

**기능 개요**
지식을 삭제하는 기능입니다. 소프트 삭제 방식을 사용하여 실제로는 삭제 플래그만 설정하고, 관리자가 완전히 삭제할 수 있습니다.

**상세 기능**

| 항목 | 설명 |
|------|------|
| **소프트 삭제** | 사용자가 삭제하면 화면에서는 보이지 않지만 DB에는 남아있습니다. |
| **삭제 확인** | 삭제 전 확인 다이얼로그를 표시하여 실수를 방지합니다. |
| **삭제 사유** | 삭제 사유를 선택적으로 입력할 수 있습니다. |
| **복구 기능** | 관리자는 삭제된 지식을 복구할 수 있습니다. |
| **영구 삭제** | 관리자는 소프트 삭제된 지식을 영구 삭제할 수 있습니다. |

**백엔드 API**
```
DELETE /api/v1/knowledge/{knowledgeId}
Content-Type: application/json

{
  "reason": "중복된 정보"
}
```

**UI/UX 요구사항**
- 삭제 버튼 클릭 시 "정말 삭제하시겠습니까?" 확인 다이얼로그를 표시합니다
- 삭제 완료 후 지식 목록 페이지로 이동하며 성공 메시지를 표시합니다
- 관리자 페이지에서는 삭제된 지식 목록을 별도로 조회할 수 있어야 합니다

### 3.2 대시보드 (Dashboard)

#### 3.2.1 메인 대시보드

**기능 개요**
사용자가 로그인 후 처음 보게 되는 화면으로, 시스템의 전반적인 현황과 개인화된 정보를 한눈에 파악할 수 있습니다.

**상세 기능**

| 위젯 | 설명 |
|------|------|
| **인기 지식 TOP 10** | 최근 7일간 가장 많이 조회된 지식 목록입니다. 제목, 조회수, 좋아요 수를 표시합니다. |
| **최신 지식** | 최근 등록된 지식 목록입니다. 등록 시간, 작성자를 함께 표시합니다. |
| **내가 작성한 지식** | 로그인한 사용자가 작성한 지식 중 최근 5개를 표시합니다. |
| **내가 북마크한 지식** | 사용자가 북마크한 지식 목록입니다. |
| **추천 지식** | AI가 사용자의 관심사와 검색 이력을 바탕으로 추천하는 지식입니다. |
| **검색 트렌드** | 최근 많이 검색된 키워드를 워드 클라우드로 표시합니다. |
| **지식 통계** | 전체 지식 수, 오늘 등록된 지식 수, 총 사용자 수 등을 카드 형태로 표시합니다. |
| **카테고리별 분포** | 지식이 카테고리별로 얼마나 분포되어 있는지 도넛 차트로 표시합니다. |
| **활동 타임라인** | 시스템 내 최근 활동(지식 등록, 댓글 작성 등)을 시간순으로 표시합니다. |
| **공지사항** | 시스템 관련 공지사항이나 중요한 업데이트를 상단에 표시합니다. |

**백엔드 API**
```
GET /api/v1/dashboard
Response:
{
  "popularKnowledge": [...],
  "latestKnowledge": [...],
  "myKnowledge": [...],
  "bookmarked": [...],
  "recommended": [...],
  "searchTrends": [...],
  "statistics": {...},
  "categoryDistribution": [...],
  "recentActivities": [...],
  "announcements": [...]
}
```

**UI/UX 요구사항**
- 모든 위젯은 그리드 레이아웃으로 배치되며, 사용자가 위치를 드래그 앤 드롭으로 조정할 수 있어야 합니다
- 각 위젯은 최소화/최대화 기능을 제공해야 합니다
- 모바일에서는 위젯이 세로로 스택되어 표시됩니다
- 로딩 중에는 스켈레톤 UI를 표시합니다
- 데이터 새로고침 버튼을 제공하여 최신 정보로 업데이트할 수 있습니다

### 3.3 개인화 페이지 (Personalization)

#### 3.3.1 개인 프로필 관리

**기능 개요**
사용자 개인의 프로필 정보를 조회하고 수정하는 기능입니다.

**상세 기능**

| 항목 | 설명 |
|------|------|
| **프로필 사진** | 사용자 프로필 사진을 업로드하거나 변경할 수 있습니다. |
| **기본 정보** | 이름, 이메일, 부서, 직급 등의 정보를 표시합니다. (SSO에서 가져온 정보는 수정 불가) |
| **선호 설정** | 언어, 테마(라이트/다크), 알림 설정 등을 변경할 수 있습니다. |
| **관심 태그** | 사용자가 관심있는 태그를 등록하여 맞춤형 추천을 받을 수 있습니다. |
| **검색 기록** | 최근 검색한 키워드 목록을 보여주며, 개별 삭제 또는 전체 삭제가 가능합니다. |

**백엔드 API**
```
GET /api/v1/users/me
PUT /api/v1/users/me/preferences
```

**UI/UX 요구사항**
- 프로필 사진은 원형으로 표시되며 hover 시 "변경" 버튼이 나타납니다
- 수정 불가능한 필드는 회색으로 표시하고 툴팁으로 이유를 설명합니다
- 설정 변경 시 즉시 반영되며, 저장 성공 메시지를 토스트로 표시합니다

#### 3.3.2 내 지식 관리

**기능 개요**
사용자가 작성한 모든 지식을 한 곳에서 관리할 수 있는 기능입니다.

**상세 기능**

| 항목 | 설명 |
|------|------|
| **목록 조회** | 작성한 모든 지식을 테이블 형태로 표시합니다. |
| **필터링** | 카테고리, 태그, 작성일, 상태(공개/비공개) 등으로 필터링할 수 있습니다. |
| **정렬** | 작성일, 조회수, 좋아요 수 등으로 정렬할 수 있습니다. |
| **일괄 작업** | 체크박스로 여러 지식을 선택하여 일괄 삭제, 공개 범위 변경 등을 수행할 수 있습니다. |
| **통계 보기** | 총 작성 수, 평균 조회수, 받은 좋아요 수 등의 통계를 표시합니다. |

**백엔드 API**
```
GET /api/v1/knowledge/my?page=1&size=20&sort=createdAt,desc
```

**UI/UX 요구사항**
- 테이블 헤더 클릭으로 정렬 방향을 토글할 수 있어야 합니다
- 각 행의 액션 버튼(수정, 삭제, 공유)은 hover 시에만 표시됩니다
- 페이지네이션은 무한 스크롤 또는 페이지 번호 중 선택 가능합니다

#### 3.3.3 북마크 관리

**기능 개요**
사용자가 북마크한 지식을 관리하는 기능입니다.

**상세 기능**

| 항목 | 설명 |
|------|------|
| **북마크 추가/제거** | 지식 상세 페이지에서 북마크 버튼 클릭으로 추가/제거합니다. |
| **폴더 관리** | 북마크를 폴더로 분류하여 관리할 수 있습니다. |
| **메모 추가** | 각 북마크에 개인적인 메모를 추가할 수 있습니다. |
| **공유** | 북마크 폴더를 다른 사용자와 공유할 수 있습니다. |

**백엔드 API**
```
POST /api/v1/bookmarks
DELETE /api/v1/bookmarks/{knowledgeId}
GET /api/v1/bookmarks
```

**UI/UX 요구사항**
- 북마크 버튼은 별 아이콘으로 표시되며, 활성/비활성 상태를 명확히 구분합니다
- 폴더는 트리 구조로 표시되며 드래그 앤 드롭으로 북마크를 이동할 수 있습니다

#### 3.3.4 개인화 페이지 검색

**기능 개요**
개인화 페이지 내에서 자신이 작성한 지식, 북마크한 지식, 조회한 지식 등을 빠르게 검색하는 기능입니다.

**상세 기능**

| 항목 | 설명 |
|------|------|
| **통합 검색** | 내 지식, 북마크, 검색 기록을 한 번에 검색합니다. |
| **범위 선택** | 검색 대상을 내 지식만, 북마크만 등으로 제한할 수 있습니다. |
| **고급 필터** | 날짜 범위, 태그, 카테고리 등 세밀한 필터를 적용할 수 있습니다. |
| **검색 결과 그룹화** | 결과를 카테고리별, 날짜별로 그룹화하여 표시합니다. |

**백엔드 API**
```
GET /api/v1/search/personal?q=검색어&scope=my_knowledge&dateFrom=2026-01-01
```

**UI/UX 요구사항**
- 검색창은 페이지 상단에 고정되어 있어야 합니다
- 검색 결과는 실시간으로 필터링되어 표시됩니다
- 검색어 하이라이팅을 제공하여 매칭된 부분을 강조합니다

### 3.4 지식 검색 (Knowledge Search)

#### 3.4.1 검색 모드

**기능 개요**
사용자가 지식을 검색하는 주요 기능으로, 채팅 모드와 검색 모드를 지원합니다.

**채팅 모드 (Chat Mode)**

채팅 모드는 자연어로 질문하고 대화형으로 답변을 받는 방식입니다. Graph RAG 엔진과 Claude LLM이 결합되어 사용자의 의도를 파악하고 맥락에 맞는 답변을 생성합니다.

| 기능 | 설명 |
|------|------|
| **자연어 질문** | "프로젝트 A의 기술 스택은 뭐야?", "2023년 보안 정책 알려줘" 등 자연스러운 문장으로 질문합니다. |
| **대화 컨텍스트 유지** | 이전 대화 내용을 기억하여 연속적인 질문에 답변합니다. "그럼 프로젝트 B는?" 같은 후속 질문 가능. |
| **실시간 스트리밍** | Claude의 답변이 생성되는 대로 실시간으로 화면에 표시됩니다. (SSE 또는 WebSocket) |
| **소스 표시** | 답변의 근거가 된 지식 문서를 하단에 표시합니다. 클릭하면 원문 확인 가능. |
| **피드백** | 답변에 대한 평가(좋아요/싫어요)와 피드백 코멘트를 남길 수 있습니다. |
| **대화 저장** | 대화 내용을 저장하여 나중에 다시 불러올 수 있습니다. |

**검색 모드 (Search Mode)**

검색 모드는 전통적인 검색 엔진 방식으로, 키워드를 입력하면 관련 지식 목록이 순위별로 표시됩니다.

| 기능 | 설명 |
|------|------|
| **키워드 검색** | 제목, 본문, 태그에서 키워드를 검색합니다. |
| **고급 검색** | AND, OR, NOT 연산자와 따옴표("")를 사용한 정확한 구문 검색을 지원합니다. |
| **필터** | 카테고리, 작성자, 작성일, 프로젝트 등 다양한 필터를 적용할 수 있습니다. |
| **정렬** | 관련도순, 최신순, 인기순, 조회수순 등으로 정렬할 수 있습니다. |
| **패싯 검색** | 왼쪽 사이드바에 카테고리, 태그, 작성자 등의 패싯을 표시하여 클릭으로 필터링합니다. |
| **검색 제안** | 입력 중 자동완성과 추천 검색어를 제공합니다. |
| **검색 결과 미리보기** | 각 결과에 본문의 일부를 스니펫으로 표시하며, 검색어는 하이라이팅됩니다. |

**백엔드 API**
```
# 채팅 모드
POST /api/v1/search/chat
{
  "message": "프로젝트 A 기술 스택",
  "conversationId": "uuid",
  "stream": true
}

# 검색 모드
GET /api/v1/search?q=검색어&category=카테고리&sort=relevance&page=1
```

**UI/UX 요구사항**
- 화면 상단에 "채팅" / "검색" 탭을 두어 모드를 쉽게 전환할 수 있어야 합니다
- 채팅 모드는 메신저 앱과 유사한 UI를 사용합니다 (내 질문은 오른쪽, AI 답변은 왼쪽)
- 검색 모드는 구글과 유사한 검색 결과 리스트 UI를 사용합니다
- 두 모드 모두 모바일 반응형으로 동작해야 합니다
- 로딩 중에는 스켈레톤 또는 스피너를 표시합니다

#### 3.4.2 검색 결과 시각화

**기능 개요**
검색 결과를 다양한 형태로 시각화하여 사용자가 정보를 더 쉽게 이해할 수 있도록 합니다.

**마크다운 렌더링**

검색 결과에 포함된 마크다운 문법을 HTML로 변환하여 표시합니다.

| 지원 요소 | 설명 |
|-----------|------|
| **헤더** | h1~h6 태그를 스타일링하여 계층 구조를 명확히 표시 |
| **리스트** | 순서 있는/없는 리스트, 체크박스 리스트 지원 |
| **링크** | 외부 링크는 새 탭에서 열기, 내부 링크는 동일 탭 |
| **이미지** | 이미지 lazy loading, 라이트박스 지원 |
| **코드** | 인라인 코드와 코드 블록, Syntax Highlighting |
| **인용** | 인용문 블록 스타일링 |
| **표** | 테이블 렌더링, 정렬 가능한 헤더 |
| **수식** | LaTeX 문법으로 작성된 수학 수식 렌더링 (KaTeX) |

**Chart 렌더링**

데이터를 포함한 검색 결과를 차트로 시각화합니다.

| 차트 타입 | 사용 사례 |
|-----------|----------|
| **라인 차트** | 시계열 데이터 (예: 프로젝트 진행률 추이) |
| **바 차트** | 카테고리별 비교 (예: 부서별 지식 수) |
| **파이 차트** | 비율 표시 (예: 기술 스택 분포) |
| **영역 차트** | 누적 데이터 (예: 월별 지식 증가량) |
| **산점도** | 상관관계 분석 (예: 조회수 vs 좋아요 수) |

차트는 대화형(interactive)이며, 호버 시 상세 데이터를 툴팁으로 표시합니다. 확대/축소, 데이터 필터링 등의 기능을 제공합니다.

**SVG 렌더링**

SVG 형식의 다이어그램을 직접 렌더링합니다. 아이콘, 로고, 간단한 다이어그램 등을 표시하며, 벡터 방식이므로 확대해도 깨짐 없이 선명하게 표시됩니다.

**Mermaid 다이어그램**

Mermaid 문법으로 작성된 다이어그램을 렌더링합니다.

| 다이어그램 타입 | 사용 사례 |
|----------------|----------|
| **플로우차트** | 프로세스 흐름 표현 |
| **시퀀스 다이어그램** | 시스템 간 상호작용 |
| **클래스 다이어그램** | 객체지향 설계 |
| **간트 차트** | 프로젝트 일정 |
| **ER 다이어그램** | 데이터베이스 스키마 |
| **상태 다이어그램** | 상태 전이 |

**UI/UX 요구사항**
- 마크다운 렌더링은 GitHub Flavored Markdown 스타일을 따릅니다
- 차트는 반응형으로 동작하여 화면 크기에 맞게 조정됩니다
- SVG와 Mermaid는 클릭하여 전체 화면 모드로 볼 수 있어야 합니다
- 렌더링 실패 시 원본 텍스트를 코드 블록으로 표시합니다

### 3.5 문서 변환 (Document Export)

#### 3.5.1 엑셀 변환

**기능 개요**
검색 결과나 지식 내용을 엑셀 파일로 변환하여 다운로드하는 기능입니다.

**상세 기능**

| 기능 | 설명 |
|------|------|
| **테이블 변환** | 마크다운 표를 엑셀 시트로 변환합니다. |
| **다중 시트** | 여러 지식을 각각의 시트로 구성할 수 있습니다. |
| **서식 적용** | 헤더 굵게, 셀 병합, 색상 등 기본 서식을 적용합니다. |
| **차트 포함** | 검색 결과에 포함된 차트를 엑셀 차트로 변환합니다. |
| **필터/정렬** | 엑셀의 자동 필터 기능이 적용된 상태로 생성합니다. |

**백엔드 API**
```
POST /api/v1/export/excel
{
  "knowledgeIds": ["id1", "id2"],
  "includeCharts": true,
  "format": "xlsx"
}

Response: Binary file download
```

**UI/UX 요구사항**
- 검색 결과 상단에 "엑셀로 내보내기" 버튼을 제공합니다
- 변환 옵션(시트 구성, 차트 포함 여부 등)을 선택할 수 있는 다이얼로그를 표시합니다
- 변환 중에는 프로그레스 바를 표시합니다
- 완료 후 브라우저의 다운로드 기능을 통해 파일을 저장합니다

#### 3.5.2 PPT 변환

**기능 개요**
검색 결과나 지식 내용을 파워포인트 파일로 변환하는 기능입니다.

**상세 기능**

| 기능 | 설명 |
|------|------|
| **자동 슬라이드 생성** | 마크다운의 헤더(#, ##)를 기준으로 슬라이드를 분할합니다. |
| **이미지 포함** | 본문의 이미지를 슬라이드에 삽입합니다. |
| **테이블 포함** | 마크다운 표를 PPT 테이블로 변환합니다. |
| **차트 포함** | 차트를 이미지로 변환하여 삽입합니다. |
| **테마 선택** | 여러 프레젠테이션 테마 중 선택할 수 있습니다. |
| **마스터 슬라이드** | 회사 로고와 템플릿을 적용할 수 있습니다. |

**백엔드 API**
```
POST /api/v1/export/ppt
{
  "knowledgeId": "id",
  "theme": "corporate",
  "includeTOC": true
}
```

**UI/UX 요구사항**
- 지식 상세 페이지와 검색 결과 페이지에서 PPT 변환 버튼을 제공합니다
- 테마 선택 프리뷰를 제공하여 최종 결과를 예상할 수 있습니다
- 슬라이드 분할 규칙을 커스터마이징할 수 있는 옵션을 제공합니다

#### 3.5.3 PDF 변환

**기능 개요**
검색 결과나 지식 내용을 PDF 파일로 변환하는 기능입니다.

**상세 기능**

| 기능 | 설명 |
|------|------|
| **HTML to PDF** | 렌더링된 HTML을 그대로 PDF로 변환합니다. |
| **페이지 설정** | 용지 크기(A4, Letter 등), 여백, 방향을 설정할 수 있습니다. |
| **헤더/푸터** | 페이지 번호, 제목, 날짜 등을 헤더/푸터에 추가할 수 있습니다. |
| **목차 생성** | 마크다운 헤더를 기반으로 자동 목차를 생성합니다. |
| **북마크** | PDF 내부 북마크를 생성하여 쉽게 탐색할 수 있습니다. |
| **워터마크** | 선택적으로 워터마크를 추가할 수 있습니다. |

**백엔드 API**
```
POST /api/v1/export/pdf
{
  "knowledgeId": "id",
  "pageSize": "A4",
  "includeTOC": true,
  "watermark": "CONFIDENTIAL"
}
```

**UI/UX 요구사항**
- PDF 미리보기 기능을 제공하여 다운로드 전 확인할 수 있습니다
- 변환 옵션을 프리셋으로 저장하여 재사용할 수 있습니다
- 여러 지식을 하나의 PDF로 병합하는 기능을 제공합니다

### 3.6 사용자 인증 및 권한 관리

#### 3.6.1 OAuth 로그인

**기능 개요**
기업의 SSO 시스템과 통합하여 OAuth 2.0 기반 로그인을 제공합니다.

**상세 기능**

| 기능 | 설명 |
|------|------|
| **SSO 연동** | Keycloak, Okta, Azure AD 등 표준 OAuth Provider 지원 |
| **자동 리다이렉트** | 미인증 사용자는 자동으로 OAuth 로그인 페이지로 이동 |
| **토큰 관리** | Access Token과 Refresh Token을 안전하게 관리 |
| **자동 갱신** | Access Token 만료 전 자동으로 Refresh |
| **로그아웃** | 세션 종료 및 토큰 무효화 |

**백엔드 API**
```
GET /oauth2/authorization/{provider}  # 로그인 시작
GET /login/oauth2/code/{provider}      # 콜백
POST /api/v1/auth/refresh              # 토큰 갱신
POST /api/v1/auth/logout               # 로그아웃
```

**UI/UX 요구사항**
- 로그인 페이지는 기업 브랜딩에 맞게 커스터마이징 가능해야 합니다
- OAuth Provider 선택 화면을 제공합니다 (여러 Provider 지원 시)
- 로그인 진행 상태를 명확히 표시합니다
- 로그인 실패 시 사용자 친화적인 에러 메시지를 표시합니다

#### 3.6.2 권한 관리

**기능 개요**
사용자의 역할에 따라 접근 가능한 기능과 데이터를 제어합니다.

**역할 정의**

| 역할 | 권한 |
|------|------|
| **일반 사용자 (User)** | 지식 조회, 검색, 본인이 작성한 지식 수정/삭제, 북마크 |
| **지식 관리자 (Knowledge Manager)** | 일반 사용자 권한 + 모든 지식 수정/삭제, 카테고리 관리 |
| **시스템 관리자 (Admin)** | 모든 권한 + 사용자 관리, 시스템 설정, 통계 조회 |

**UI/UX 요구사항**
- 권한이 없는 기능의 버튼은 비활성화하거나 숨깁니다
- 권한 부족으로 인한 접근 거부 시 명확한 안내 메시지를 표시합니다
- 관리자 페이지는 별도의 레이아웃과 네비게이션을 사용합니다

---

## 4. 화면 설계

### 4.1 레이아웃 구조

전체 레이아웃은 헤더, 사이드바, 메인 컨텐츠, 푸터로 구성됩니다.

**헤더 (Header)**
- 로고 및 애플리케이션 이름
- 전역 검색바
- 사용자 프로필 메뉴 (드롭다운)
- 알림 아이콘 (뱃지로 새 알림 표시)
- 테마 전환 버튼 (라이트/다크)

**사이드바 (Sidebar)**
- 대시보드
- 지식 검색
- 내 지식
- 북마크
- 카테고리 탐색
- 관리자 메뉴 (관리자만)

**메인 컨텐츠 (Main Content)**
- 각 페이지의 실제 내용이 표시되는 영역
- 브레드크럼 네비게이션 상단에 표시
- 컨텐츠 영역은 최대 너비를 제한하여 가독성 확보

**푸터 (Footer)**
- 저작권 정보
- 도움말 링크
- 개인정보처리방침
- 버전 정보

### 4.2 주요 화면별 상세 설계

#### 4.2.1 대시보드 화면

**레이아웃**
- 2열 그리드 (데스크톱), 1열 (모바일)
- 각 위젯은 카드 형태로 표시
- 위젯 간 간격은 16px

**위젯 구성**
1. **상단 통계 카드** (4개 가로 배열)
   - 전체 지식 수
   - 오늘 등록된 지식
   - 내 지식 수
   - 북마크 수

2. **인기 지식 TOP 10** (테이블)
   - 순위, 제목, 작성자, 조회수, 좋아요
   - 각 행 클릭 시 상세 페이지로 이동

3. **최신 지식** (카드 리스트)
   - 썸네일, 제목, 작성자, 작성일
   - 최대 5개 표시

4. **검색 트렌드** (워드 클라우드)
   - 최근 7일간 검색 키워드
   - 클릭하면 해당 키워드로 검색

5. **추천 지식** (카드 리스트)
   - AI 추천 지식 3개
   - "더보기" 버튼

6. **카테고리 분포** (도넛 차트)
   - 각 섹션 클릭 시 해당 카테고리 페이지로 이동

#### 4.2.2 검색 화면

**채팅 모드**
```
+------------------------------------------+
|  [채팅] [검색]                            |
+------------------------------------------+
|                                          |
|  [AI] 안녕하세요! 무엇을 도와드릴까요?     |
|                                          |
|  프로젝트 A 기술 스택 알려줘 [나]          |
|                                          |
|  [AI] 프로젝트 A는 다음 기술을 사용합니다: |
|       - Frontend: React, TypeScript      |
|       - Backend: Spring Boot             |
|       - Database: PostgreSQL, Neo4j      |
|                                          |
|  출처:                                    |
|  [📄 프로젝트 A 기술문서]                 |
|                                          |
+------------------------------------------+
| [메시지 입력...]              [전송]      |
+------------------------------------------+
```

**검색 모드**
```
+------------------------------------------+
|  [채팅] [검색]                            |
+------------------------------------------+
| 검색어: [_________________] [검색]        |
| 필터: [카테고리▼] [날짜▼] [작성자▼]       |
+------------------------------------------+
| 카테고리     | 검색 결과 (123건)            |
| □ 기술(45)   +-----------------------------+
| □ 정책(32)   | ⭐⭐⭐⭐⭐                  |
| □ 가이드(28) | **프로젝트 A 기술 문서**     |
| □ FAQ(18)    | 작성자: 김철수 | 2026-01-05  |
|              | ...본문 미리보기...          |
| 작성자       | 검색어 하이라이트 표시        |
| □ 김철수(23) +-----------------------------+
| □ 이영희(15) | ⭐⭐⭐⭐                    |
|              | **Spring Boot 시작하기**    |
|              | ...                          |
+------------------------------------------+
```

#### 4.2.3 지식 상세 화면

```
+------------------------------------------+
| < 뒤로가기                                |
+------------------------------------------+
| [편집] [삭제] [공유] [북마크] [PDF 변환]   |
+------------------------------------------+
| # 프로젝트 A 기술 문서                     |
| 작성자: 김철수 | 작성일: 2026-01-05         |
| 조회수: 234 | 좋아요: 15                   |
| 태그: #React #SpringBoot #PostgreSQL      |
+------------------------------------------+
| [본문 내용]                               |
| 마크다운 렌더링                            |
| 이미지, 차트, 코드 블록 등                 |
+------------------------------------------+
| 💬 댓글 (5)                               |
| [댓글 내용...]                            |
+------------------------------------------+
| 관련 지식                                 |
| - 유사한 지식 1                           |
| - 유사한 지식 2                           |
+------------------------------------------+
```

#### 4.2.4 지식 작성/수정 화면

```
+------------------------------------------+
| 지식 등록                                 |
+------------------------------------------+
| 제목: [_________________________________] |
| 카테고리: [기술 ▼]                        |
| 프로젝트: [검색...] ⊕                     |
+------------------------------------------+
| [편집] [미리보기]                         |
+------------------------------------------+
| # 제목 입력                               |
| 본문 작성...                              |
|                                          |
| [마크다운 에디터]                         |
|                                          |
+------------------------------------------+
| 태그: [React] [Spring] + 추가             |
| 공개범위: ◉ 전체공개 ○ 부서공개 ○ 비공개   |
| 유효기간: [2026-01-09] ~ [2027-01-09]    |
+------------------------------------------+
| 첨부파일: 파일을 드래그하세요             |
| [📎 file.pdf] [×]                        |
+------------------------------------------+
| [임시저장]           [취소] [등록]        |
+------------------------------------------+
```

### 4.3 반응형 디자인

모든 화면은 반응형으로 설계되어 데스크톱, 태블릿, 모바일에서 최적화된 경험을 제공합니다.

**브레이크포인트**
- Mobile: < 768px
- Tablet: 768px ~ 1024px
- Desktop: > 1024px

**모바일 최적화**
- 사이드바는 햄버거 메뉴로 숨김
- 검색바는 아이콘으로 축소, 클릭 시 전체 화면 검색
- 테이블은 카드 형태로 전환
- 폰트 크기와 터치 타겟 크기 확대

---

## 5. 기술 상세 설계

### 5.1 상태 관리 아키텍처

#### 5.1.1 Redux Toolkit 구조

**슬라이스 구성**
```
src/store/
├── slices/
│   ├── authSlice.ts          # 인증 상태
│   ├── knowledgeSlice.ts     # 지식 목록
│   ├── searchSlice.ts        # 검색 상태
│   ├── uiSlice.ts            # UI 상태 (테마, 사이드바 등)
│   └── userSlice.ts          # 사용자 정보
├── store.ts
└── hooks.ts                  # Typed hooks
```

**상태 구조 예시**
```typescript
interface RootState {
  auth: {
    isAuthenticated: boolean;
    user: User | null;
    accessToken: string | null;
    refreshToken: string | null;
  };
  knowledge: {
    items: Knowledge[];
    currentKnowledge: Knowledge | null;
    loading: boolean;
    error: string | null;
  };
  search: {
    query: string;
    results: SearchResult[];
    filters: SearchFilters;
    mode: 'chat' | 'search';
  };
  ui: {
    theme: 'light' | 'dark';
    sidebarOpen: boolean;
    notifications: Notification[];
  };
}
```

#### 5.1.2 React Query 통합

서버 상태는 React Query로 관리하여 캐싱, 동기화, 백그라운드 업데이트를 자동화합니다.

**쿼리 키 구조**
```typescript
// 쿼리 키 상수
export const queryKeys = {
  knowledge: {
    all: ['knowledge'] as const,
    lists: () => [...queryKeys.knowledge.all, 'list'] as const,
    list: (filters: string) => [...queryKeys.knowledge.lists(), filters] as const,
    details: () => [...queryKeys.knowledge.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.knowledge.details(), id] as const,
  },
  search: {
    all: ['search'] as const,
    query: (q: string) => [...queryKeys.search.all, q] as const,
  },
};
```

**사용 예시**
```typescript
// 지식 목록 조회
const { data, isLoading, error } = useQuery({
  queryKey: queryKeys.knowledge.list('all'),
  queryFn: () => api.getKnowledgeList(),
  staleTime: 5 * 60 * 1000, // 5분
});

// 지식 생성 (Mutation)
const mutation = useMutation({
  mutationFn: (newKnowledge: KnowledgeInput) => api.createKnowledge(newKnowledge),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.knowledge.lists() });
  },
});
```

### 5.2 API 통신 레이어

#### 5.2.1 Axios 인스턴스 설정

```typescript
import axios from 'axios';
import { store } from '@/store';
import { refreshToken, logout } from '@/store/slices/authSlice';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
});

// 요청 인터셉터 - Access Token 자동 추가
apiClient.interceptors.request.use(
  (config) => {
    const token = store.getState().auth.accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 응답 인터셉터 - Token 갱신 처리
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 401 에러 && 재시도 안 했으면 토큰 갱신
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        await store.dispatch(refreshToken()).unwrap();
        const newToken = store.getState().auth.accessToken;
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        store.dispatch(logout());
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
```

#### 5.2.2 API 서비스 모듈화

```typescript
// src/services/knowledgeService.ts
import { apiClient } from './apiClient';

export const knowledgeService = {
  // 목록 조회
  getList: async (params: KnowledgeListParams) => {
    const response = await apiClient.get('/api/v1/knowledge', { params });
    return response.data.data;
  },

  // 상세 조회
  getById: async (id: string) => {
    const response = await apiClient.get(`/api/v1/knowledge/${id}`);
    return response.data.data;
  },

  // 생성
  create: async (data: KnowledgeInput) => {
    const response = await apiClient.post('/api/v1/knowledge', data);
    return response.data.data;
  },

  // 수정
  update: async (id: string, data: Partial<KnowledgeInput>) => {
    const response = await apiClient.put(`/api/v1/knowledge/${id}`, data);
    return response.data.data;
  },

  // 삭제
  delete: async (id: string) => {
    await apiClient.delete(`/api/v1/knowledge/${id}`);
  },
};
```

### 5.3 WebSocket 통신 (채팅 모드)

#### 5.3.1 STOMP over WebSocket 설정

```typescript
import { Client, StompSubscription } from '@stomp/stompjs';
import SockJS from 'sockjs-client';

class ChatService {
  private client: Client | null = null;
  private subscription: StompSubscription | null = null;

  connect(conversationId: string, onMessage: (message: ChatMessage) => void) {
    this.client = new Client({
      webSocketFactory: () => new SockJS('/ws'),
      connectHeaders: {
        Authorization: `Bearer ${getAccessToken()}`,
      },
      onConnect: () => {
        this.subscription = this.client!.subscribe(
          `/topic/chat/${conversationId}`,
          (message) => {
            onMessage(JSON.parse(message.body));
          }
        );
      },
    });

    this.client.activate();
  }

  sendMessage(conversationId: string, message: string) {
    if (this.client?.connected) {
      this.client.publish({
        destination: `/app/chat/${conversationId}`,
        body: JSON.stringify({ message }),
      });
    }
  }

  disconnect() {
    this.subscription?.unsubscribe();
    this.client?.deactivate();
  }
}

export const chatService = new ChatService();
```

#### 5.3.2 채팅 컴포넌트 통합

```typescript
const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const conversationId = useConversationId();

  useEffect(() => {
    chatService.connect(conversationId, (message) => {
      setMessages((prev) => [...prev, message]);
    });

    return () => chatService.disconnect();
  }, [conversationId]);

  const handleSend = (text: string) => {
    chatService.sendMessage(conversationId, text);
  };

  return (
    <ChatUI messages={messages} onSend={handleSend} />
  );
};
```

### 5.4 파일 업로드 및 처리

#### 5.4.1 Multipart Upload

```typescript
const uploadKnowledge = async (data: KnowledgeFormData) => {
  const formData = new FormData();
  formData.append('title', data.title);
  formData.append('content', data.content);
  data.tags.forEach((tag) => formData.append('tags', tag));
  
  // 파일 첨부
  data.files.forEach((file) => {
    formData.append('files', file);
  });

  return apiClient.post('/api/v1/knowledge', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / (progressEvent.total || 1)
      );
      console.log(percentCompleted);
    },
  });
};
```

#### 5.4.2 드래그 앤 드롭

```typescript
const FileDropZone: React.FC<FileDropZoneProps> = ({ onFilesAdded }) => {
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    onFilesAdded(files);
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className="dropzone"
    >
      파일을 드래그하세요
    </div>
  );
};
```

### 5.5 렌더링 최적화

#### 5.5.1 코드 스플리팅

```typescript
import { lazy, Suspense } from 'react';

// 라우트별 코드 스플리팅
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Search = lazy(() => import('@/pages/Search'));
const KnowledgeDetail = lazy(() => import('@/pages/KnowledgeDetail'));

const App = () => (
  <Suspense fallback={<LoadingSpinner />}>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/search" element={<Search />} />
      <Route path="/knowledge/:id" element={<KnowledgeDetail />} />
    </Routes>
  </Suspense>
);
```

#### 5.5.2 가상화 (Virtualization)

대량의 검색 결과를 효율적으로 렌더링하기 위해 react-window를 사용합니다.

```typescript
import { FixedSizeList } from 'react-window';

const SearchResults: React.FC<{ results: SearchResult[] }> = ({ results }) => {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      <SearchResultCard data={results[index]} />
    </div>
  );

  return (
    <FixedSizeList
      height={600}
      itemCount={results.length}
      itemSize={120}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
};
```

---

## 6. 개발 환경 및 도구

### 6.1 Google Antigravity IDE 설정

Google Antigravity는 클라우드 기반 IDE로, Claude Code와 통합하여 AI 기반 개발 경험을 제공합니다.

#### 6.1.1 프로젝트 설정

**워크스페이스 생성**
1. Antigravity에서 새 워크스페이스 생성
2. Git 리포지토리 클론
3. Node.js 18+ 환경 설정
4. 확장 프로그램 설치:
   - ESLint
   - Prettier
   - TypeScript
   - Claude Code Extension

**환경 변수 설정**
Antigravity의 Secrets 관리 기능을 사용하여 환경 변수를 안전하게 저장합니다.

```bash
# .env.local (로컬 개발용)
VITE_API_BASE_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080/ws
VITE_OAUTH_CLIENT_ID=your_client_id
VITE_OAUTH_REDIRECT_URI=http://localhost:5173/callback
```

#### 6.1.2 Claude Code 통합

**Claude Code 활성화**
1. Antigravity에서 Claude Code 확장 설치
2. Anthropic API 키 설정
3. 프로젝트 컨텍스트 설정

**AI 기반 개발 워크플로우**

프론트엔드 컴포넌트 생성:
```
"검색 결과를 테이블로 표시하는 React 컴포넌트를 만들어줘.
- TypeScript 사용
- Material-UI Table 컴포넌트 활용
- 정렬, 페이지네이션 기능 포함
- 각 행 클릭 시 상세 페이지로 이동"
```

API 서비스 코드 생성:
```
"knowledgeService.ts에 검색 API 호출 함수 추가해줘.
- 파라미터: query, filters, page, size
- React Query와 통합 가능한 형태로
- 에러 핸들링 포함"
```

스타일링:
```
"이 컴포넌트에 Material-UI의 테마 시스템을 적용해서
다크 모드를 지원하도록 수정해줘"
```

### 6.2 개발 서버 실행

```bash
# 의존성 설치
npm install

# 개발 서버 시작
npm run dev

# 빌드
npm run build

# 프리뷰 (빌드 결과 확인)
npm run preview

# 테스트
npm run test

# 린트
npm run lint

# 타입 체크
npm run type-check
```

### 6.3 코드 품질 관리

#### 6.3.1 ESLint 설정

```javascript
// .eslintrc.cjs
module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'prettier',
  ],
  rules: {
    'react/react-in-jsx-scope': 'off',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  },
};
```

#### 6.3.2 Prettier 설정

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "arrowParens": "always"
}
```

#### 6.3.3 Husky & lint-staged

```json
// package.json
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{json,md}": ["prettier --write"]
  }
}
```

```bash
# .husky/pre-commit
npm run lint-staged
npm run type-check
```

---

## 7. 빌드 및 배포 전략

### 7.1 Docker 컨테이너화

#### 7.1.1 Dockerfile

```dockerfile
# 멀티 스테이지 빌드
FROM node:18-alpine AS builder

WORKDIR /app

# 의존성 설치
COPY package*.json ./
RUN npm ci

# 소스 복사 및 빌드
COPY . .
RUN npm run build

# 프로덕션 이미지
FROM nginx:alpine

# Nginx 설정
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 빌드 결과물 복사
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### 7.1.2 Nginx 설정

```nginx
# nginx.conf
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # SPA 라우팅 지원
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 프록시
    location /api {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 프록시
    location /ws {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 정적 파일 캐싱
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip 압축
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
```

### 7.2 Docker Compose 설정

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 프론트엔드
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    environment:
      - VITE_API_BASE_URL=http://localhost:8080
    depends_on:
      - backend
    networks:
      - knowledge-network

  # 백엔드 (SpringBoot)
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=prod
      - POSTGRES_HOST=postgres
      - NEO4J_URI=bolt://neo4j:7687
      - ELASTICSEARCH_HOST=elasticsearch
    depends_on:
      - postgres
      - neo4j
      - elasticsearch
    networks:
      - knowledge-network

  # PostgreSQL
  postgres:
    image: postgres:16
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=knowledge
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=secret
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - knowledge-network

  # Neo4j
  neo4j:
    image: neo4j:5.15
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
    volumes:
      - neo4j-data:/data
    networks:
      - knowledge-network

  # Elasticsearch
  elasticsearch:
    image: elasticsearch:8.11.0
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es-data:/usr/share/elasticsearch/data
    networks:
      - knowledge-network

volumes:
  postgres-data:
  neo4j-data:
  es-data:

networks:
  knowledge-network:
    driver: bridge
```

### 7.3 배포 전략

#### 7.3.1 일괄 배포

모든 서비스를 한 번에 시작:
```bash
# 전체 빌드 및 시작
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 상태 확인
docker-compose ps

# 전체 중지
docker-compose down
```

#### 7.3.2 개별 배포

특정 서비스만 재배포:
```bash
# 프론트엔드만 재빌드 및 재시작
docker-compose up -d --build frontend

# 백엔드만 재시작 (코드 변경 없이)
docker-compose restart backend

# 특정 서비스 로그만 확인
docker-compose logs -f frontend
```

#### 7.3.3 환경별 설정

```bash
# 개발 환경
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 프로덕션 환경
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up

# 테스트 환경
docker-compose -f docker-compose.yml -f docker-compose.test.yml up
```

### 7.4 CI/CD 파이프라인

#### 7.4.1 GitHub Actions 예시

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Build
        run: npm run build

      - name: Build Docker image
        run: docker build -t knowledge-frontend:latest .

      - name: Push to registry
        run: |
          docker tag knowledge-frontend:latest registry.example.com/knowledge-frontend:latest
          docker push registry.example.com/knowledge-frontend:latest

      - name: Deploy to server
        run: |
          ssh deploy@server "docker pull registry.example.com/knowledge-frontend:latest"
          ssh deploy@server "docker-compose up -d frontend"
```

---

## 8. 보안 및 성능 고려사항

### 8.1 보안

#### 8.1.1 XSS 방지

- React의 자동 이스케이핑 활용
- `dangerouslySetInnerHTML` 사용 시 DOMPurify로 sanitize
- CSP(Content Security Policy) 헤더 설정

```typescript
import DOMPurify from 'dompurify';

const SafeHTML: React.FC<{ html: string }> = ({ html }) => {
  const sanitized = DOMPurify.sanitize(html);
  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
};
```

#### 8.1.2 CSRF 방지

- SameSite 쿠키 설정
- CSRF 토큰 사용 (백엔드에서 발급)
- CORS 설정 엄격하게 관리

#### 8.1.3 인증 토큰 보안

- Access Token은 메모리에만 저장 (localStorage 사용 금지)
- Refresh Token은 HttpOnly 쿠키 사용
- HTTPS 강제

### 8.2 성능 최적화

#### 8.2.1 번들 크기 최적화

```javascript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@mui/material'],
          charts: ['recharts'],
        },
      },
    },
  },
});
```

#### 8.2.2 이미지 최적화

- WebP 포맷 사용
- Lazy loading
- 반응형 이미지 (srcset)
- CDN 활용

#### 8.2.3 캐싱 전략

- React Query의 staleTime과 cacheTime 적절히 설정
- Service Worker를 통한 오프라인 지원 (선택사항)
- HTTP 캐시 헤더 활용

---

## 9. 개발 로드맵

### Phase 1: 기반 구축 (4주)

**Week 1-2: 프로젝트 설정 및 기본 레이아웃**
- Vite 프로젝트 초기화
- TypeScript 설정
- MUI 설치 및 테마 설정
- 라우팅 구조 설계
- 레이아웃 컴포넌트 구현 (헤더, 사이드바, 푸터)

**Week 3-4: 인증 및 기본 기능**
- OAuth 로그인 통합
- JWT 토큰 관리
- 권한 기반 라우팅
- 대시보드 화면 구현

### Phase 2: 핵심 기능 개발 (6주)

**Week 5-6: 지식 관리 CRUD**
- 지식 목록 페이지
- 지식 상세 페이지
- 지식 작성 페이지 (마크다운 에디터)
- 지식 수정/삭제 기능

**Week 7-8: 검색 기능**
- 검색 모드 구현
- 채팅 모드 구현 (WebSocket)
- 필터 및 정렬 기능
- 검색 결과 렌더링

**Week 9-10: 개인화 페이지**
- 프로필 관리
- 내 지식 관리
- 북마크 기능
- 검색 기록 관리

### Phase 3: 고급 기능 및 최적화 (4주)

**Week 11-12: 문서 변환 및 시각화**
- 마크다운 렌더링 고도화
- Chart/SVG/Mermaid 렌더링
- 엑셀/PPT/PDF 변환 기능

**Week 13-14: 성능 최적화 및 테스트**
- 코드 스플리팅
- 가상화 적용
- 단위 테스트 작성
- E2E 테스트 작성

### Phase 4: 배포 준비 (2주)

**Week 15: Docker 및 배포 설정**
- Dockerfile 작성
- Docker Compose 설정
- CI/CD 파이프라인 구축

**Week 16: 최종 점검 및 문서화**
- 성능 벤치마킹
- 보안 점검
- 사용자 가이드 작성
- API 문서화

---

## 10. 테스트 전략

### 10.1 단위 테스트

**Vitest + React Testing Library**

```typescript
// SearchBar.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { SearchBar } from './SearchBar';

describe('SearchBar', () => {
  it('should call onSearch when enter is pressed', () => {
    const mockOnSearch = vi.fn();
    render(<SearchBar onSearch={mockOnSearch} />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '검색어' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 13 });

    expect(mockOnSearch).toHaveBeenCalledWith('검색어');
  });
});
```

### 10.2 통합 테스트

**API 모킹**

```typescript
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/v1/knowledge', (req, res, ctx) => {
    return res(ctx.json({ data: mockKnowledgeList }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### 10.3 E2E 테스트

**Playwright**

```typescript
// e2e/search.spec.ts
import { test, expect } from '@playwright/test';

test('should search and display results', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.click('[data-testid="search-mode-tab"]');
  await page.fill('[data-testid="search-input"]', 'React');
  await page.press('[data-testid="search-input"]', 'Enter');

  await expect(page.locator('[data-testid="search-result"]')).toHaveCount(5);
});
```

---

## 11. 모니터링 및 로깅

### 11.1 에러 추적

**Sentry 통합**

```typescript
import * as Sentry from '@sentry/react';

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  integrations: [new Sentry.BrowserTracing()],
  tracesSampleRate: 1.0,
});
```

### 11.2 사용자 행동 분석

**Google Analytics 또는 자체 분석 시스템**

```typescript
const trackEvent = (category: string, action: string, label?: string) => {
  if (window.gtag) {
    window.gtag('event', action, {
      event_category: category,
      event_label: label,
    });
  }
};

// 사용 예시
trackEvent('Search', 'query_submitted', searchQuery);
```

---

## 12. 결론

본 프론트엔드 시스템은 React와 TypeScript를 기반으로 현대적인 웹 개발 기술을 활용하여 구축됩니다. SpringBoot 백엔드와의 긴밀한 통합, OAuth 기반 보안, Docker를 통한 컨테이너화로 엔터프라이즈급 안정성을 확보합니다.

Google Antigravity IDE와 Claude Code를 활용한 AI 기반 개발 워크플로우를 통해 개발 생산성을 극대화하며, 철저한 테스트와 CI/CD 파이프라인으로 품질을 보장합니다.

사용자 중심의 직관적인 UI/UX, 강력한 검색 기능, 다양한 시각화 옵션을 통해 사내 지식 검색 시스템의 프론트엔드로서 충분한 가치를 제공할 것입니다.

향후 사용자 피드백을 지속적으로 수집하고 개선하여, 조직의 지식 관리 문화를 혁신하는 플랫폼으로 발전시킬 계획입니다.

---

**문서 작성 일자: 2026-01-09**
