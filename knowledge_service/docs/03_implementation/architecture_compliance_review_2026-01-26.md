# 아키텍처 정합성 검토 보고서

**날짜**: 2026-01-26
**검토자**: TechLead
**버전**: 1.0
**상태**: 완료

---

## 1. Executive Summary

### 종합 평가: **B 등급 (75/100점)**

| 평가 영역 | 점수 | 등급 | 요약 |
|----------|:----:|:----:|------|
| 인프라 구성 | 92/100 | A | Docker Compose 18개 컨테이너 거의 완벽 일치 |
| Gateway 레이어 | 88/100 | A | 설계서 대비 충실한 구현, 이중 인증 완료 |
| Backend 레이어 | 65/100 | C | 핵심 인증 구현 완료, 다수 기능 미구현 |
| AI Service 레이어 | 55/100 | D | 스켈레톤 수준, 핵심 파이프라인 미구현 |
| Frontend 레이어 | 70/100 | B | 기본 구조 완성, 주요 페이지 구현됨 |
| 데이터 레이어 | 78/100 | B | 스키마 존재하나 설계서와 스키마 차이 있음 |
| 기술 스택 | 90/100 | A | 대부분 설계서와 일치 |
| 보안 설정 | 82/100 | B | Keycloak + JWT 이중 인증 구현 완료 |

### 핵심 발견

- **강점**: 인프라 기반(Docker Compose, CI/CD, 보안 하드닝)이 매우 견고함
- **강점**: Gateway의 JWT 이중 인증(HS256 + RS256) 설계서 대비 완벽 구현
- **약점**: AI Service의 핵심 기능(Hybrid 검색, VIP 파이프라인, Gleaning)이 스켈레톤 수준
- **약점**: Backend의 Knowledge/Bookmark/Dashboard/Export 도메인 미구현
- **약점**: PostgreSQL 실제 스키마가 설계서의 ERD 스키마와 구조 차이 존재

---

## 2. 기술 스택 정합성

| 설계서 기술 | 설계 버전 | 실제 구현 | 실제 버전 | 상태 | 비고 |
|------------|----------|----------|----------|:----:|------|
| Python 3.11+ | 3.11 | pyproject.toml `^3.11` | 3.11+ | **일치** | |
| SpringBoot 3.x | 3.2+ | build.gradle `3.2.2` | 3.2.2 | **일치** | |
| Spring Cloud Gateway | 4.x | spring-cloud `2023.0.0` | 4.x | **일치** | |
| React 18 | 18 | package.json `^18.3.1` | 18.3 | **일치** | |
| PostgreSQL | 16+ | docker-compose `postgres:16-alpine` | 16 | **일치** | |
| Neo4j | 5.x | docker-compose `neo4j:5.15-community` | 5.15 | **일치** | |
| Elasticsearch | 8.x | docker-compose `8.11.0` | 8.11 | **일치** | |
| Redis | 7.x | docker-compose `redis:7.2-alpine` | 7.2 | **일치** | |
| MinIO | latest | docker-compose `minio/minio:latest` | latest | **일치** | |
| Keycloak | 23.0 | docker-compose `keycloak:23.0` | 23.0 | **일치** | |
| LangGraph | 1.0+ | pyproject.toml `^1.0.6` | 1.0+ | **일치** | 코드 미활용 |
| LangChain | 1.2+ | pyproject.toml `^1.2.3` | 1.2+ | **일치** | 코드 미활용 |
| DeepSeek V3.2 | V3.2 | config.py에 설정 존재 | V3.2 | **일치** | 코드 미활용 |
| BGE-M3 | - | pyproject.toml에 의존성 존재 | - | **일치** | 코드 미활용 |
| Resilience4j | 2.x | build.gradle `2.2.0` | 2.2 | **일치** | |
| Docling | 2.x | pyproject.toml `^2.60.0` | 2.60+ | **일치** | 코드 미활용 |
| Java | 17+ | build.gradle `sourceCompatibility = '17'` | 17 | **일치** | |
| Gradle | 8.x | gateway/backend 모두 Gradle | Groovy DSL | **차이** | 설계서: Kotlin DSL |

**기술 스택 정합률**: 17/18 = **94%**

**차이 사항**:
- **Gradle DSL**: 설계서는 Kotlin DSL(`build.gradle.kts`)을 명시하나, 실제 구현은 Groovy DSL(`build.gradle`) 사용. 기능 차이 없음.
- **모듈 구조**: 설계서는 Gradle 멀티 모듈(`platform-common`, `platform-domain`, `platform-api`, `platform-gateway`)을 명시하나, 실제로는 `gateway/`와 `backend/`가 독립 프로젝트로 분리됨. 설계서의 공통 모듈 공유 패턴 미적용.
- **패키지명**: 설계서는 `com.company.platform.*`을 명시하나, 실제는 `com.knowledge.gateway.*` / `com.knowledge.backend.*` 사용.

---

## 3. 아키텍처 레이어별 검토

### 3.1 인프라 레이어 (92/100)

#### Docker Compose 구성 vs 설계서

| 설계서 항목 | Docker Compose 구현 | 상태 | 비고 |
|------------|-------------------|:----:|------|
| 18개 컨테이너 | 19개 (init-db 포함) | **일치** | init-db는 init profile, 실질 18개 |
| 네트워크 4개 (frontend, backend, database, monitoring) | 4개 네트워크 정확히 일치 | **일치** | kp-frontend, kp-backend, kp-database, kp-monitoring |
| 볼륨 (데이터 영속화) | 10개 named volume + 4개 tmp volume | **일치** | postgresql, neo4j, es, redis, minio, prometheus, grafana, loki 등 |
| 헬스체크 설정 | 모든 서비스에 healthcheck 설정됨 | **일치** | |
| 리소스 제한 | 모든 서비스에 deploy.resources 설정 | **일치** | |
| 보안 하드닝 | no-new-privileges, security_opt 적용 | **일치** | read_only, cap_drop은 WSL2로 인해 주석 처리 |
| docker-compose.override.yml | 존재 | **일치** | 개발 환경 오버라이드 |
| docker-compose.wsl2.yml | 존재 (설계서 미명시) | **추가** | 설계서에 WSL2 가이드 추가(v2.3)와 일치 |

#### 네트워크 배치 정합성

| 네트워크 | 설계서 컨테이너 | 실제 구현 | 상태 |
|----------|---------------|----------|:----:|
| kp-frontend | nginx, frontend, api-gateway, keycloak, grafana | nginx(frontend), frontend(frontend), api-gateway(frontend+backend), keycloak(frontend+database), grafana(monitoring+frontend) | **일치** |
| kp-backend | api-gateway, backend, ai-service, prometheus, jaeger | api-gateway(frontend+backend), backend(backend+database), ai-service(backend+database), prometheus(monitoring+backend), jaeger(monitoring+backend) | **일치** |
| kp-database | backend, ai-service, keycloak, postgresql, keycloak-db, neo4j, elasticsearch, kibana, redis, minio, init-db | 모두 database 네트워크에 연결됨 + api-gateway도 database에 연결 (Redis 접근용) | **차이** | api-gateway가 설계서에는 database 미연결이나 실제로는 Redis 접근을 위해 연결됨 |
| kp-monitoring | prometheus, grafana, loki, promtail, jaeger, kibana | 동일 | **일치** |

#### 불일치 사항

1. **Minor**: api-gateway가 `database` 네트워크에 추가 연결됨 (Redis Rate Limiter 접근 목적). 설계서에는 명시되지 않았으나 합리적 변경.
2. **Minor**: WSL2 환경에서 보안 설정 일부(read_only, cap_drop) 주석 처리. 프로덕션 배포 시 활성화 필요.

---

### 3.2 Gateway 레이어 (88/100)

#### Spring Cloud Gateway 설정 vs 설계서

| 설계서 항목 | 실제 구현 | 상태 | 비고 |
|------------|----------|:----:|------|
| Spring Cloud Gateway 4.x | spring-cloud `2023.0.0` (Gateway 4.x) | **일치** | |
| JWT 이중 인증 (HS256 + RS256) | SecurityConfig.java에 두 체인 구현 | **일치** | Order 1: Auth (permitAll), Order 2: Default (HS256 + OAuth2 RS256) |
| Keycloak OAuth2 연동 | jwk-set-uri 설정 완료 | **일치** | |
| Rate Limiting (Redis) | RequestRateLimiter 필터 적용 | **일치** | |
| CircuitBreaker (Resilience4j) | 모든 라우트에 CircuitBreaker 적용 | **일치** | |
| Retry 패턴 | 라우트별 Retry 필터 설정 | **일치** | |
| CORS 설정 | corsConfigurationSource 빈 정의 | **일치** | |
| Fallback 패턴 | FallbackController 구현 | **일치** | |
| Logging Filter | LoggingFilter 구현 | **일치** | |
| Prometheus 메트릭 | actuator/prometheus 노출 | **일치** | |

#### API 라우팅 규칙 정합성

| 설계서 경로 | Gateway 라우팅 | 대상 서비스 | 상태 |
|------------|--------------|-----------|:----:|
| /api/v1/auth/** | auth-service-v1 | backend:8081 | **일치** |
| /api/v1/knowledge/** | knowledge-service | backend:8081 | **일치** |
| /api/v1/search/** | search-service | ai-service:8000 | **일치** |
| /api/v1/search/stream/** | search-service-stream | ai-service:8000 | **일치** |
| /api/v1/users/** | user-service | backend:8081 | **일치** |
| /internal/v1/** | internal-ai-service | ai-service:8000 | **일치** |
| /auth/** | keycloak | keycloak:8080 | **일치** |

**참고**: 설계서의 API 통합 설계서에서 Internal API는 `/internal/v1/*`로 정의. Gateway에서도 동일 패턴으로 라우팅 설정. 다만, 설계서에서 Internal API는 "내부 네트워크에서만 접근"으로 명시했으나, Gateway를 통해서도 접근 가능하게 설정됨 (TokenRelay 필터 적용).

#### 불일치 사항

1. **Minor**: `/api/auth/**` 경로가 추가로 존재 (v1 prefix 없음). 설계서에는 `/api/v1/auth/**`만 명시되어 있으나, 하위 호환성을 위한 추가 라우트로 판단됨.
2. **Minor**: `/ai/**` 레거시 라우트가 존재. 설계서에 명시되지 않은 추가 경로.
3. **Medium**: Internal API가 Gateway를 통해 외부에서도 접근 가능. 설계서에서는 "내부 네트워크에서만 접근"으로 제한 명시. 프로덕션에서는 Gateway에서 Internal API 라우트 제거 또는 IP 제한 필요.

---

### 3.3 Backend 레이어 (65/100)

#### SpringBoot 프로젝트 구조 vs 설계서

| 설계서 항목 | 실제 구현 | 상태 |
|------------|----------|:----:|
| Gradle 멀티 모듈 (4개 모듈) | 단일 모듈 (backend) | **차이** |
| Kotlin DSL | Groovy DSL | **차이** |
| Spring Data JPA | R2DBC (Reactive) 사용 | **차이** |
| MapStruct | 의존성 추가됨, 매퍼 미구현 | **미완** |
| Liquibase 마이그레이션 | 미구현 | **미구현** |
| Swagger/OpenAPI | 미구현 (springdoc 의존성 없음) | **미구현** |

#### API 엔드포인트 구현 현황

| 설계서 API 그룹 | 엔드포인트 수 (설계서) | 구현 현황 | 정합률 |
|----------------|:-------------------:|----------|:------:|
| /api/v1/auth/* | 5개 (login, token, refresh, logout, me) | 4개 (login, refresh, logout, me) | 80% |
| /api/v1/knowledge/* | 7개+ (CRUD, 검색, 카테고리) | 0개 | 0% |
| /api/v1/search/* | 3개 (hybrid, chat, stream) | 1개 (SearchController 존재, 기본 구현) | 33% |
| /api/v1/users/* | 4개+ (목록, 상세, 수정, 비밀번호) | 0개 | 0% |
| /api/v1/bookmarks/* | 4개 (생성, 목록, 삭제, 폴더) | 0개 | 0% |
| /api/v1/dashboard/* | 3개 (통계, 인기지식, 활동) | 0개 | 0% |
| /api/v1/export/* | 2개 (PDF, Excel) | 0개 | 0% |
| /api/v1/admin/* | 4개+ (사용자관리, 시스템, 감사) | 0개 | 0% |

**Backend API 전체 정합률**: 약 **15%** (5/32+ 엔드포인트)

#### 도메인 모델 구현 현황

| 설계서 Entity | 구현 여부 | 비고 |
|--------------|:--------:|------|
| User (auth_users) | **구현** | User.java (R2DBC 엔티티) |
| Knowledge (documents) | **미구현** | |
| Chunk | **미구현** | |
| Entity | **미구현** | |
| Category | **미구현** | |
| Project | **미구현** | |
| Bookmark | **미구현** | |
| SearchHistory | **미구현** | |

#### 주요 차이 사항

1. **Critical**: 설계서에서 Spring Data JPA를 명시했으나, 실제로는 R2DBC(Reactive)를 사용. application.yml에 `spring.r2dbc.url` 설정 및 `spring-boot-starter-data-r2dbc` 의존성 사용. 이는 의도적 아키텍처 결정이나 설계서 업데이트 필요.
2. **Major**: Knowledge 도메인 전체(CRUD, 검색, 카테고리)가 미구현. Sprint 02에서 인증만 완료한 상태.
3. **Major**: Liquibase DB 마이그레이션 미구현 (설계서 22장 명시).
4. **Minor**: Swagger/OpenAPI 문서 자동 생성 미구현 (설계서에 `springdoc-openapi` 명시).

---

### 3.4 AI Service 레이어 (55/100)

#### FastAPI 구현 현황 vs 설계서

| 설계서 항목 | 실제 구현 | 상태 |
|------------|----------|:----:|
| FastAPI 앱 구조 | main.py + create_app() 패턴 | **일치** |
| 환경 설정 (pydantic-settings) | config.py Settings 클래스 | **일치** |
| 예외 처리 | KnowledgeServiceError 정의 | **일치** |
| 로깅 모듈 | core/logging.py | **일치** |
| API v1 prefix | `/api/v1` | **일치** |

#### API 엔드포인트 구현 현황

| 설계서 Internal API | 라우터 파일 존재 | 구현 수준 | 상태 |
|--------------------|:--------------:|----------|:----:|
| /api/v1/search/hybrid | search.py | 스켈레톤 (빈 결과 반환) | **미완** |
| /api/v1/search/chat | search.py | 스켈레톤 (VIP agent 호출 시도) | **미완** |
| /api/v1/search/chat/stream | search.py | 스켈레톤 (더미 SSE) | **미완** |
| /api/v1/extract/entities | extract.py | 파일 존재 | **미완** |
| /api/v1/extract/metadata | extract.py | 파일 존재 | **미완** |
| /api/v1/embed | embed.py | 파일 존재 | **미완** |
| /api/v1/embed/batch | embed.py | 파일 존재 | **미완** |
| /api/v1/documents | documents.py | 파일 존재 | **미완** |
| /health | health.py | 기본 구현 | **구현** |
| /api/v1/auth | auth.py | 기본 구현 | **구현** |

#### VIP 파이프라인 구현 현황

| 설계서 기능 | 구현 파일 | 구현 수준 | 상태 |
|------------|----------|----------|:----:|
| VIP 3단계 (Value/Intelligent/Planning) | agents/vip_agent.py, agents/state.py | 기본 구조 존재 | **미완** |
| Stage 1: 엔티티 추출 | 미구현 | - | **미구현** |
| Stage 2: 오케스트레이션 | 미구현 | - | **미구현** |
| Stage 3: 답변 합성 | 미구현 | - | **미구현** |
| Gleaning (다중 추출) | 미구현 | - | **미구현** |
| ReAct Agent | 미구현 | - | **미구현** |
| Hybrid Search (ES + Neo4j) | rag/retriever.py 존재 | 스켈레톤 | **미완** |
| RRF 결과 융합 | 미구현 | - | **미구현** |
| BGE-M3 임베딩 | rag/embedder.py 존재 | 스켈레톤 | **미완** |
| ETL 파이프라인 (Docling) | etl/parser.py, etl/docling_adapter.py | 기본 구조 | **미완** |
| LLM 서비스 (DeepSeek) | services/llm_service.py | 기본 구조 | **미완** |

#### 설정값 정합성

| 설계서 설정 | config.py 설정 | 상태 |
|------------|--------------|:----:|
| chunk_size: 600 | chunk_size: 600 | **일치** |
| max_gleanings: 1 | max_gleanings: 1 | **일치** |
| embedding_dimension: 1024 | embedding_dimension: 1024 | **일치** |
| retrieval_top_k: 10 | retrieval_top_k: 10 | **일치** |
| rrf_k: 60 | rrf_k: 60 | **일치** |
| deepseek-chat 모델 | deepseek_chat_model: deepseek-chat | **일치** |
| deepseek-reasoner 모델 | deepseek_reasoner_model: deepseek-reasoner | **일치** |

**AI Service 설정 정합률**: **100%** (설정값은 모두 설계서와 일치)

---

### 3.5 Frontend 레이어 (70/100)

#### React 프로젝트 구성 vs 설계서

| 설계서 항목 | 실제 구현 | 상태 |
|------------|----------|:----:|
| React 18 | react `^18.3.1` | **일치** |
| TypeScript | tsconfig.json 존재 | **일치** |
| Vite | vite `^5.4.10` | **일치** |
| React Router | react-router-dom `^6.28.0` | **일치** |
| Redux Toolkit | @reduxjs/toolkit `^2.3.0` | **일치** |
| React Query | @tanstack/react-query `^5.59.20` | **일치** |
| MUI | @mui/material `^6.1.6` | **일치** |
| Tailwind CSS | tailwindcss `^3.4.17` | **일치** |
| Headless UI | @headlessui/react `^2.2.9` | **일치** |
| Keycloak-js | keycloak-js `^26.2.2` | **일치** |
| Axios | axios `^1.7.7` | **일치** |
| Playwright (E2E) | @playwright/test `^1.58.0` | **일치** |

#### 페이지/컴포넌트 구현 현황

| 설계서 페이지 | 구현 파일 | 상태 |
|-------------|----------|:----:|
| 로그인 페이지 | LoginPage.tsx, LoginForm.tsx | **구현** |
| 대시보드 | DashboardPage.tsx | **구현** |
| 검색 페이지 | SearchPage.tsx, ChatSearch.tsx, KeywordSearch.tsx | **구현** |
| 지식 목록/상세 | KnowledgePage.tsx | **구현** |
| 404 페이지 | NotFoundPage.tsx | **구현** |
| 공통 레이아웃 | Header.tsx, Sidebar.tsx, MainLayout.tsx | **구현** |
| 북마크 페이지 | 미구현 | **미구현** |
| 사용자 프로필 | 미구현 | **미구현** |
| 관리자 페이지 | 미구현 | **미구현** |
| 문서 업로드 | 미구현 | **미구현** |

#### 인프라 연동

| 항목 | 상태 |
|------|:----:|
| Keycloak 인증 연동 | KeycloakProvider.tsx, ProtectedRoute.tsx 구현 |
| Direct Login (HS256) | useDirectAuth.ts 구현 |
| API 서비스 레이어 | authService.ts, searchService.ts, knowledgeService.ts 구현 |
| 상태 관리 (Redux) | authSlice.ts, searchSlice.ts, uiSlice.ts 구현 |

---

### 3.6 데이터 레이어 (78/100)

#### PostgreSQL 스키마 비교

| 설계서 ERD 테이블 | 실제 schema.sql 테이블 | 상태 | 비고 |
|-----------------|---------------------|:----:|------|
| documents | knowledge_master | **차이** | 테이블명/컬럼명 다름 |
| chunks | knowledge_chunks | **차이** | 테이블명 다름, chunk_id UUID 일치 |
| entities | extracted_entities | **차이** | 테이블명/구조 다름 |
| entity_relationships | (extracted_entities 내) | **차이** | 별도 테이블 아닌 엔티티 테이블 내 |
| projects | projects | **일치** | 구조 유사 |
| persons | users | **차이** | 테이블명/구조 다름 |
| categories | (미구현) | **미구현** | 설계서 v2.5에 추가된 계층형 카테고리 |
| document_categories | (미구현) | **미구현** | 설계서 v2.5에 추가 |
| document_entities | (별도 없음) | **차이** | extracted_entities에 통합 |
| auth_users | auth_users | **추가** | 설계서 ERD에 없으나 인증용 추가 |

**분석**: PostgreSQL 스키마는 두 가지 버전이 공존.
- **설계서 ERD** (hybrid_rag_platform_detailed_design.md 섹션 4.1): `documents`, `chunks`, `entities`, `categories` 등 UUID PK 사용
- **실제 schema.sql**: `knowledge_master`, `knowledge_chunks`, `extracted_entities` 등 SERIAL PK 사용

이는 초기 구현 스키마(Phase 3 이전)와 설계서 정규화 스키마가 동기화되지 않은 것으로 판단됨. 설계서가 나중에 정비되면서 테이블명과 PK 전략이 변경되었으나 실제 SQL 파일은 업데이트되지 않음.

#### Elasticsearch 인덱스 매핑 비교

| 설계서 필드 | 실제 mappings.json | 상태 | 비고 |
|------------|-------------------|:----:|------|
| chunk_id (keyword) | metadata.chunk_id (keyword) | **차이** | 위치 다름 (루트 vs metadata 내부) |
| document_id (keyword) | metadata.knowledge_id (integer) | **차이** | 필드명/타입 다름 |
| text (korean_analyzer) | text (standard, 한국어는 ngram) | **차이** | nori_tokenizer 미사용 |
| dense_vector (1024) | vector_field (dense_vector, 1024) | **차이** | 필드명 다름 |
| sparse_vector | (미구현) | **미구현** | 설계서 명시 sparse_vector 미포함 |
| metadata.categories | (미구현) | **미구현** | 계층형 카테고리 필드 없음 |
| metadata.summary | metadata.summary (text) | **일치** | |
| metadata.document_type | metadata.document_type (keyword) | **일치** | |
| metadata.project_name | metadata.project_name (keyword) | **일치** | |
| metadata.valid_start_date | metadata.valid_start_date (date) | **일치** | |
| metadata.valid_end_date | metadata.valid_end_date (date) | **일치** | |
| metadata.entities.persons | metadata.entities.persons (keyword) | **일치** | |
| metadata.entities.technologies | metadata.entities.technologies (keyword) | **일치** | |
| metadata.neo4j_entity_ids | (미구현) | **미구현** | |
| metadata.neo4j_community_id | (미구현) | **미구현** | |

**분석**: Elasticsearch 매핑에서 가장 큰 차이는 (1) 한국어 분석기가 nori 대신 ngram/standard 사용, (2) dense_vector 필드명이 `vector_field`로 다름, (3) sparse_vector 미구현. 이는 ES 인덱스가 초기 프로토타입 수준에서 정지되어 있음을 의미.

#### Neo4j 스키마

Neo4j 스키마 파일(`infrastructure/database/neo4j/schema.cypher`)이 존재하며, 설계서의 노드/관계 타입(Entity, TextUnit, Community, Document)과 비교 필요하나, 실제 데이터 적재 코드는 미구현 상태.

---

## 4. 정합성 매트릭스

| 영역 | 설계 항목 수 | 구현 완료 | 미구현 | 불일치 | 정합률 |
|------|:----------:|:--------:|:------:|:------:|:------:|
| 기술 스택 | 18 | 17 | 0 | 1 | **94%** |
| 인프라 (Docker) | 22 | 21 | 0 | 1 | **95%** |
| Gateway 라우팅 | 10 | 10 | 0 | 0 | **100%** |
| Gateway 보안 | 8 | 8 | 0 | 0 | **100%** |
| Backend API | 32+ | 5 | 27+ | 0 | **15%** |
| Backend 도메인 | 8 | 1 | 7 | 0 | **12%** |
| AI Service API | 10 | 2 | 0 | 8 (스켈레톤) | **20%** |
| AI Service 핵심 | 11 | 0 | 11 | 0 | **0%** |
| Frontend 페이지 | 10 | 6 | 4 | 0 | **60%** |
| PostgreSQL 스키마 | 10 | 5 | 2 | 3 | **50%** |
| ES 매핑 | 15 | 8 | 4 | 3 | **53%** |
| CI/CD | 5 | 7 | 0 | 0 | **100%+** |

**전체 정합률**: 약 **55%** (설계서의 전체 스펙 대비 구현 완료 비율)

---

## 5. 주요 불일치 사항

### 5.1 Critical (즉시 조치 필요)

| # | 영역 | 불일치 내용 | 영향도 | 권장 조치 |
|---|------|-----------|--------|----------|
| C1 | 데이터 | PostgreSQL 실제 스키마(knowledge_master, SERIAL PK)가 설계서 ERD(documents, UUID PK)와 불일치 | 전체 시스템 | 설계서 또는 스키마 중 하나를 기준으로 통일. 권장: 설계서 ERD 기준으로 schema.sql 마이그레이션 |
| C2 | 데이터 | ES 매핑의 dense_vector 필드명(vector_field)이 설계서(dense_vector)와 불일치 | AI Service 검색 | ES 매핑을 설계서 기준으로 업데이트 |
| C3 | 보안 | Internal API(/internal/v1/**)가 Gateway를 통해 외부 노출 가능 | 보안 위험 | 프로덕션에서 Internal API 라우트 제거 또는 IP 화이트리스트 적용 |

### 5.2 Major (스프린트 내 조치 필요)

| # | 영역 | 불일치 내용 | 영향도 | 권장 조치 |
|---|------|-----------|--------|----------|
| M1 | Backend | JPA 대신 R2DBC 사용 - 설계서 업데이트 필요 | 설계 일관성 | backend_detailed_design.md 섹션 7-8을 R2DBC 기반으로 업데이트 |
| M2 | Backend | Gradle 멀티 모듈 미적용 (설계서: 4개 모듈) | 코드 재사용 | 프로젝트 규모가 커지면 모듈 분리 고려. 현재는 단일 모듈로도 충분 |
| M3 | 데이터 | ES 매핑에 nori 한국어 분석기 미적용 (설계서 명시) | 검색 품질 | nori 플러그인 설치 및 매핑 업데이트 |
| M4 | 데이터 | ES 매핑에 sparse_vector 필드 미구현 | Hybrid 검색 | BGE-M3 Sparse Vector 지원 추가 |
| M5 | AI | VIP 파이프라인 전체 미구현 | 핵심 기능 | Sprint 03-04에서 구현 예정으로 추정 |
| M6 | 데이터 | categories/document_categories 테이블 미구현 | 패싯 검색 | 설계서 v2.5에 추가된 기능, 스키마 마이그레이션 필요 |

### 5.3 Minor (개선 권장)

| # | 영역 | 불일치 내용 | 권장 조치 |
|---|------|-----------|----------|
| m1 | Gateway | `/api/auth/**` 비표준 라우트 존재 | v1 prefix 통일 또는 명시적 deprecated 표시 |
| m2 | Gateway | `/ai/**` 레거시 라우트 존재 | 필요 없으면 제거 |
| m3 | Backend | Gradle Kotlin DSL 대신 Groovy DSL 사용 | 기능 차이 없음, 설계서 업데이트 또는 Kotlin DSL 전환 |
| m4 | Backend | 패키지명 `com.knowledge.*` (설계서: `com.company.platform.*`) | 설계서 업데이트 |
| m5 | AI | API prefix가 `/api/v1`이나 Internal API는 설계서 기준 `/internal/v1` | 현재 AI Service 라우터가 `/api/v1` 하위에 등록됨. Internal 전용 라우터 분리 필요 |
| m6 | Frontend | 북마크, 사용자 프로필, 관리자 페이지 미구현 | 후속 Sprint에서 구현 |

---

## 6. 권장 사항

### 우선순위 1 (즉시 - 현재 Sprint)

1. **[C1] PostgreSQL 스키마 통일**
   - 설계서 ERD를 기준으로 `schema.sql` 마이그레이션 스크립트 작성
   - 또는 현행 `schema.sql`을 기준으로 설계서 ERD 업데이트
   - 권장: Liquibase 도입하여 스키마 버전 관리 시작

2. **[C3] Internal API 보안 강화**
   - Gateway의 `/internal/v1/**` 라우트에 IP 제한 또는 API Key 필수 적용
   - 프로덕션 배포 전 반드시 조치

3. **[M1] 설계서 업데이트 - R2DBC 반영**
   - backend_detailed_design.md에 R2DBC 사용 결정 사항을 ADR로 기록
   - JPA 관련 코드 예시를 R2DBC 패턴으로 업데이트

### 우선순위 2 (다음 Sprint)

4. **[C2/M3/M4] Elasticsearch 매핑 현행화**
   - dense_vector 필드명을 설계서와 통일
   - nori 한국어 분석기 적용
   - sparse_vector 필드 추가
   - 매핑 변경 시 인덱스 재생성 필요

5. **[M5] AI Service 핵심 기능 구현**
   - Hybrid Search (ES knn + Neo4j Cypher)
   - VIP Stage 1: 엔티티 추출
   - BGE-M3 임베딩 생성

6. **[M6] 카테고리 스키마 추가**
   - categories, document_categories 테이블 생성
   - ES 매핑에 categories 필드 추가

### 우선순위 3 (장기)

7. **Backend Knowledge 도메인 구현**
   - KnowledgeController, KnowledgeService, KnowledgeRepository
   - 문서 CRUD + 검색 연동

8. **Gradle 멀티 모듈 전환 검토**
   - 프로젝트 규모 확대 시 platform-common, platform-domain 분리
   - 현재 단일 모듈로 충분하므로 급하지 않음

9. **Swagger/OpenAPI 문서 자동 생성**
   - springdoc-openapi 의존성 추가
   - 컨트롤러에 OpenAPI 어노테이션 적용

---

## 7. 결론

### 프로젝트 현재 상태 분석

프로젝트는 **Phase 3 구현 35% 진행** 상태로, 인프라 기반과 인증 레이어가 견고하게 구축되어 있으나, 핵심 비즈니스 로직(Knowledge CRUD, Hybrid 검색, VIP 파이프라인)은 대부분 미구현 상태입니다.

### 긍정적 측면

1. **인프라 완성도 높음**: Docker Compose 18개 컨테이너가 설계서와 거의 완벽하게 일치하며, 보안 하드닝, 헬스체크, 리소스 제한이 모두 적용됨
2. **인증 아키텍처 우수**: JWT 이중 인증(HS256 Self-issued + RS256 Keycloak)이 Gateway와 Backend 양측에서 완벽 구현됨
3. **기술 스택 일치율 94%**: 설계서에 명시된 대부분의 기술이 올바른 버전으로 적용됨
4. **CI/CD 파이프라인 완비**: 7개 GitHub Actions 워크플로우 (ci, cd, code-quality, docker-build, docker-compose-validate, e2e-test, pr-build)
5. **설정값 정합성 100%**: AI Service의 RAG 관련 설정(chunk_size, max_gleanings, embedding_dimension 등)이 설계서와 정확히 일치

### 주의사항

1. **PostgreSQL 스키마 이중화**: 설계서 ERD와 실제 SQL 스키마가 서로 다른 테이블명/구조를 사용하여 혼란 가능. 조기 통일 필요
2. **AI Service 핵심 기능 부재**: 프로젝트의 핵심 가치인 Hybrid RAG 파이프라인이 스켈레톤 수준. Sprint 우선순위 최상위 배치 권장
3. **Internal API 외부 노출**: 보안 설계서에서 "내부 네트워크 전용"으로 명시된 API가 Gateway를 통해 접근 가능한 상태

### 최종 판단

전체적으로 **설계 품질과 인프라 기반은 A등급**이나, **핵심 기능 구현율이 낮아 종합 B등급**으로 평가합니다. 현재 Sprint 02까지 완료된 5/35 SP 진행률(14%)과 비례하는 구현 상태이며, 설계서가 매우 상세하게 작성되어 있어 후속 구현의 방향성은 명확합니다.

---

**검토 완료일**: 2026-01-26
**검토자**: TechLead Agent
**다음 리뷰 예정**: Sprint 03 완료 시점
