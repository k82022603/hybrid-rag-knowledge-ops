# 에러 코드 및 공통 코드 표준

**프로젝트**: Hybrid RAG Knowledge Operations Platform
**버전**: 1.2
**작성일**: 2026-01-16
**수정일**: 2026-01-22
**작성자**: Claude AI Architect

---

## 목차

1. [개요](#1-개요)
2. [에러 코드 체계](#2-에러-코드-체계)
3. [에러 코드 카탈로그](#3-에러-코드-카탈로그)
4. [에러 응답 표준](#4-에러-응답-표준)
5. [공통 코드 정의](#5-공통-코드-정의)
6. [코드 관리 방법](#6-코드-관리-방법)
7. [모니터링 연계](#7-모니터링-연계)
8. [구현 가이드](#8-구현-가이드)

---

## 1. 개요

### 1.1 목적

본 문서는 시스템 전체에서 사용하는 에러 코드와 공통 코드의 표준을 정의합니다.

**목표**:
- 일관된 에러 응답 형식 제공
- 에러 원인 신속 파악 (코드만으로 조회 가능)
- 모니터링/알림 시스템 연계
- 클라이언트 에러 처리 단순화

### 1.2 적용 범위

| 서비스 | 적용 대상 |
|--------|-----------|
| Frontend | 에러 표시, 사용자 메시지 |
| Backend API | REST API 응답 |
| AI Service | 내부 API 응답 |
| 모니터링 | 메트릭 레이블, 알림 |

### 1.3 용어 정의

| 용어 | 정의 |
|------|------|
| 에러 코드 | 에러를 고유하게 식별하는 코드 |
| 공통 코드 | 상태, 구분 값 등 시스템 전체에서 사용하는 코드 |
| 메시지 키 | 다국어 메시지 조회용 키 |

---

## 2. 에러 코드 체계

### 2.1 코드 형식

```
[서비스][카테고리][순번]

예시: AUTH001, DOC002, RAG101
```

| 구성 요소 | 형식 | 설명 |
|-----------|------|------|
| 서비스 | 2-4자 영문 | 에러 발생 서비스 |
| 카테고리 | - | 서비스 코드에 포함 |
| 순번 | 3자리 숫자 | 카테고리 내 순번 |

### 2.2 서비스 코드

| 코드 | 서비스 | 설명 |
|------|--------|------|
| `SYS` | System | 시스템 공통 |
| `AUTH` | Authentication | 인증/인가 |
| `USER` | User | 사용자 관리 |
| `DOC` | Document | 문서 관리 |
| `SRCH` | Search | 검색 |
| `RAG` | RAG | RAG 파이프라인 |
| `EMB` | Embedding | 임베딩 |
| `GRAPH` | Graph | 그래프 DB |
| `LLM` | LLM | LLM 연동 |
| `SYNC` | Sync | 데이터 동기화 |
| `FILE` | File | 파일 처리 |
| `EXT` | External | 외부 시스템 |

### 2.3 HTTP 상태 코드 매핑

| 에러 유형 | HTTP 상태 | 에러 코드 범위 |
|-----------|-----------|----------------|
| 클라이언트 오류 (요청) | 400 | xxx001-099 |
| 인증/인가 오류 | 401, 403 | AUTH001-099 |
| 리소스 없음 | 404 | xxx100-199 |
| 충돌/제약 위반 | 409 | xxx200-299 |
| 서버 내부 오류 | 500 | xxx300-399 |
| 외부 서비스 오류 | 502, 503 | xxx400-499 |
| 타임아웃 | 504 | xxx500-599 |

---

## 3. 에러 코드 카탈로그

### 3.1 시스템 공통 (SYS)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `SYS001` | 400 | 잘못된 요청입니다 | 요청 형식 오류 | 요청 파라미터 확인 |
| `SYS002` | 400 | 필수 파라미터가 누락되었습니다 | 필수 값 미입력 | 필수 필드 입력 |
| `SYS003` | 400 | 파라미터 형식이 올바르지 않습니다 | 타입/형식 오류 | 데이터 형식 확인 |
| `SYS004` | 400 | 허용되지 않는 값입니다 | 유효성 검증 실패 | 허용 값 확인 |
| `SYS005` | 400 | 요청 크기가 초과되었습니다 | Payload 크기 초과 | 요청 크기 축소 |
| `SYS100` | 404 | 요청한 리소스를 찾을 수 없습니다 | 일반 404 | URL 확인 |
| `SYS101` | 404 | API 엔드포인트가 존재하지 않습니다 | 잘못된 API 경로 | API 문서 확인 |
| `SYS300` | 500 | 내부 서버 오류가 발생했습니다 | 예상치 못한 오류 | 로그 확인, 재시도 |
| `SYS301` | 500 | 데이터베이스 오류가 발생했습니다 | DB 연결/쿼리 오류 | DBA 확인 |
| `SYS302` | 500 | 설정 오류가 발생했습니다 | 환경 설정 문제 | 설정 파일 확인 |
| `SYS400` | 503 | 서비스가 일시적으로 사용할 수 없습니다 | 서비스 장애 | 잠시 후 재시도 |
| `SYS500` | 504 | 요청 처리 시간이 초과되었습니다 | 타임아웃 | 요청 최적화, 재시도 |

---

### 3.2 인증/인가 (AUTH)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `AUTH001` | 401 | 인증이 필요합니다 | 토큰 없음 | 로그인 필요 |
| `AUTH002` | 401 | 인증 토큰이 만료되었습니다 | 토큰 만료 | 토큰 갱신 |
| `AUTH003` | 401 | 유효하지 않은 인증 토큰입니다 | 토큰 검증 실패 | 재로그인 |
| `AUTH004` | 401 | 잘못된 자격 증명입니다 | ID/PW 오류 | 자격 증명 확인 |
| `AUTH005` | 401 | 계정이 잠겨있습니다 | Brute Force 잠금 | 관리자 문의 |
| `AUTH006` | 401 | 비활성화된 계정입니다 | 계정 비활성화 | 관리자 문의 |
| `AUTH010` | 403 | 접근 권한이 없습니다 | 권한 부족 | 권한 요청 |
| `AUTH011` | 403 | 해당 리소스에 대한 권한이 없습니다 | 리소스 접근 제한 | 소유자/관리자 문의 |
| `AUTH012` | 403 | 해당 작업을 수행할 권한이 없습니다 | 작업 권한 부족 | 역할 확인 |
| `AUTH020` | 400 | 세션이 만료되었습니다 | 세션 타임아웃 | 재로그인 |
| `AUTH021` | 400 | 중복 로그인이 감지되었습니다 | 다중 세션 | 다른 세션 종료 |
| `AUTH030` | 429 | 로그인 시도 횟수를 초과했습니다 | Rate Limit | 대기 후 재시도 |

---

### 3.3 사용자 관리 (USER)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `USER001` | 400 | 잘못된 사용자 정보입니다 | 입력값 오류 | 입력 형식 확인 |
| `USER002` | 400 | 비밀번호 형식이 올바르지 않습니다 | 비밀번호 정책 위반 | 정책 확인 |
| `USER003` | 400 | 이메일 형식이 올바르지 않습니다 | 이메일 형식 오류 | 이메일 확인 |
| `USER100` | 404 | 사용자를 찾을 수 없습니다 | 존재하지 않는 사용자 | ID 확인 |
| `USER200` | 409 | 이미 존재하는 사용자 ID입니다 | 중복 ID | 다른 ID 사용 |
| `USER201` | 409 | 이미 등록된 이메일입니다 | 중복 이메일 | 이메일 확인 |
| `USER300` | 500 | 사용자 정보 처리 중 오류가 발생했습니다 | 내부 오류 | 재시도, 관리자 문의 |

---

### 3.4 문서 관리 (DOC)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `DOC001` | 400 | 잘못된 문서 정보입니다 | 입력값 오류 | 입력 확인 |
| `DOC002` | 400 | 지원하지 않는 파일 형식입니다 | 파일 타입 제한 | 지원 형식 확인 |
| `DOC003` | 400 | 파일 크기가 초과되었습니다 | 크기 제한 초과 | 파일 크기 축소 |
| `DOC004` | 400 | 문서 제목이 너무 깁니다 | 제목 길이 초과 | 제목 축소 |
| `DOC005` | 400 | 유효기간이 올바르지 않습니다 | 날짜 형식/범위 오류 | 날짜 확인 |
| `DOC100` | 404 | 문서를 찾을 수 없습니다 | 존재하지 않는 문서 | 문서 ID 확인 |
| `DOC101` | 404 | 삭제된 문서입니다 | Soft Delete된 문서 | 복구 또는 다른 문서 |
| `DOC102` | 404 | 만료된 문서입니다 | 유효기간 만료 | 최신 버전 확인 |
| `DOC200` | 409 | 문서가 이미 존재합니다 | 중복 문서 | 기존 문서 업데이트 |
| `DOC201` | 409 | 동시 수정이 감지되었습니다 | Optimistic Lock | 새로고침 후 재시도 |
| `DOC300` | 500 | 문서 처리 중 오류가 발생했습니다 | 내부 오류 | 재시도 |
| `DOC301` | 500 | 문서 파싱에 실패했습니다 | Docling 오류 | 파일 형식 확인 |
| `DOC302` | 500 | 문서 저장에 실패했습니다 | 저장 오류 | 재시도 |

---

### 3.5 검색 (SRCH)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `SRCH001` | 400 | 검색어가 필요합니다 | 빈 검색어 | 검색어 입력 |
| `SRCH002` | 400 | 검색어가 너무 짧습니다 | 최소 길이 미달 | 2자 이상 입력 |
| `SRCH003` | 400 | 검색어가 너무 깁니다 | 최대 길이 초과 | 검색어 축소 |
| `SRCH004` | 400 | 잘못된 검색 필터입니다 | 필터 형식 오류 | 필터 조건 확인 |
| `SRCH005` | 400 | 잘못된 정렬 조건입니다 | 정렬 필드 오류 | 정렬 조건 확인 |
| `SRCH100` | 404 | 검색 결과가 없습니다 | 결과 0건 | 검색어 변경 |
| `SRCH300` | 500 | 검색 처리 중 오류가 발생했습니다 | 내부 오류 | 재시도 |
| `SRCH301` | 500 | Elasticsearch 오류가 발생했습니다 | ES 연결/쿼리 오류 | 인프라 확인 |
| `SRCH500` | 504 | 검색 시간이 초과되었습니다 | 검색 타임아웃 | 검색 조건 단순화 |

---

### 3.6 RAG 파이프라인 (RAG)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `RAG001` | 400 | 질문이 필요합니다 | 빈 질문 | 질문 입력 |
| `RAG002` | 400 | 질문이 너무 깁니다 | 질문 길이 초과 | 질문 축소 |
| `RAG003` | 400 | 잘못된 채팅 세션입니다 | 세션 ID 오류 | 새 세션 시작 |
| `RAG100` | 404 | 관련 문서를 찾을 수 없습니다 | 검색 결과 없음 | 다른 질문 시도 |
| `RAG300` | 500 | 답변 생성 중 오류가 발생했습니다 | 파이프라인 오류 | 재시도 |
| `RAG301` | 500 | 컨텍스트 생성에 실패했습니다 | 검색 실패 | 재시도 |
| `RAG302` | 500 | 답변 합성에 실패했습니다 | LLM 처리 실패 | 재시도 |
| `RAG400` | 503 | RAG 서비스를 사용할 수 없습니다 | 서비스 장애 | 잠시 후 재시도 |
| `RAG500` | 504 | 답변 생성 시간이 초과되었습니다 | 처리 타임아웃 | 질문 단순화 |

---

### 3.7 임베딩 (EMB)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `EMB001` | 400 | 임베딩할 텍스트가 필요합니다 | 빈 텍스트 | 텍스트 입력 |
| `EMB002` | 400 | 텍스트가 너무 깁니다 | 최대 토큰 초과 | 텍스트 분할 |
| `EMB300` | 500 | 임베딩 생성에 실패했습니다 | 모델 오류 | 재시도 |
| `EMB301` | 500 | 임베딩 모델 로드에 실패했습니다 | 모델 초기화 실패 | 인프라 확인 |
| `EMB302` | 500 | 메모리 부족으로 임베딩에 실패했습니다 | OOM | 배치 크기 축소 |
| `EMB400` | 503 | 임베딩 서비스를 사용할 수 없습니다 | 서비스 장애 | 잠시 후 재시도 |

---

### 3.8 그래프 (GRAPH)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `GRAPH001` | 400 | 잘못된 그래프 쿼리입니다 | Cypher 문법 오류 | 쿼리 확인 |
| `GRAPH100` | 404 | 엔티티를 찾을 수 없습니다 | 노드 없음 | 엔티티 ID 확인 |
| `GRAPH101` | 404 | 관계를 찾을 수 없습니다 | 엣지 없음 | 관계 조건 확인 |
| `GRAPH300` | 500 | 그래프 처리 중 오류가 발생했습니다 | 내부 오류 | 재시도 |
| `GRAPH301` | 500 | Neo4j 연결에 실패했습니다 | 연결 오류 | 인프라 확인 |
| `GRAPH400` | 503 | 그래프 서비스를 사용할 수 없습니다 | 서비스 장애 | 잠시 후 재시도 |
| `GRAPH500` | 504 | 그래프 탐색 시간이 초과되었습니다 | 탐색 타임아웃 | 탐색 깊이 축소 |

---

### 3.9 LLM 연동 (LLM)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `LLM001` | 400 | 잘못된 프롬프트입니다 | 프롬프트 형식 오류 | 프롬프트 확인 |
| `LLM002` | 400 | 토큰 한도를 초과했습니다 | 입력 토큰 초과 | 입력 축소 |
| `LLM300` | 500 | LLM 처리 중 오류가 발생했습니다 | API 오류 | 재시도 |
| `LLM301` | 500 | LLM 응답을 파싱할 수 없습니다 | JSON 파싱 실패 | 재시도 |
| `LLM400` | 502 | LLM API 오류가 발생했습니다 | 외부 API 오류 | Fallback 또는 재시도 |
| `LLM401` | 503 | LLM 서비스를 사용할 수 없습니다 | API 서비스 장애 | Fallback 사용 |
| `LLM402` | 429 | LLM API 호출 한도를 초과했습니다 | Rate Limit | 잠시 후 재시도 |
| `LLM500` | 504 | LLM 응답 시간이 초과되었습니다 | API 타임아웃 | 재시도 |

---

### 3.10 데이터 동기화 (SYNC)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `SYNC001` | 400 | 잘못된 동기화 요청입니다 | 요청 형식 오류 | 요청 확인 |
| `SYNC300` | 500 | 동기화 처리 중 오류가 발생했습니다 | 내부 오류 | 재시도 |
| `SYNC301` | 500 | PostgreSQL 동기화에 실패했습니다 | PG 오류 | DBA 확인 |
| `SYNC302` | 500 | Elasticsearch 동기화에 실패했습니다 | ES 오류 | 인프라 확인 |
| `SYNC303` | 500 | Neo4j 동기화에 실패했습니다 | Neo4j 오류 | 인프라 확인 |
| `SYNC304` | 500 | 데이터 정합성 오류가 발생했습니다 | 불일치 감지 | 정합성 검증 실행 |
| `SYNC400` | 503 | 동기화 서비스를 사용할 수 없습니다 | 서비스 장애 | 잠시 후 재시도 |

---

### 3.11 파일 처리 (FILE)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `FILE001` | 400 | 파일이 필요합니다 | 파일 누락 | 파일 첨부 |
| `FILE002` | 400 | 지원하지 않는 파일 형식입니다 | 확장자 제한 | 지원 형식 확인 |
| `FILE003` | 400 | 파일 크기가 초과되었습니다 | 크기 제한 | 파일 크기 축소 |
| `FILE004` | 400 | 손상된 파일입니다 | 파일 무결성 오류 | 파일 재업로드 |
| `FILE005` | 400 | 빈 파일입니다 | 내용 없음 | 파일 내용 확인 |
| `FILE300` | 500 | 파일 처리 중 오류가 발생했습니다 | 내부 오류 | 재시도 |
| `FILE301` | 500 | 파일 저장에 실패했습니다 | 스토리지 오류 | 인프라 확인 |
| `FILE302` | 500 | 파일 읽기에 실패했습니다 | 파일 접근 오류 | 권한 확인 |

---

### 3.12 외부 시스템 (EXT)

| 코드 | HTTP | 메시지 | 설명 | 대응 방법 |
|------|------|--------|------|-----------|
| `EXT001` | 400 | 외부 시스템 요청이 올바르지 않습니다 | 요청 형식 오류 | 요청 확인 |
| `EXT400` | 502 | 외부 시스템 오류가 발생했습니다 | 외부 API 오류 | 외부 시스템 확인 |
| `EXT401` | 503 | 외부 시스템에 연결할 수 없습니다 | 연결 실패 | 네트워크 확인 |
| `EXT402` | 503 | 외부 시스템이 응답하지 않습니다 | 응답 없음 | 외부 시스템 상태 확인 |
| `EXT500` | 504 | 외부 시스템 응답 시간이 초과되었습니다 | 타임아웃 | 재시도 |

---

## 4. 에러 응답 표준

### 4.1 응답 형식

```json
{
  "success": false,
  "error": {
    "code": "DOC100",
    "message": "문서를 찾을 수 없습니다",
    "detail": "요청한 문서 ID(doc_12345)가 존재하지 않습니다.",
    "timestamp": "2026-01-16T10:30:00Z",
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "path": "/api/v1/documents/doc_12345"
  }
}
```

### 4.2 필드 정의

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `success` | boolean | O | 성공 여부 (에러 시 false) |
| `error.code` | string | O | 에러 코드 |
| `error.message` | string | O | 사용자 표시용 메시지 |
| `error.detail` | string | X | 상세 설명 (개발자용) |
| `error.timestamp` | string | O | 에러 발생 시간 (ISO 8601) |
| `error.traceId` | string | O | 추적 ID (로그 조회용) |
| `error.path` | string | O | 요청 경로 |
| `error.field` | string | X | 오류 발생 필드 (유효성 검증) |
| `error.errors` | array | X | 다중 에러 목록 |

### 4.3 다중 에러 응답

```json
{
  "success": false,
  "error": {
    "code": "SYS003",
    "message": "파라미터 형식이 올바르지 않습니다",
    "timestamp": "2026-01-16T10:30:00Z",
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "path": "/api/v1/documents",
    "errors": [
      {
        "field": "title",
        "code": "DOC004",
        "message": "문서 제목이 너무 깁니다",
        "value": "very long title..."
      },
      {
        "field": "valid_end_date",
        "code": "DOC005",
        "message": "유효기간이 올바르지 않습니다",
        "value": "2025-01-01"
      }
    ]
  }
}
```

### 4.4 성공 응답 형식 (참고)

```json
{
  "success": true,
  "data": {
    "id": "doc_12345",
    "title": "문서 제목",
    ...
  },
  "meta": {
    "timestamp": "2026-01-16T10:30:00Z",
    "traceId": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## 5. 공통 코드 정의

### 5.1 문서 상태 (DOC_STATUS)

| 코드 | 한글명 | 영문명 | 설명 |
|------|--------|--------|------|
| `DRAFT` | 임시저장 | Draft | 작성 중인 문서 |
| `PENDING` | 처리대기 | Pending | 처리 대기 중 |
| `PROCESSING` | 처리중 | Processing | 임베딩/분석 처리 중 |
| `PUBLISHED` | 게시됨 | Published | 정상 게시된 문서 |
| `EXPIRED` | 만료됨 | Expired | 유효기간 만료 |
| `DELETED` | 삭제됨 | Deleted | Soft Delete된 문서 |
| `ERROR` | 오류 | Error | 처리 중 오류 발생 |

### 5.2 문서 유형 (DOC_TYPE)

| 코드 | 한글명 | 설명 |
|------|--------|------|
| `TECH` | 기술문서 | 기술 관련 문서 |
| `MEETING` | 회의록 | 회의 기록 |
| `REPORT` | 보고서 | 각종 보고서 |
| `GUIDE` | 가이드 | 사용 가이드 |
| `MANUAL` | 매뉴얼 | 운영/사용 매뉴얼 |
| `PROPOSAL` | 제안서 | 제안/기획 문서 |
| `POLICY` | 정책 | 정책/규정 문서 |
| `OTHER` | 기타 | 기타 문서 |

### 5.3 사용자 역할 (USER_ROLE)

| 코드 | 한글명 | 설명 | 권한 수준 |
|------|--------|------|-----------|
| `ADMIN` | 관리자 | 시스템 전체 관리 | 최고 |
| `MANAGER` | 매니저 | 부서/팀 관리 | 높음 |
| `USER` | 사용자 | 일반 사용자 | 보통 |
| `VIEWER` | 열람자 | 읽기 전용 | 낮음 |
| `GUEST` | 게스트 | 비회원 접근 | 최저 |

### 5.4 검색 유형 (SEARCH_TYPE)

| 코드 | 한글명 | 설명 |
|------|--------|------|
| `VECTOR` | 벡터검색 | 임베딩 유사도 검색 |
| `GRAPH` | 그래프검색 | 엔티티/관계 탐색 |
| `KEYWORD` | 키워드검색 | BM25 텍스트 검색 |
| `HYBRID` | 하이브리드 | 통합 검색 |

### 5.5 엔티티 유형 (ENTITY_TYPE)

| 코드 | 한글명 | 설명 |
|------|--------|------|
| `PERSON` | 인물 | 사람 (이름, 직책) |
| `PROJECT` | 프로젝트 | 프로젝트/시스템 |
| `TECHNOLOGY` | 기술 | 기술/도구/언어 |
| `ORGANIZATION` | 조직 | 회사/부서/팀 |
| `CONCEPT` | 개념 | 아키텍처/방법론 |
| `DOCUMENT` | 문서 | 문서 참조 |
| `DATE` | 날짜 | 일정/기한 |
| `LOCATION` | 위치 | 장소 |

### 5.6 관계 유형 (RELATION_TYPE)

| 코드 | 한글명 | 설명 |
|------|--------|------|
| `CREATED` | 생성함 | A가 B를 생성 |
| `USES` | 사용함 | A가 B를 사용 |
| `BELONGS_TO` | 소속됨 | A가 B에 소속 |
| `PARTICIPATES` | 참여함 | A가 B에 참여 |
| `MANAGES` | 관리함 | A가 B를 관리 |
| `RELATED_TO` | 관련됨 | A와 B가 관련 |
| `DEPENDS_ON` | 의존함 | A가 B에 의존 |
| `MENTIONS` | 언급함 | A가 B를 언급 |

### 5.7 동기화 상태 (SYNC_STATUS)

| 코드 | 한글명 | 설명 |
|------|--------|------|
| `PENDING` | 대기중 | 동기화 대기 |
| `IN_PROGRESS` | 진행중 | 동기화 진행 중 |
| `COMPLETED` | 완료 | 동기화 완료 |
| `PARTIAL` | 부분완료 | 일부만 완료 |
| `FAILED` | 실패 | 동기화 실패 |
| `RETRY` | 재시도중 | 재시도 진행 중 |

### 5.8 카테고리 (CATEGORY)

#### 대분류 (CATEGORY_L1)

| 코드 | 한글명 |
|------|--------|
| `TECH` | 기술 |
| `MGMT` | 경영 |
| `HR` | 인사 |
| `FIN` | 재무 |
| `PLAN` | 기획 |
| `OPS` | 운영 |

---

## 6. 코드 관리 방법

### 6.1 코드 저장 구조

```
knowledge_service/
├── src/
│   └── app/
│       └── core/
│           └── codes/
│               ├── __init__.py
│               ├── error_codes.py      # 에러 코드 정의
│               ├── common_codes.py     # 공통 코드 정의
│               └── messages.py         # 메시지 템플릿
└── resources/
    └── codes/
        ├── error_codes.json            # JSON 형식 (프론트엔드 공유)
        └── common_codes.json
```

### 6.2 Python 코드 정의

```python
# error_codes.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional

@dataclass
class ErrorDefinition:
    code: str
    http_status: int
    message: str
    message_key: str  # i18n 키
    description: str

class ErrorCode(Enum):
    """에러 코드 정의"""

    # 시스템 공통
    SYS001 = ErrorDefinition(
        code="SYS001",
        http_status=400,
        message="잘못된 요청입니다",
        message_key="error.sys.bad_request",
        description="요청 형식 오류"
    )
    SYS300 = ErrorDefinition(
        code="SYS300",
        http_status=500,
        message="내부 서버 오류가 발생했습니다",
        message_key="error.sys.internal",
        description="예상치 못한 오류"
    )

    # 인증
    AUTH001 = ErrorDefinition(
        code="AUTH001",
        http_status=401,
        message="인증이 필요합니다",
        message_key="error.auth.required",
        description="토큰 없음"
    )

    # 문서
    DOC100 = ErrorDefinition(
        code="DOC100",
        http_status=404,
        message="문서를 찾을 수 없습니다",
        message_key="error.doc.not_found",
        description="존재하지 않는 문서"
    )

    # ... 계속

    @property
    def definition(self) -> ErrorDefinition:
        return self.value
```

### 6.3 공통 코드 정의

```python
# common_codes.py
from enum import Enum

class DocStatus(str, Enum):
    """문서 상태"""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PUBLISHED = "PUBLISHED"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"
    ERROR = "ERROR"

    @property
    def label(self) -> str:
        labels = {
            "DRAFT": "임시저장",
            "PENDING": "처리대기",
            "PROCESSING": "처리중",
            "PUBLISHED": "게시됨",
            "EXPIRED": "만료됨",
            "DELETED": "삭제됨",
            "ERROR": "오류"
        }
        return labels[self.value]

class DocType(str, Enum):
    """문서 유형"""
    TECH = "TECH"
    MEETING = "MEETING"
    REPORT = "REPORT"
    GUIDE = "GUIDE"
    MANUAL = "MANUAL"
    PROPOSAL = "PROPOSAL"
    POLICY = "POLICY"
    OTHER = "OTHER"

class UserRole(str, Enum):
    """사용자 역할"""
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"
    VIEWER = "VIEWER"
    GUEST = "GUEST"
```

### 6.4 Java/Spring 코드 정의

```java
// ErrorCode.java
public enum ErrorCode {

    // 시스템 공통
    SYS001(400, "잘못된 요청입니다", "error.sys.bad_request"),
    SYS300(500, "내부 서버 오류가 발생했습니다", "error.sys.internal"),

    // 인증
    AUTH001(401, "인증이 필요합니다", "error.auth.required"),
    AUTH010(403, "접근 권한이 없습니다", "error.auth.forbidden"),

    // 문서
    DOC100(404, "문서를 찾을 수 없습니다", "error.doc.not_found"),
    DOC200(409, "문서가 이미 존재합니다", "error.doc.duplicate");

    private final int httpStatus;
    private final String message;
    private final String messageKey;

    ErrorCode(int httpStatus, String message, String messageKey) {
        this.httpStatus = httpStatus;
        this.message = message;
        this.messageKey = messageKey;
    }

    public int getHttpStatus() { return httpStatus; }
    public String getMessage() { return message; }
    public String getMessageKey() { return messageKey; }
}
```

### 6.5 JSON 형식 (프론트엔드 공유)

```json
{
  "version": "1.0",
  "updated": "2026-01-16",
  "error_codes": {
    "SYS001": {
      "http_status": 400,
      "message": "잘못된 요청입니다",
      "message_key": "error.sys.bad_request"
    },
    "AUTH001": {
      "http_status": 401,
      "message": "인증이 필요합니다",
      "message_key": "error.auth.required"
    },
    "DOC100": {
      "http_status": 404,
      "message": "문서를 찾을 수 없습니다",
      "message_key": "error.doc.not_found"
    }
  },
  "common_codes": {
    "DOC_STATUS": {
      "DRAFT": { "label": "임시저장", "order": 1 },
      "PENDING": { "label": "처리대기", "order": 2 },
      "PROCESSING": { "label": "처리중", "order": 3 },
      "PUBLISHED": { "label": "게시됨", "order": 4 },
      "EXPIRED": { "label": "만료됨", "order": 5 },
      "DELETED": { "label": "삭제됨", "order": 6 }
    },
    "DOC_TYPE": {
      "TECH": { "label": "기술문서" },
      "MEETING": { "label": "회의록" }
    }
  }
}
```

### 6.6 코드 변경 관리

| 작업 | 절차 |
|------|------|
| 코드 추가 | 1. 설계서 업데이트 → 2. 소스 코드 추가 → 3. JSON 동기화 → 4. 배포 |
| 코드 수정 | 1. 영향도 분석 → 2. 설계서 업데이트 → 3. 소스 코드 수정 → 4. 테스트 → 5. 배포 |
| 코드 삭제 | 1. 사용처 확인 → 2. Deprecated 표시 → 3. 마이그레이션 → 4. 삭제 |

---

## 7. 모니터링 연계

### 7.1 Prometheus 메트릭

```python
# 에러 코드별 메트릭
from prometheus_client import Counter

error_counter = Counter(
    'app_errors_total',
    'Total application errors',
    ['error_code', 'service', 'path']
)

# 사용 예시
def handle_error(error_code: str, service: str, path: str):
    error_counter.labels(
        error_code=error_code,
        service=service,
        path=path
    ).inc()
```

### 7.2 Grafana 쿼리

```promql
# 에러 코드별 발생 건수 (1시간)
sum by (error_code) (
  increase(app_errors_total[1h])
)

# 특정 에러 코드 조회
app_errors_total{error_code="AUTH001"}

# 서비스별 에러율
sum by (service) (rate(app_errors_total[5m])) /
sum by (service) (rate(http_requests_total[5m])) * 100

# 상위 10개 에러 코드
topk(10, sum by (error_code) (increase(app_errors_total[24h])))
```

### 7.3 알림 규칙

```yaml
# prometheus/alerts/error_alerts.yml
groups:
  - name: error_code_alerts
    rules:
      # 인증 에러 급증
      - alert: AuthErrorSpike
        expr: |
          sum(rate(app_errors_total{error_code=~"AUTH.*"}[5m])) > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "인증 에러 급증"
          description: "인증 관련 에러가 분당 10건 이상 발생: {{ $value }}"

      # 500 에러 발생
      - alert: InternalErrorOccurred
        expr: |
          sum(rate(app_errors_total{error_code=~".*300"}[5m])) > 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "내부 서버 에러 발생"
          description: "에러 코드: {{ $labels.error_code }}"

      # LLM 서비스 에러
      - alert: LLMServiceError
        expr: |
          sum(rate(app_errors_total{error_code=~"LLM4.*"}[5m])) > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "LLM 서비스 에러"
          description: "LLM API 에러가 지속적으로 발생. Fallback 전환 필요."
```

### 7.4 Grafana 대시보드

```json
{
  "panels": [
    {
      "title": "에러 코드별 발생 현황",
      "type": "piechart",
      "targets": [
        {
          "expr": "sum by (error_code) (increase(app_errors_total[24h]))",
          "legendFormat": "{{error_code}}"
        }
      ]
    },
    {
      "title": "에러 추이 (서비스별)",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum by (service) (rate(app_errors_total[5m]))",
          "legendFormat": "{{service}}"
        }
      ]
    },
    {
      "title": "에러 코드 검색",
      "type": "table",
      "targets": [
        {
          "expr": "app_errors_total{error_code=~\"$error_code\"}",
          "legendFormat": "{{error_code}} - {{path}}"
        }
      ]
    }
  ],
  "templating": {
    "list": [
      {
        "name": "error_code",
        "type": "query",
        "query": "label_values(app_errors_total, error_code)"
      }
    ]
  }
}
```

### 7.5 로그 연계

```python
import structlog

logger = structlog.get_logger()

def log_error(error_code: str, message: str, traceId: str, **context):
    """에러 로그 기록"""
    logger.error(
        message,
        error_code=error_code,
        traceId=traceId,
        **context
    )

# 사용 예시
log_error(
    error_code="DOC100",
    message="문서를 찾을 수 없습니다",
    traceId="550e8400-e29b-41d4-a716-446655440000",
    document_id="123e4567-e89b-12d3-a456-426614174000",
    user_id="7c9e6679-7425-40de-944b-e07fc1f90ae7"
)
```

**Loki 쿼리 (에러 코드로 조회)**:
```logql
{service="backend"} |= "error_code" | json | error_code="DOC100"
```

---

## 8. 구현 가이드

### 8.1 Python (FastAPI)

```python
# exceptions.py
from fastapi import HTTPException
from app.core.codes.error_codes import ErrorCode

class AppException(HTTPException):
    """애플리케이션 예외"""

    def __init__(
        self,
        error_code: ErrorCode,
        detail: str = None,
        headers: dict = None
    ):
        self.error_code = error_code.definition
        super().__init__(
            status_code=self.error_code.http_status,
            detail=detail or self.error_code.message,
            headers=headers
        )

class DocumentNotFoundException(AppException):
    def __init__(self, document_id: str):
        super().__init__(
            error_code=ErrorCode.DOC100,
            detail=f"문서 ID({document_id})를 찾을 수 없습니다"
        )

# 사용
raise DocumentNotFoundException("doc_12345")
```

```python
# exception_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
import uuid
from datetime import datetime

async def app_exception_handler(request: Request, exc: AppException):
    traceId = request.headers.get("X-Trace-ID", str(uuid.uuid4()))

    # 메트릭 기록
    error_counter.labels(
        error_code=exc.error_code.code,
        service="ai-service",
        path=request.url.path
    ).inc()

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code.code,
                "message": exc.error_code.message,
                "detail": exc.detail,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "traceId": traceId,
                "path": request.url.path
            }
        }
    )
```

### 8.2 Java (Spring Boot)

```java
// GlobalExceptionHandler.java
@RestControllerAdvice
public class GlobalExceptionHandler {

    private final MeterRegistry meterRegistry;

    @ExceptionHandler(AppException.class)
    public ResponseEntity<ErrorResponse> handleAppException(
        AppException ex,
        HttpServletRequest request
    ) {
        String traceId = request.getHeader("X-Trace-ID");
        if (traceId == null) {
            traceId = UUID.randomUUID().toString();
        }

        // 메트릭 기록
        meterRegistry.counter("app.errors",
            "error_code", ex.getErrorCode().name(),
            "service", "backend",
            "path", request.getRequestURI()
        ).increment();

        ErrorResponse response = ErrorResponse.builder()
            .success(false)
            .code(ex.getErrorCode().name())
            .message(ex.getErrorCode().getMessage())
            .detail(ex.getDetail())
            .timestamp(Instant.now().toString())
            .traceId(traceId)
            .path(request.getRequestURI())
            .build();

        return ResponseEntity
            .status(ex.getErrorCode().getHttpStatus())
            .body(response);
    }
}
```

### 8.3 TypeScript (Frontend)

```typescript
// errorHandler.ts
interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    detail?: string;
    timestamp: string;
    traceId: string;
    path: string;
  };
}

// 에러 코드 메시지 매핑 (다국어 지원)
const ERROR_MESSAGES: Record<string, string> = {
  AUTH001: "로그인이 필요합니다.",
  AUTH002: "세션이 만료되었습니다. 다시 로그인해주세요.",
  DOC100: "문서를 찾을 수 없습니다.",
  SYS300: "오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
  // ...
};

export function handleApiError(error: ErrorResponse): void {
  const { code, message } = error.error;

  // 사용자 친화적 메시지 표시
  const userMessage = ERROR_MESSAGES[code] || message;

  // 토스트 알림
  toast.error(userMessage);

  // 특정 에러 처리
  if (code === "AUTH001" || code === "AUTH002") {
    // 로그인 페이지로 리다이렉트
    router.push("/login");
  }

  // 에러 로깅 (Sentry 등)
  logError({
    code,
    message,
    traceId: error.error.traceId,
  });
}
```

---

## 9. 부록

### 9.1 HTTP 상태 코드 참조

| 코드 | 의미 | 사용 시나리오 |
|------|------|---------------|
| 200 | OK | 성공 |
| 201 | Created | 리소스 생성 성공 |
| 204 | No Content | 삭제 성공 (응답 본문 없음) |
| 400 | Bad Request | 요청 형식 오류 |
| 401 | Unauthorized | 인증 필요 |
| 403 | Forbidden | 권한 없음 |
| 404 | Not Found | 리소스 없음 |
| 409 | Conflict | 충돌 (중복 등) |
| 429 | Too Many Requests | 요청 한도 초과 |
| 500 | Internal Server Error | 서버 내부 오류 |
| 502 | Bad Gateway | 외부 서비스 오류 |
| 503 | Service Unavailable | 서비스 일시 중단 |
| 504 | Gateway Timeout | 타임아웃 |

### 9.2 체크리스트

- [ ] 모든 API 응답이 표준 형식을 따르는지 확인
- [ ] 에러 코드가 Prometheus 메트릭에 기록되는지 확인
- [ ] Grafana에서 에러 코드별 조회가 가능한지 확인
- [ ] 프론트엔드에서 에러 메시지가 올바르게 표시되는지 확인
- [ ] 알림 규칙이 정상 동작하는지 확인

---

**문서 끝**

**관련 문서**:
- [용어사전](./glossary.md)
- [API 통합 설계서](./api_integration_design.md)
- [백엔드 상세 설계서](./backend_detailed_design.md)
- [Hybrid RAG 플랫폼 상세 설계서](./hybrid_rag_platform_detailed_design.md)
