# Hybrid RAG Knowledge Platform 통합 상세 설계서

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | Hybrid RAG Knowledge Platform 통합 상세 설계서 |
| **버전** | 1.0 |
| **작성일** | 2026-01-16 |
| **작성자** | Claude Code (Opus 4.5) |
| **상태** | Final Draft |
| **목적** | 프로젝트 발표 및 설계 통합 참조용 |

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-16 | Claude Code | 초안 작성 - 9개 설계서 통합 |

---

## 목차

1. [Executive Summary](#1-executive-summary)
2. [프로젝트 개요](#2-프로젝트-개요)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [플랫폼 핵심 설계](#4-플랫폼-핵심-설계)
5. [백엔드 설계](#5-백엔드-설계)
6. [프론트엔드 설계](#6-프론트엔드-설계)
7. [인증 및 보안 설계](#7-인증-및-보안-설계)
8. [인프라 및 DevOps 설계](#8-인프라-및-devops-설계)
9. [API 통합 설계](#9-api-통합-설계)
10. [품질 보증 전략](#10-품질-보증-전략)
11. [2단계 구축 사업 이관 항목](#11-2단계-구축-사업-이관-항목)
12. [부록](#12-부록)

---

## 1. Executive Summary

### 1.1 프로젝트 비전

**"기업 지식의 80%가 잠들어 있는 문서에서, AI가 즉시 답을 찾아드립니다"**

Hybrid RAG Knowledge Platform은 **Vector Search + Graph Search**를 결합한 차세대 지식 검색 시스템으로, 기업 내부 문서에서 정확하고 신뢰할 수 있는 답변을 제공합니다.

### 1.2 핵심 가치 제안

```mermaid
mindmap
  root((Hybrid RAG<br/>Platform))
    비용 효율성
      DeepSeek 단일 모델
      LLM 비용 95% 절감
      연간 ~$14,000
    정확한 검색
      Vector + Graph 융합
      RRF 재순위 알고리즘
      컨텍스트 기반 답변
    기업 보안
      Keycloak OAuth 2.0
      AES-256 암호화
      RBAC 권한 관리
    확장 가능성
      Docker Compose → K8s
      마이크로서비스 구조
      API 기반 통합
```

### 1.3 주요 수치

| 항목 | 목표 | 비고 |
|------|------|------|
| **응답 시간** | < 3초 (P95) | Hybrid 검색 + 답변 생성 |
| **검색 정확도** | > 85% (Precision@5) | 상위 5개 결과 기준 |
| **LLM 비용** | 95% 절감 | GPT-4 대비 DeepSeek |
| **가용성** | 99.5% | SLA 기준 |
| **동시 사용자** | 100명 | 1단계 목표 |

---

## 2. 프로젝트 개요

### 2.1 배경 및 목적

```mermaid
flowchart LR
    subgraph Problem["현재 문제점"]
        P1["📁 문서 분산 저장"]
        P2["🔍 검색 불가"]
        P3["⏰ 정보 탐색 시간 ↑"]
        P4["💸 중복 업무 발생"]
    end

    subgraph Solution["해결 방안"]
        S1["🗄️ 통합 지식 저장소"]
        S2["🤖 AI 기반 검색"]
        S3["⚡ 즉시 답변 제공"]
        S4["📊 지식 재활용"]
    end

    Problem --> Solution

    style Problem fill:#ffcccc
    style Solution fill:#ccffcc
```

### 2.2 프로젝트 범위

#### 2.2.1 1단계 구축 범위 (본 설계서)

| 영역 | 포함 기능 |
|------|----------|
| **검색** | Hybrid 검색, 채팅 모드, 키워드 검색 |
| **지식 관리** | 문서 CRUD, 버전 관리, 유효기간 |
| **사용자** | 인증, 권한, 프로필, 북마크 |
| **내보내기** | Excel, PDF, PPT 변환 |
| **관리** | 대시보드, 사용자 관리 |

#### 2.2.2 2단계 구축 이관 (Section 11 참조)

- 성능/확장성 설계서
- 재해복구 설계서
- 기타 Medium/Low Priority 항목

### 2.3 기술 스택 요약

```mermaid
block-beta
    columns 4

    block:Frontend["Frontend"]
        F1["React 18"]
        F2["TypeScript"]
        F3["MUI v5"]
        F4["Redux + React Query"]
    end

    block:Backend["Backend"]
        B1["Spring Boot 3.x"]
        B2["Spring Security"]
        B3["WebClient"]
        B4["Resilience4j"]
    end

    block:AI["AI Service"]
        A1["FastAPI"]
        A2["LangGraph"]
        A3["DeepSeek V3.2"]
        A4["BGE-M3"]
    end

    block:Data["Data Layer"]
        D1["PostgreSQL 16"]
        D2["Elasticsearch 8.x"]
        D3["Neo4j 5.x"]
        D4["Redis 7.x"]
    end

    style Frontend fill:#61dafb
    style Backend fill:#6db33f
    style AI fill:#009688
    style Data fill:#336791
```

---

## 3. 시스템 아키텍처

### 3.1 전체 시스템 구조

```mermaid
flowchart TB
    subgraph External["외부 영역"]
        User["👤 사용자"]
        DS["🤖 DeepSeek API"]
    end

    subgraph Gateway["Gateway Layer"]
        Nginx["🚪 Nginx<br/>SSL Termination"]
        GW["🔀 Spring Cloud Gateway<br/>JWT 검증, Rate Limit"]
    end

    subgraph Application["Application Layer"]
        FE["🖥️ Frontend<br/>React SPA"]
        BE["⚙️ Backend<br/>Spring Boot"]
        AI["🧠 AI Service<br/>FastAPI + LangGraph"]
    end

    subgraph Auth["인증 Layer"]
        KC["🔐 Keycloak<br/>OAuth 2.0"]
    end

    subgraph Data["Data Layer"]
        PG[("🐘 PostgreSQL<br/>SSOT")]
        ES[("🔍 Elasticsearch<br/>Vector Search")]
        Neo[("🕸️ Neo4j<br/>Graph Search")]
        Redis[("💾 Redis<br/>Cache")]
        MinIO[("📦 MinIO<br/>File Storage")]
    end

    subgraph Monitor["Monitoring"]
        Prometheus["📊 Prometheus"]
        Grafana["📈 Grafana"]
        Loki["📝 Loki"]
    end

    User -->|HTTPS| Nginx --> FE & GW
    GW --> KC
    GW --> BE --> AI --> DS
    BE --> PG & Redis & MinIO
    AI --> ES & Neo

    BE & AI --> Prometheus
    Prometheus --> Grafana

    classDef external fill:#ffeaa7,stroke:#fdcb6e
    classDef gateway fill:#fab1a0,stroke:#e17055
    classDef app fill:#81ecec,stroke:#00cec9
    classDef auth fill:#dfe6e9,stroke:#b2bec3
    classDef data fill:#a29bfe,stroke:#6c5ce7
    classDef monitor fill:#fd79a8,stroke:#e84393

    class User,DS external
    class Nginx,GW gateway
    class FE,BE,AI app
    class KC auth
    class PG,ES,Neo,Redis,MinIO data
    class Prometheus,Grafana,Loki monitor
```

### 3.2 서비스 분리 아키텍처

```mermaid
flowchart LR
    subgraph SB["SpringBoot Backend"]
        direction TB
        S1["비즈니스 로직"]
        S2["CRUD 작업"]
        S3["인증/인가"]
        S4["트랜잭션 관리"]
    end

    subgraph AI["AI Service (Python)"]
        direction TB
        A1["Hybrid 검색"]
        A2["엔티티 추출"]
        A3["임베딩 생성"]
        A4["답변 합성"]
    end

    subgraph LLM["DeepSeek API"]
        L1["deepseek-chat"]
        L2["deepseek-reasoner"]
    end

    SB -->|REST API| AI -->|API| LLM

    style SB fill:#6db33f,color:#fff
    style AI fill:#009688,color:#fff
    style LLM fill:#1a73e8,color:#fff
```

**역할 분담 원칙:**

| 서비스 | 역할 | 기술 |
|--------|------|------|
| **SpringBoot** | 비즈니스 로직, 인증, CRUD | Java, Spring Security, JPA |
| **AI Service** | AI 처리, 검색, 임베딩 | Python, FastAPI, LangGraph |

> **중요**: SpringBoot는 LLM/임베딩 모델과 직접 연동하지 않습니다.

### 3.3 데이터 흐름

#### 3.3.1 검색 흐름

```mermaid
sequenceDiagram
    autonumber
    participant U as 사용자
    participant FE as Frontend
    participant GW as Gateway
    participant BE as Backend
    participant AI as AI Service
    participant ES as Elasticsearch
    participant Neo as Neo4j
    participant DS as DeepSeek

    U->>FE: 질문 입력
    FE->>GW: POST /api/v1/search/chat
    GW->>BE: JWT 검증 후 전달
    BE->>AI: POST /internal/v1/search/chat

    par Vector Search
        AI->>ES: knn 검색 (BGE-M3)
    and Graph Search
        AI->>Neo: Cypher 쿼리
    end

    AI->>AI: RRF 결과 융합
    AI->>DS: 답변 합성 요청
    DS-->>AI: 생성된 답변
    AI-->>BE: 검색 결과 + 답변
    BE-->>GW: 응답
    GW-->>FE: JSON 응답
    FE-->>U: 답변 표시
```

#### 3.3.2 문서 업로드 흐름

```mermaid
sequenceDiagram
    autonumber
    participant U as 사용자
    participant BE as Backend
    participant MinIO as MinIO
    participant AI as AI Service
    participant PG as PostgreSQL
    participant ES as Elasticsearch
    participant Neo as Neo4j

    U->>BE: POST /api/v1/knowledge
    BE->>MinIO: 파일 저장
    BE->>PG: 메타데이터 저장 (pending)
    BE->>AI: POST /internal/v1/process

    Note over AI: Docling 파싱
    Note over AI: 청킹 처리
    Note over AI: BGE-M3 임베딩

    AI->>ES: 청크 + 벡터 저장

    Note over AI: DeepSeek 엔티티 추출

    AI->>Neo: 엔티티/관계 저장
    AI-->>BE: 처리 완료
    BE->>PG: 상태 업데이트 (completed)
    BE-->>U: 업로드 완료
```

---

## 4. 플랫폼 핵심 설계

### 4.1 VIP 3단계 LLM 아키텍처

Hybrid RAG Platform의 핵심은 **VIP (Value-Intelligent-Planning)** 3단계 LLM 처리 파이프라인입니다.

```mermaid
flowchart LR
    subgraph Stage1["Stage 1: Value<br/>엔티티 채굴"]
        D1["📄 문서"]
        E1["DeepSeek-Chat"]
        O1["엔티티/관계"]
    end

    subgraph Stage2["Stage 2: Intelligent<br/>오케스트레이션"]
        Q["❓ 질문"]
        A1["의도 분석"]
        P["검색 전략"]
        X["쿼리 실행"]
    end

    subgraph Stage3["Stage 3: Planning<br/>답변 합성"]
        R["검색 결과"]
        C["컨텍스트"]
        G["DeepSeek-Chat"]
        F["💬 답변"]
    end

    D1 --> E1 --> O1
    Q --> A1 --> P --> X
    X --> R --> C --> G --> F

    style Stage1 fill:#c8e6c9
    style Stage2 fill:#bbdefb
    style Stage3 fill:#f8bbd9
```

#### Stage별 상세

| Stage | 목적 | 모델 | 입력 | 출력 |
|-------|------|------|------|------|
| **1. Value** | 문서에서 지식 추출 | DeepSeek-Chat | 청크 텍스트 | 엔티티, 관계, 메타데이터 |
| **2. Intelligent** | 검색 전략 수립 | DeepSeek-Reasoner | 사용자 질의 | 검색 전략, 필터 조건 |
| **3. Planning** | 답변 생성 | DeepSeek-Chat | 검색 결과 | 최종 답변 |

### 4.2 Hybrid Search 융합

```mermaid
flowchart TB
    Q["사용자 질의"]

    subgraph Parallel["병렬 검색"]
        VS["Vector Search<br/>Elasticsearch knn"]
        GS["Graph Search<br/>Neo4j Cypher"]
    end

    RRF["RRF 융합 알고리즘<br/>1/(k+rank)"]

    Result["통합 검색 결과<br/>Top-K 문서"]

    Q --> VS & GS
    VS --> RRF
    GS --> RRF
    RRF --> Result

    style VS fill:#f9b716
    style GS fill:#018bff
    style RRF fill:#ff6b6b
```

**RRF (Reciprocal Rank Fusion) 알고리즘:**

```python
def rrf_fusion(vector_results, graph_results, k=60):
    scores = {}
    for rank, doc in enumerate(vector_results):
        scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank + 1)
    for rank, doc in enumerate(graph_results):
        scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### 4.3 데이터베이스 설계 원칙

#### 제로 조인 아키텍처

```mermaid
flowchart LR
    subgraph SSOT["PostgreSQL (SSOT)"]
        PG["마스터 레코드"]
    end

    subgraph Denormalized["비정규화된 검색 인덱스"]
        ES["Elasticsearch<br/>메타데이터 + 벡터"]
        Neo["Neo4j<br/>엔티티 + 관계"]
    end

    PG -->|비동기 동기화| ES
    PG -->|비동기 동기화| Neo

    style SSOT fill:#336791,color:#fff
    style Denormalized fill:#f5f5f5
```

**핵심 원칙:**

| 원칙 | 설명 |
|------|------|
| **SSOT** | PostgreSQL이 단일 진실 공급원 |
| **비정규화** | ES/Neo4j에 메타데이터 복제 |
| **제로 조인** | 단일 DB 쿼리로 검색 완료 |

### 4.4 데이터 모델

#### 4.4.1 PostgreSQL ERD

```mermaid
erDiagram
    users ||--o{ knowledge : creates
    users ||--o{ bookmarks : has
    users ||--o{ search_history : has
    knowledge ||--o{ knowledge_chunks : contains
    knowledge ||--o{ knowledge_versions : has
    bookmarks }o--|| bookmark_folders : belongs_to

    users {
        uuid id PK
        string email UK
        string name
        string password_hash
        string department
        enum role
        timestamp created_at
    }

    knowledge {
        uuid id PK
        string title
        text content
        enum document_type
        uuid created_by FK
        jsonb categories
        date valid_start
        date valid_end
        enum status
        timestamp created_at
    }

    knowledge_chunks {
        uuid id PK
        uuid knowledge_id FK
        text chunk_text
        int chunk_index
        vector_1024 embedding
    }

    bookmarks {
        uuid id PK
        uuid user_id FK
        uuid knowledge_id FK
        uuid folder_id FK
        timestamp created_at
    }
```

#### 4.4.2 Elasticsearch 인덱스

```json
{
  "knowledge_chunks": {
    "mappings": {
      "properties": {
        "chunk_id": { "type": "keyword" },
        "knowledge_id": { "type": "keyword" },
        "chunk_text": { "type": "text", "analyzer": "korean" },
        "embedding": { "type": "dense_vector", "dims": 1024 },
        "metadata": {
          "properties": {
            "document_type": { "type": "keyword" },
            "project_name": { "type": "keyword" },
            "categories": { "type": "keyword" },
            "valid_start": { "type": "date" },
            "valid_end": { "type": "date" }
          }
        }
      }
    }
  }
}
```

#### 4.4.3 Neo4j 그래프 모델

```mermaid
graph LR
    subgraph Nodes["노드 타입"]
        Person["👤 Person"]
        Project["📁 Project"]
        Technology["⚙️ Technology"]
        Document["📄 Document"]
        Concept["💡 Concept"]
    end

    subgraph Relationships["관계 타입"]
        R1["CREATED"]
        R2["PARTICIPATED"]
        R3["USES"]
        R4["RELATED_TO"]
        R5["BELONGS_TO"]
    end

    Person -->|CREATED| Document
    Person -->|PARTICIPATED| Project
    Project -->|USES| Technology
    Document -->|RELATED_TO| Concept
```

---

## 5. 백엔드 설계

### 5.1 레이어드 아키텍처

```mermaid
flowchart TB
    subgraph Presentation["Presentation Layer"]
        C1["Controller"]
        C2["DTO"]
        C3["Mapper"]
    end

    subgraph Application["Application Layer"]
        S1["Service Interface"]
        S2["Service Impl"]
        S3["Facade"]
    end

    subgraph Domain["Domain Layer"]
        D1["Entity"]
        D2["Value Object"]
        D3["Repository Interface"]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        I1["Repository Impl"]
        I2["WebClient"]
        I3["Config"]
    end

    Presentation --> Application --> Domain
    Infrastructure --> Domain

    style Presentation fill:#e3f2fd
    style Application fill:#e8f5e9
    style Domain fill:#fff3e0
    style Infrastructure fill:#fce4ec
```

### 5.2 모듈 구조

```
knowledge-platform-backend/
├── platform-common/          # 공통 (DTO, Exception, Util)
├── platform-domain/          # 도메인 (Entity, Repository Interface)
├── platform-gateway/         # API Gateway
├── platform-api/             # API Service (Controller, Service Impl)
└── platform-batch/           # 배치 처리 (선택)
```

### 5.3 AI Service 연동

```mermaid
sequenceDiagram
    participant BE as Backend
    participant CB as Circuit Breaker
    participant AI as AI Service

    BE->>CB: 요청

    alt 정상 상태
        CB->>AI: REST 호출
        AI-->>CB: 응답
        CB-->>BE: 정상 응답
    else 장애 발생
        CB-->>BE: Fallback 응답
        Note over CB: Open 상태 전환
    else 복구 시도
        CB->>AI: Half-Open 테스트
        alt 성공
            CB-->>BE: 정상 복구
        else 실패
            CB-->>BE: Fallback 유지
        end
    end
```

**Resilience4j 설정:**

| 설정 | 값 | 설명 |
|------|-----|------|
| failureRateThreshold | 50% | 실패율 임계치 |
| waitDurationInOpenState | 30초 | Open 상태 유지 시간 |
| slidingWindowSize | 10 | 집계 윈도우 크기 |
| timeout | 30초 | 요청 타임아웃 |

---

## 6. 프론트엔드 설계

### 6.1 컴포넌트 아키텍처

```mermaid
flowchart TB
    subgraph Pages["Pages (페이지)"]
        P1["DashboardPage"]
        P2["SearchPage"]
        P3["KnowledgeDetailPage"]
    end

    subgraph Features["Features (기능)"]
        F1["SearchChat"]
        F2["KnowledgeList"]
        F3["BookmarkPanel"]
    end

    subgraph Components["Components (공유)"]
        C1["Button"]
        C2["Card"]
        C3["Modal"]
        C4["Table"]
    end

    Pages --> Features --> Components

    style Pages fill:#1976d2,color:#fff
    style Features fill:#388e3c,color:#fff
    style Components fill:#f57c00,color:#fff
```

### 6.2 상태 관리

```mermaid
flowchart LR
    subgraph Client["클라이언트 상태"]
        Redux["Redux Toolkit"]
        Redux --> UI["UI 상태"]
        Redux --> Auth["인증 상태"]
    end

    subgraph Server["서버 상태"]
        RQ["React Query"]
        RQ --> Cache["서버 데이터 캐시"]
        RQ --> Sync["자동 동기화"]
    end

    style Client fill:#764abc,color:#fff
    style Server fill:#ff4154,color:#fff
```

### 6.3 라우팅 구조

| 경로 | 페이지 | 권한 |
|------|--------|------|
| `/` | 대시보드 | USER |
| `/search` | 검색 | USER |
| `/knowledge` | 지식 목록 | USER |
| `/knowledge/:id` | 지식 상세 | USER |
| `/knowledge/new` | 지식 등록 | MANAGER |
| `/bookmarks` | 북마크 | USER |
| `/profile` | 프로필 | USER |
| `/admin/*` | 관리자 | ADMIN |

### 6.4 핵심 기능 UI

#### 6.4.1 검색 모드

```
┌─────────────────────────────────────────────────────────────┐
│  [📖 검색 모드] [💬 채팅 모드]                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🔍  검색어를 입력하세요...                    [검색]   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  📄 문서 제목 1                                             │
│     요약 내용 미리보기...                                    │
│     [기술문서] [프로젝트A] 2026-01-15                        │
│                                                             │
│  📄 문서 제목 2                                             │
│     요약 내용 미리보기...                                    │
│     [제안서] [프로젝트B] 2026-01-10                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 6.4.2 채팅 모드

```
┌─────────────────────────────────────────────────────────────┐
│  [📖 검색 모드] [💬 채팅 모드]                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  👤 RAG 시스템의 장점이 뭐야?                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🤖 RAG 시스템의 주요 장점은 다음과 같습니다:        │   │
│  │                                                     │   │
│  │  1. **정확한 정보 제공**: 검색된 문서 기반 답변      │   │
│  │  2. **환각 감소**: 실제 데이터 기반으로 답변 생성   │   │
│  │  3. **최신 정보**: 실시간 데이터 반영 가능          │   │
│  │                                                     │   │
│  │  📚 참조 문서:                                      │   │
│  │  • RAG 시스템 설계서 (2026-01-15)                   │   │
│  │  • AI 플랫폼 기획서 (2026-01-10)                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  💬 질문을 입력하세요...                      [전송]   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. 인증 및 보안 설계

### 7.1 인증 아키텍처

```mermaid
sequenceDiagram
    autonumber
    participant C as Client (React)
    participant G as API Gateway
    participant B as Backend API
    participant K as Keycloak (IdP)

    rect rgb(230, 245, 255)
        Note over C,K: 1. Authorization Code Flow + PKCE
        C->>K: /auth?response_type=code&code_challenge={PKCE}
        K-->>C: Login Page
        C->>K: User Credentials
        K-->>C: 302 Redirect + auth_code
    end

    rect rgb(255, 245, 230)
        Note over C,K: 2. Token Exchange
        C->>K: POST /token (code + code_verifier)
        K-->>C: Access Token + Refresh Token
    end

    rect rgb(230, 255, 230)
        Note over C,B: 3. API Request
        C->>G: Request + Bearer Token
        G->>K: Token Validation
        K-->>G: User Info
        G->>B: Authenticated Request
        B-->>C: Response
    end
```

### 7.2 JWT 토큰 전략

| 토큰 | 수명 | 저장 위치 | 갱신 |
|------|------|----------|------|
| **Access Token** | 15분 | 메모리 | 만료 2분 전 자동 갱신 |
| **Refresh Token** | 7일 | HttpOnly Cookie | Access 갱신 시 Rotation |

### 7.3 RBAC 권한 모델

```mermaid
flowchart TB
    subgraph Roles["역할"]
        ADMIN["🔧 ADMIN<br/>시스템 관리자"]
        MANAGER["📁 KNOWLEDGE_MANAGER<br/>지식 관리자"]
        USER["👤 USER<br/>일반 사용자"]
    end

    subgraph Permissions["권한"]
        P1["사용자 관리"]
        P2["시스템 설정"]
        P3["지식 CRUD"]
        P4["지식 조회/검색"]
        P5["북마크 관리"]
    end

    ADMIN --> P1 & P2 & P3 & P4 & P5
    MANAGER --> P3 & P4 & P5
    USER --> P4 & P5

    style ADMIN fill:#ff6b6b,color:#fff
    style MANAGER fill:#feca57,color:#000
    style USER fill:#54a0ff,color:#fff
```

### 7.4 데이터 암호화 계층

```mermaid
flowchart TB
    subgraph AppLayer["Application Layer"]
        FE["필드 암호화<br/>AES-256-GCM"]
        HASH["비밀번호 해싱<br/>bcrypt"]
        SIGN["토큰 서명<br/>RS256"]
    end

    subgraph Transport["Transport Layer"]
        TLS["TLS 1.3<br/>HTTPS"]
    end

    subgraph Storage["Storage Layer"]
        TDE["투명 데이터 암호화<br/>TDE"]
        DISK["디스크 암호화<br/>LUKS"]
    end

    subgraph KMS["Key Management"]
        Vault["HashiCorp Vault"]
    end

    FE & TLS & TDE --> Vault

    style AppLayer fill:#e8f5e9
    style Transport fill:#e3f2fd
    style Storage fill:#fff3e0
    style KMS fill:#fce4ec
```

### 7.5 데이터 분류 및 보호

| 분류 | 예시 | 암호화 | 마스킹 |
|------|------|--------|--------|
| **Level 4 (극비)** | 암호화 키, 마스터 비밀번호 | HSM/Vault | 전체 |
| **Level 3 (비밀)** | 비밀번호 해시, API 키 | DB 암호화 | 부분 |
| **Level 2 (대외비)** | 이름, 이메일, 검색 기록 | 필드 암호화 | 부분 |
| **Level 1 (일반)** | 문서 메타데이터, 로그 | TDE | 없음 |

---

## 8. 인프라 및 DevOps 설계

### 8.1 인프라 구성 (Docker Compose)

```mermaid
flowchart TB
    subgraph Server["Docker Host (Single Server)"]
        subgraph Containers["컨테이너 (15개)"]
            subgraph App["Application"]
                nginx["nginx"]
                frontend["frontend"]
                gateway["api-gateway"]
                backend["backend"]
                ai["ai-service"]
                keycloak["keycloak"]
            end

            subgraph Data["Database"]
                pg["postgresql"]
                es["elasticsearch"]
                neo["neo4j"]
                redis["redis"]
                minio["minio"]
            end

            subgraph Monitor["Monitoring"]
                prom["prometheus"]
                graf["grafana"]
                loki["loki"]
                promtail["promtail"]
            end
        end
    end

    style App fill:#81ecec,stroke:#00cec9
    style Data fill:#a29bfe,stroke:#6c5ce7
    style Monitor fill:#fd79a8,stroke:#e84393
```

### 8.2 서버 사양

| 환경 | CPU | Memory | Storage | 용도 |
|------|-----|--------|---------|------|
| **Production** | 32 cores | 128 GB | 1TB SSD + 2TB HDD | 운영 |
| **Staging** | 16 cores | 64 GB | 500 GB SSD | 통합 테스트 |
| **Development** | 8 cores | 32 GB | 256 GB SSD | 개발 |

### 8.3 Git 브랜치 전략

```mermaid
gitGraph
    commit id: "Initial"
    branch develop
    checkout develop
    commit id: "Setup"

    branch feature/login
    checkout feature/login
    commit id: "Add login"
    checkout develop
    merge feature/login id: "PR #1"

    branch feature/search
    checkout feature/search
    commit id: "Search API"
    checkout develop
    merge feature/search id: "PR #2"

    checkout main
    merge develop id: "Release v1.0"
    commit id: "v1.0.0" tag: "v1.0.0"
```

**브랜치 규칙:**

| 브랜치 | 패턴 | 용도 |
|--------|------|------|
| `main` | `main` | 프로덕션 릴리스 |
| `develop` | `develop` | 개발 통합 |
| `feature/*` | `feature/ISSUE-{번호}-{설명}` | 새 기능 |
| `fix/*` | `fix/ISSUE-{번호}-{설명}` | 버그 수정 |
| `hotfix/*` | `hotfix/ISSUE-{번호}-{설명}` | 긴급 수정 |

### 8.4 CI/CD 파이프라인

```mermaid
flowchart LR
    subgraph CI["CI (Continuous Integration)"]
        Push["Git Push"]
        Build["Build"]
        Test["Test"]
        Scan["Security Scan"]
        Quality["SonarQube"]
    end

    subgraph CD["CD (Continuous Deployment)"]
        Image["Docker Image"]
        Stage["Staging Deploy"]
        Approve["Manual Approve"]
        Prod["Production Deploy"]
    end

    Push --> Build --> Test --> Scan --> Quality
    Quality --> Image --> Stage --> Approve --> Prod

    style CI fill:#e3f2fd
    style CD fill:#e8f5e9
```

### 8.5 모니터링 스택

| 도구 | 용도 | 수집 대상 |
|------|------|----------|
| **Prometheus** | 메트릭 수집 | CPU, Memory, API 지연시간 |
| **Grafana** | 대시보드 | 시스템 현황 시각화 |
| **Loki** | 로그 수집 | 애플리케이션 로그 |
| **Promtail** | 로그 수집 에이전트 | 컨테이너 로그 |

---

## 9. API 통합 설계

### 9.1 API 구조

```
External API (Frontend ↔ Backend)
├── /api/v1/auth/*          # 인증
├── /api/v1/knowledge/*     # 지식 관리
├── /api/v1/search/*        # 검색
├── /api/v1/users/*         # 사용자
├── /api/v1/bookmarks/*     # 북마크
├── /api/v1/dashboard/*     # 대시보드
├── /api/v1/export/*        # 내보내기
└── /api/v1/admin/*         # 관리자

Internal API (Backend ↔ AI Service)
├── /internal/v1/search/*   # 검색 파이프라인
├── /internal/v1/extract/*  # 엔티티 추출
├── /internal/v1/embed/*    # 임베딩 생성
├── /internal/v1/parse/*    # 문서 파싱
└── /health                 # 헬스체크
```

### 9.2 주요 API 엔드포인트

#### External API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/search/chat` | 채팅 검색 (RAG) |
| POST | `/api/v1/search/hybrid` | Hybrid 검색 |
| GET | `/api/v1/knowledge` | 지식 목록 |
| POST | `/api/v1/knowledge` | 지식 등록 |
| GET | `/api/v1/knowledge/{id}` | 지식 상세 |
| PUT | `/api/v1/knowledge/{id}` | 지식 수정 |
| DELETE | `/api/v1/knowledge/{id}` | 지식 삭제 |
| POST | `/api/v1/export/excel` | Excel 내보내기 |
| POST | `/api/v1/export/pdf` | PDF 내보내기 |

#### Internal API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/internal/v1/search/hybrid` | Hybrid 검색 수행 |
| POST | `/internal/v1/search/chat` | 답변 합성 포함 검색 |
| POST | `/internal/v1/extract/entities` | 엔티티 추출 |
| POST | `/internal/v1/extract/metadata` | 메타데이터 생성 |
| POST | `/internal/v1/embed` | 임베딩 생성 |
| POST | `/internal/v1/embed/batch` | 배치 임베딩 |

### 9.3 공통 응답 형식

#### 성공 응답

```json
{
  "success": true,
  "data": { /* 응답 데이터 */ },
  "message": "요청이 성공적으로 처리되었습니다.",
  "timestamp": "2026-01-16T10:30:00Z",
  "requestId": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 에러 응답

```json
{
  "success": false,
  "error": {
    "code": "KNOWLEDGE_NOT_FOUND",
    "message": "요청한 지식을 찾을 수 없습니다.",
    "details": { "knowledgeId": "xxx-xxx" }
  },
  "timestamp": "2026-01-16T10:30:00Z",
  "requestId": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 9.4 에러 코드 체계

| 서비스 | 코드 범위 | 예시 |
|--------|----------|------|
| **SYS** (시스템) | SYS001-599 | SYS300: 내부 서버 오류 |
| **AUTH** (인증) | AUTH001-099 | AUTH002: 토큰 만료 |
| **USER** (사용자) | USER001-399 | USER100: 사용자 없음 |
| **DOC** (문서) | DOC001-399 | DOC100: 문서 없음 |
| **SRCH** (검색) | SRCH001-599 | SRCH301: ES 오류 |
| **RAG** (RAG) | RAG001-599 | RAG300: 답변 생성 오류 |
| **LLM** (LLM) | LLM001-599 | LLM400: API 연결 실패 |

---

## 10. 품질 보증 전략

### 10.1 테스트 피라미드

```mermaid
flowchart TB
    subgraph Pyramid["테스트 피라미드"]
        E2E["🔺 E2E 테스트<br/>(10%)"]
        Integration["🔷 통합 테스트<br/>(30%)"]
        Unit["🟩 단위 테스트<br/>(60%)"]
    end

    E2E --> Integration --> Unit

    style E2E fill:#ff6b6b,color:#fff
    style Integration fill:#feca57,color:#000
    style Unit fill:#54a0ff,color:#fff
```

### 10.2 테스트 커버리지 목표

| 영역 | 목표 커버리지 | 도구 |
|------|-------------|------|
| **Backend (Java)** | 80%+ | JUnit 5, Mockito |
| **AI Service (Python)** | 75%+ | pytest |
| **Frontend (React)** | 70%+ | Vitest, RTL |
| **E2E** | 핵심 시나리오 | Playwright |

### 10.3 코드 품질 관리

| 도구 | 용도 |
|------|------|
| **SonarQube** | 정적 분석, 코드 품질 |
| **ESLint** | JavaScript/TypeScript 린팅 |
| **Prettier** | 코드 포맷팅 |
| **Black/isort** | Python 포맷팅 |
| **Checkstyle** | Java 코드 스타일 |

### 10.4 RAG 성능 평가

```mermaid
flowchart TB
    subgraph Metrics["RAG 평가 지표"]
        subgraph Retrieval["검색 품질"]
            P["Precision@K"]
            R["Recall@K"]
            MRR["MRR"]
            NDCG["NDCG"]
        end

        subgraph Generation["생성 품질"]
            F["Faithfulness"]
            AR["Answer Relevance"]
            CR["Context Relevance"]
        end

        subgraph Latency["응답 시간"]
            TTFB["TTFB"]
            P95["P95 Latency"]
        end
    end

    style Retrieval fill:#e3f2fd
    style Generation fill:#e8f5e9
    style Latency fill:#fff3e0
```

**상세 설계서 참조**: [RAG 성능 테스트 설계서](./rag_performance_test_design.md)

---

## 11. 2단계 구축 사업 이관 항목

### 11.1 이관 대상 문서

| 문서명 | 사유 | 2단계 추정 공수 |
|--------|------|----------------|
| **성능/확장성 설계서** | Docker Compose → K8s 마이그레이션 시 필요 | 2~3주 |
| **재해복구 설계서** | 고가용성 요구사항 발생 시 필요 | 1~2주 |

### 11.2 이관 대상 기능 (Medium Priority)

| # | 조치 | 대상 문서 | 예상 공수 |
|---|------|----------|----------|
| 1 | 캐싱 전략 상세화 | backend_detailed_design.md | 0.5일 |
| 2 | MFA 설계 추가 | authentication_authorization_detailed_design.md | 0.5일 |

### 11.3 이관 대상 기능 (Low Priority)

| # | 조치 | 대상 | 예상 공수 |
|---|------|------|----------|
| 1 | 데이터 거버넌스 설계서 | 신규 문서 | 1일 |
| 2 | 모델 버전 관리 추가 | hybrid_rag_platform_detailed_design.md | 0.5일 |
| 3 | PWA 설계 추가 | frontend_detailed_design.md | 0.5일 |
| 4 | 통합 테스트 계획서 | 신규 문서 | 1일 |

### 11.4 2단계 마이그레이션 로드맵

```mermaid
flowchart LR
    subgraph Phase1["Phase 1 (현재)<br/>Docker Compose"]
        DC["단일 서버<br/>$14,000/년"]
    end

    subgraph Phase2["Phase 2<br/>+ Redis Sentinel"]
        DR["캐시 이중화<br/>$20,000/년"]
    end

    subgraph Phase3["Phase 3<br/>Docker Swarm"]
        DS["3노드 클러스터<br/>$40,000/년"]
    end

    subgraph Phase4["Phase 4<br/>Kubernetes"]
        K8s["풀 클러스터<br/>$100,000/년"]
    end

    Phase1 --> Phase2 --> Phase3 --> Phase4
```

**마이그레이션 트리거 조건:**

| 지표 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|
| 동시 사용자 | 100+ | 500+ | 1,000+ |
| 일일 요청 수 | 10,000+ | 50,000+ | 200,000+ |
| 가용성 요구 | 99.5% | 99.9% | 99.99% |

---

## 12. 부록

### 12.1 관련 설계서 목록

| 문서명 | 파일명 | 버전 |
|--------|--------|------|
| 플랫폼 상세 설계서 | hybrid_rag_platform_detailed_design.md | 2.3 |
| 백엔드 상세 설계서 | backend_detailed_design.md | 1.0 |
| 프론트엔드 상세 설계서 | frontend_detailed_design.md | 1.0 |
| 인증/권한 상세 설계서 | authentication_authorization_detailed_design.md | 1.0 |
| 데이터 암호화 설계서 | data_encryption_design.md | 1.0 |
| 인프라 상세 설계서 | infrastructure_detailed_design.md | 2.0 |
| DevOps 상세 설계서 | devops_detailed_design.md | 1.0 |
| API 통합 설계서 | api_integration_design.md | 1.0 |
| 에러 코드 표준 | error_code_standards.md | 1.0 |
| RAG 성능 테스트 설계서 | rag_performance_test_design.md | 1.0 |
| 용어집 | glossary.md | 2.0 |

### 12.2 기술 스택 상세

#### Frontend

| 기술 | 버전 | 용도 |
|------|------|------|
| React | 18.3+ | UI 라이브러리 |
| TypeScript | 5.4+ | 타입 안정성 |
| Vite | 5.x | 빌드 도구 |
| MUI | 5.x | 컴포넌트 라이브러리 |
| Redux Toolkit | 2.x | 상태 관리 |
| React Query | 5.x | 서버 상태 |
| React Hook Form | 7.x | 폼 관리 |
| Zod | 3.x | 스키마 검증 |

#### Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| Spring Boot | 3.2+ | 프레임워크 |
| Spring Security | 6.x | 보안 |
| Spring Data JPA | 3.x | ORM |
| WebClient | 3.x | HTTP 클라이언트 |
| Resilience4j | 2.x | Circuit Breaker |
| Gradle | 8.x | 빌드 도구 |
| Java | 17+ | 런타임 |

#### AI Service

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | 런타임 |
| FastAPI | 0.110+ | API 프레임워크 |
| LangChain | 1.2+ | LLM 통합 |
| LangGraph | 1.0+ | 워크플로우 |
| Docling | 2.x | 문서 파싱 |
| BGE-M3 | - | 임베딩 |

#### Infrastructure

| 기술 | 버전 | 용도 |
|------|------|------|
| Docker | 24.x | 컨테이너 |
| Docker Compose | 2.x | 오케스트레이션 |
| Nginx | 1.25+ | 리버스 프록시 |
| PostgreSQL | 16+ | RDBMS |
| Elasticsearch | 8.x | 벡터 검색 |
| Neo4j | 5.x | 그래프 DB |
| Redis | 7.x | 캐시 |
| Keycloak | 24.x | IdP |

### 12.3 비용 추정

| 항목 | 월간 비용 | 연간 비용 | 비고 |
|------|----------|----------|------|
| **서버 (Production)** | $800 | $9,600 | 32C/128G |
| **서버 (Staging)** | $200 | $2,400 | 16C/64G |
| **DeepSeek API** | $150 | $1,800 | 예상 사용량 기준 |
| **도메인/SSL** | $20 | $240 | |
| **합계** | **$1,170** | **$14,040** | |

> GPT-4 사용 시 예상 비용: ~$100,000/년 → **86% 비용 절감**

### 12.4 프로젝트 일정 요약

```mermaid
gantt
    title 1단계 구축 일정 (예시)
    dateFormat  YYYY-MM-DD
    section 설계
    상세 설계           :done, 2026-01-01, 2026-01-20
    설계 검토           :done, 2026-01-15, 2026-01-20
    section 개발
    인프라 구축         :2026-01-21, 5d
    백엔드 개발         :2026-01-26, 20d
    AI Service 개발     :2026-01-26, 20d
    프론트엔드 개발     :2026-02-01, 15d
    section 테스트
    통합 테스트         :2026-02-16, 10d
    사용자 테스트       :2026-02-26, 5d
    section 배포
    운영 배포           :2026-03-03, 2d
```

---

## 문서 끝

**작성**: Claude Code (Opus 4.5)
**최종 수정**: 2026-01-16
**검토 상태**: Final Draft
