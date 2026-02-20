# 인프라 상세 설계서

> **현행화 정보**
> - **최종 현행화**: 2026-02-20
> - **프로젝트 상태**: 종료 (2026-02-18)
> - **구현 상태**: 부분구현 (Docker Compose 단일 노드만 구현, K8s 미적용)
> - **주요 변경사항**: 본 문서는 Kubernetes 기반 운영 환경을 목표로 작성된 참조 설계서임. 실제 구현은 Docker Compose 기반 단일 노드 18개 컨테이너로 운영하다 종료. K8s 배포, Helm Chart, ArgoCD, HashiCorp Vault, MinIO, Redis Cluster 등 본 문서 내용 대부분은 미구현. 모니터링 스택(Prometheus/Grafana/Kibana/Jaeger)은 Docker Compose로 부분 구현됨.

**프로젝트**: Hybrid RAG Knowledge Operations Platform
**버전**: 1.0
**작성일**: 2026-01-16
**작성자**: Claude AI Architect
**상태**: Draft

---

## 목차

1. [개요](#1-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
   - 2.1 [논리 구성도 (Logical Architecture)](#21-논리-구성도-logical-architecture)
   - 2.2 [물리 구성도 (Physical Architecture)](#22-물리-구성도-physical-architecture)
   - 2.3 [물리 서버 사양 요약](#23-물리-서버-사양-요약)
   - 2.4 [네트워크 구성도 (Network Architecture)](#24-네트워크-구성도-network-architecture)
   - 2.5 [VLAN 및 서브넷 설계](#25-vlan-및-서브넷-설계)
   - 2.6 [방화벽 정책 요약](#26-방화벽-정책-요약)
   - 2.7 [환경별 구성](#27-환경별-구성)
   - 2.8 [데이터 흐름도 (Data Flow Diagram)](#28-데이터-흐름도-data-flow-diagram)
     - 2.8.1 [전체 데이터 흐름 개요](#281-전체-데이터-흐름-개요)
     - 2.8.2 [문서 업로드 및 처리 흐름](#282-문서-업로드-및-처리-흐름)
     - 2.8.3 [Hybrid 검색 흐름](#283-hybrid-검색-흐름)
     - 2.8.4 [RAG Chat 스트리밍 흐름](#284-rag-chat-스트리밍-흐름)
     - 2.8.5 [인증/인가 흐름](#285-인증인가-흐름)
     - 2.8.6 [데이터 동기화 흐름 (Triple Store)](#286-데이터-동기화-흐름-triple-store)
     - 2.8.7 [데이터 저장소별 역할 요약](#287-데이터-저장소별-역할-요약)
3. [컨테이너 설계](#3-컨테이너-설계)
4. [Kubernetes 배포](#4-kubernetes-배포)
5. [네트워크 설계](#5-네트워크-설계)
6. [스토리지 설계](#6-스토리지-설계)
7. [데이터베이스 인프라](#7-데이터베이스-인프라)
8. [모니터링 및 로깅](#8-모니터링-및-로깅)
9. [CI/CD 파이프라인](#9-cicd-파이프라인)
10. [보안 인프라](#10-보안-인프라)
11. [재해 복구](#11-재해-복구)
12. [비용 추정](#12-비용-추정)

---

## 1. 개요

### 1.1 목적

본 문서는 Hybrid RAG Knowledge Platform의 인프라 아키텍처를 정의합니다.

### 1.2 범위

| 항목 | 범위 |
|------|------|
| 배포 환경 | 온프레미스 (Kubernetes) |
| 대상 시스템 | Frontend, Backend, AI Service, Databases |
| 운영 환경 | Development, Staging, Production |

> ⚠️ **실제 구현**: 배포 환경은 온프레미스 Kubernetes 대신 **Docker Compose 단일 노드**로 구현됨. Staging/Production 환경 없이 Development 환경 단일 운영으로 종료.

### 1.3 설계 원칙

| 원칙 | 설명 |
|------|------|
| **고가용성** | 단일 장애점(SPOF) 제거 |
| **확장성** | 수평적 스케일아웃 지원 |
| **보안** | Zero Trust 아키텍처 |
| **관측 가능성** | 중앙 집중식 모니터링 |
| **자동화** | IaC (Infrastructure as Code) |

---

## 2. 시스템 아키텍처

### 2.1 논리 구성도 (Logical Architecture)

시스템의 논리적 계층과 컴포넌트 간 관계를 나타냅니다.

```mermaid
flowchart TB
    subgraph External["외부 영역 (External Zone)"]
        Users["👤 사용자<br/>(Web Browser)"]
        ExtAPI["🔗 외부 API<br/>(SSO, Email 등)"]
        DeepSeek["🤖 DeepSeek API<br/>(LLM Service)"]
    end

    subgraph DMZ["DMZ 영역"]
        LB["⚖️ Load Balancer<br/>(L7)"]
        Ingress["🚪 Ingress Controller<br/>(NGINX)"]
        WAF["🛡️ WAF<br/>(ModSecurity)"]
    end

    subgraph AppLayer["애플리케이션 계층 (Application Layer)"]
        subgraph Presentation["프레젠테이션 레이어"]
            FE["🖥️ Frontend<br/>(React SPA)"]
        end

        subgraph Gateway["API 게이트웨이 레이어"]
            APIGW["🔀 API Gateway<br/>(Spring Cloud Gateway)"]
            Auth["🔐 Keycloak<br/>(OAuth 2.0 / OIDC)"]
        end

        subgraph Business["비즈니스 로직 레이어"]
            BE["⚙️ Backend API<br/>(Spring Boot)"]
            AI["🧠 AI Service<br/>(FastAPI + LangGraph)"]
        end

        subgraph Caching["캐싱 레이어"]
            Redis["💾 Redis Cluster<br/>(Session / Cache)"]
        end
    end

    subgraph DataLayer["데이터 계층 (Data Layer)"]
        subgraph SSOT["SSOT (Single Source of Truth)"]
            PG["🐘 PostgreSQL<br/>(Primary + Replica)"]
        end

        subgraph Search["검색 엔진"]
            ES["🔍 Elasticsearch<br/>(Vector + Full-text)"]
        end

        subgraph Graph["그래프 DB"]
            Neo4j["🕸️ Neo4j<br/>(Knowledge Graph)"]
        end

        subgraph Storage["오브젝트 스토리지"]
            MinIO["📦 MinIO<br/>(Document Storage)"]
        end

        subgraph Secrets["시크릿 관리"]
            Vault["🔒 HashiCorp Vault<br/>(Secrets & Keys)"]
        end
    end

    %% 연결 관계
    Users --> LB
    LB --> WAF --> Ingress
    Ingress --> FE
    Ingress --> APIGW

    FE --> APIGW
    APIGW --> Auth
    APIGW --> BE

    BE <--> AI
    BE --> Redis
    BE --> PG
    AI --> ES
    AI --> Neo4j
    AI --> DeepSeek

    BE --> MinIO
    BE --> Vault
    AI --> Vault

    ExtAPI -.-> Auth

    %% 스타일
    classDef external fill:#ffeaa7,stroke:#fdcb6e
    classDef dmz fill:#fab1a0,stroke:#e17055
    classDef app fill:#81ecec,stroke:#00cec9
    classDef data fill:#a29bfe,stroke:#6c5ce7

    class Users,ExtAPI,DeepSeek external
    class LB,Ingress,WAF dmz
    class FE,APIGW,Auth,BE,AI,Redis app
    class PG,ES,Neo4j,MinIO,Vault data
```

### 2.2 물리 구성도 (Physical Architecture)

온프레미스 Kubernetes 클러스터의 물리적 서버 배치와 Pod 분산을 나타냅니다.

```mermaid
flowchart TB
    subgraph DC["데이터센터 (On-Premise)"]
        subgraph Rack1["Rack A"]
            subgraph Master1["Master Node 1<br/>4 CPU / 8GB RAM"]
                etcd1["etcd"]
                apiserver1["kube-apiserver"]
            end
            subgraph Worker1["Worker Node 1<br/>16 CPU / 64GB RAM"]
                FE1["Frontend Pod"]
                BE1["Backend Pod"]
                AI1["AI Service Pod"]
            end
            subgraph Storage1["Storage Node 1<br/>8 CPU / 32GB RAM / 2TB SSD"]
                PG_Primary["PostgreSQL Primary"]
                ES_Data1["ES Data Node 1"]
            end
        end

        subgraph Rack2["Rack B"]
            subgraph Master2["Master Node 2<br/>4 CPU / 8GB RAM"]
                etcd2["etcd"]
                apiserver2["kube-apiserver"]
            end
            subgraph Worker2["Worker Node 2<br/>16 CPU / 64GB RAM"]
                FE2["Frontend Pod"]
                BE2["Backend Pod"]
                AI2["AI Service Pod"]
            end
            subgraph Storage2["Storage Node 2<br/>8 CPU / 32GB RAM / 2TB SSD"]
                PG_Replica["PostgreSQL Replica"]
                ES_Data2["ES Data Node 2"]
            end
        end

        subgraph Rack3["Rack C"]
            subgraph Master3["Master Node 3<br/>4 CPU / 8GB RAM"]
                etcd3["etcd"]
                apiserver3["kube-apiserver"]
            end
            subgraph Worker3["Worker Node 3<br/>16 CPU / 64GB RAM"]
                FE3["Frontend Pod"]
                BE3["Backend Pod"]
                APIGW1["API Gateway Pod"]
            end
            subgraph Storage3["Storage Node 3<br/>8 CPU / 32GB RAM / 2TB SSD"]
                Neo4j1["Neo4j Core 1"]
                ES_Data3["ES Data Node 3"]
            end
        end

        subgraph Rack4["Rack D"]
            subgraph Worker4["Worker Node 4<br/>16 CPU / 64GB RAM"]
                Redis1["Redis Node 1"]
                Redis2["Redis Node 2"]
                Redis3["Redis Node 3"]
                Keycloak1["Keycloak Pod 1"]
            end
            subgraph Storage4["Storage Node 4<br/>8 CPU / 32GB RAM / 2TB SSD"]
                Neo4j2["Neo4j Core 2"]
                Neo4j3["Neo4j Core 3"]
                MinIO1["MinIO Node 1"]
            end
        end

        subgraph SharedInfra["공유 인프라"]
            subgraph Worker5["Worker Node 5<br/>16 CPU / 64GB RAM"]
                Vault1["Vault Pod 1"]
                Vault2["Vault Pod 2"]
                Vault3["Vault Pod 3"]
                APIGW2["API Gateway Pod 2"]
                Keycloak2["Keycloak Pod 2"]
            end
            subgraph MonitoringNode["Monitoring Node<br/>8 CPU / 32GB RAM"]
                Prometheus["Prometheus"]
                Grafana["Grafana"]
                Loki["Loki"]
                AlertMgr["AlertManager"]
            end
        end

        SAN["SAN Storage<br/>10TB NVMe"]
    end

    %% 스토리지 연결
    Storage1 -.-> SAN
    Storage2 -.-> SAN
    Storage3 -.-> SAN
    Storage4 -.-> SAN

    %% 복제 관계
    PG_Primary --> PG_Replica
    ES_Data1 <--> ES_Data2
    ES_Data2 <--> ES_Data3
    Neo4j1 <--> Neo4j2
    Neo4j2 <--> Neo4j3

    %% 스타일
    classDef master fill:#74b9ff,stroke:#0984e3
    classDef worker fill:#55efc4,stroke:#00b894
    classDef storage fill:#ffeaa7,stroke:#fdcb6e
    classDef monitor fill:#fd79a8,stroke:#e84393

    class Master1,Master2,Master3 master
    class Worker1,Worker2,Worker3,Worker4,Worker5 worker
    class Storage1,Storage2,Storage3,Storage4,SAN storage
    class MonitoringNode monitor
```

### 2.3 물리 서버 사양 요약

```mermaid
pie showData
    title "서버 유형별 CPU 코어 분배 (총 124 cores)"
    "Master Nodes (3x4)" : 12
    "Worker Nodes (5x16)" : 80
    "Storage Nodes (4x8)" : 32
```

| 서버 유형 | 수량 | CPU | Memory | Storage | 용도 |
|-----------|------|-----|--------|---------|------|
| Master Node | 3 | 4 cores | 8 GB | 100 GB SSD | K8s Control Plane |
| Worker Node | 5 | 16 cores | 64 GB | 500 GB SSD | Application Pods |
| Storage Node | 4 | 8 cores | 32 GB | 2 TB NVMe | Database, ES, Neo4j |
| Monitoring Node | 1 | 8 cores | 32 GB | 500 GB SSD | Observability Stack |
| **합계** | **13** | **140 cores** | **480 GB** | **12.3 TB** | |

### 2.4 네트워크 구성도 (Network Architecture)

VLAN 분리와 방화벽 정책을 포함한 네트워크 토폴로지입니다.

```mermaid
flowchart TB
    subgraph Internet["인터넷"]
        ExtUsers["👤 외부 사용자"]
        ExtServices["☁️ 외부 서비스<br/>(DeepSeek API)"]
    end

    subgraph Edge["엣지 네트워크 (Edge Network)"]
        FW_Ext["🔥 외부 방화벽<br/>(Palo Alto)"]
        LB_Ext["⚖️ L4 Load Balancer<br/>(F5 BIG-IP)"]
    end

    subgraph DMZ_Net["DMZ (10.0.1.0/24)"]
        direction TB
        NGINX["🚪 Ingress Controller<br/>10.0.1.10-11"]
        WAF_Node["🛡️ WAF<br/>10.0.1.20"]
    end

    subgraph FW_Internal["내부 방화벽"]
        FW_Int["🔥 Internal FW<br/>(iptables/Calico)"]
    end

    subgraph App_Net["Application Network (10.0.10.0/24)"]
        subgraph K8s_Services["Kubernetes Service Network (10.96.0.0/16)"]
            FE_SVC["frontend-svc<br/>10.96.100.1:80"]
            APIGW_SVC["api-gateway-svc<br/>10.96.100.2:8080"]
            BE_SVC["backend-svc<br/>10.96.100.3:8081"]
            AI_SVC["ai-service-svc<br/>10.96.100.4:8000"]
            Auth_SVC["keycloak-svc<br/>10.96.100.5:8080"]
        end

        subgraph K8s_Pods["Kubernetes Pod Network (10.244.0.0/16)"]
            FE_Pods["Frontend Pods<br/>10.244.1.x"]
            BE_Pods["Backend Pods<br/>10.244.2.x"]
            AI_Pods["AI Service Pods<br/>10.244.3.x"]
        end
    end

    subgraph Data_Net["Data Network (10.0.20.0/24)"]
        subgraph DB_Segment["Database Segment"]
            PG_VIP["PostgreSQL VIP<br/>10.0.20.10"]
            PG_Pri["PG Primary<br/>10.0.20.11"]
            PG_Rep["PG Replica<br/>10.0.20.12"]
        end

        subgraph Search_Segment["Search Segment"]
            ES_VIP["Elasticsearch VIP<br/>10.0.20.20"]
            ES1["ES Node 1<br/>10.0.20.21"]
            ES2["ES Node 2<br/>10.0.20.22"]
            ES3["ES Node 3<br/>10.0.20.23"]
        end

        subgraph Graph_Segment["Graph Segment"]
            Neo_VIP["Neo4j VIP<br/>10.0.20.30"]
            Neo1["Neo4j 1<br/>10.0.20.31"]
            Neo2["Neo4j 2<br/>10.0.20.32"]
            Neo3["Neo4j 3<br/>10.0.20.33"]
        end

        subgraph Cache_Segment["Cache Segment"]
            Redis_VIP["Redis VIP<br/>10.0.20.40"]
        end
    end

    subgraph Storage_Net["Storage Network (10.0.30.0/24)"]
        MinIO_VIP["MinIO VIP<br/>10.0.30.10"]
        SAN_Net["SAN Network<br/>10.0.30.100/28"]
    end

    subgraph Mgmt_Net["Management Network (10.0.100.0/24)"]
        Vault_VIP["Vault VIP<br/>10.0.100.10"]
        Prometheus_IP["Prometheus<br/>10.0.100.20"]
        Grafana_IP["Grafana<br/>10.0.100.21"]
        Bastion["Bastion Host<br/>10.0.100.50"]
    end

    %% 트래픽 흐름
    ExtUsers -->|"HTTPS:443"| FW_Ext
    ExtServices <-->|"HTTPS:443"| FW_Ext
    FW_Ext --> LB_Ext
    LB_Ext -->|"HTTP:80"| NGINX
    NGINX --> WAF_Node
    WAF_Node --> FW_Int

    FW_Int --> FE_SVC
    FW_Int --> APIGW_SVC

    FE_SVC --> FE_Pods
    APIGW_SVC --> BE_SVC
    APIGW_SVC --> Auth_SVC
    BE_SVC --> BE_Pods
    BE_SVC --> AI_SVC
    AI_SVC --> AI_Pods

    BE_Pods -->|"TCP:5432"| PG_VIP
    AI_Pods -->|"TCP:9200"| ES_VIP
    AI_Pods -->|"TCP:7687"| Neo_VIP
    BE_Pods -->|"TCP:6379"| Redis_VIP
    BE_Pods -->|"TCP:9000"| MinIO_VIP

    BE_Pods -->|"TCP:8200"| Vault_VIP
    AI_Pods -->|"TCP:8200"| Vault_VIP

    AI_Pods -.->|"HTTPS:443<br/>(Outbound)"| FW_Ext

    %% 스타일
    classDef internet fill:#ff7675,stroke:#d63031
    classDef edge fill:#fab1a0,stroke:#e17055
    classDef dmz fill:#ffeaa7,stroke:#fdcb6e
    classDef app fill:#81ecec,stroke:#00cec9
    classDef data fill:#a29bfe,stroke:#6c5ce7
    classDef storage fill:#55efc4,stroke:#00b894
    classDef mgmt fill:#fd79a8,stroke:#e84393

    class ExtUsers,ExtServices internet
    class FW_Ext,LB_Ext edge
    class NGINX,WAF_Node dmz
    class FE_SVC,APIGW_SVC,BE_SVC,AI_SVC,Auth_SVC,FE_Pods,BE_Pods,AI_Pods app
    class PG_VIP,PG_Pri,PG_Rep,ES_VIP,ES1,ES2,ES3,Neo_VIP,Neo1,Neo2,Neo3,Redis_VIP data
    class MinIO_VIP,SAN_Net storage
    class Vault_VIP,Prometheus_IP,Grafana_IP,Bastion mgmt
```

### 2.5 VLAN 및 서브넷 설계

```mermaid
flowchart LR
    subgraph VLANs["VLAN 구성"]
        VLAN10["VLAN 10<br/>DMZ<br/>10.0.1.0/24"]
        VLAN20["VLAN 20<br/>Application<br/>10.0.10.0/24"]
        VLAN30["VLAN 30<br/>Database<br/>10.0.20.0/24"]
        VLAN40["VLAN 40<br/>Storage<br/>10.0.30.0/24"]
        VLAN100["VLAN 100<br/>Management<br/>10.0.100.0/24"]
    end

    VLAN10 -->|"443, 80"| VLAN20
    VLAN20 -->|"5432, 9200, 7687, 6379"| VLAN30
    VLAN20 -->|"9000"| VLAN40
    VLAN100 -.->|"SSH, SNMP"| VLAN10
    VLAN100 -.->|"SSH, SNMP"| VLAN20
    VLAN100 -.->|"SSH, SNMP"| VLAN30
    VLAN100 -.->|"SSH, SNMP"| VLAN40
```

| VLAN ID | 이름 | 서브넷 | 용도 | 보안 등급 |
|---------|------|--------|------|-----------|
| 10 | DMZ | 10.0.1.0/24 | Ingress, WAF | 낮음 |
| 20 | Application | 10.0.10.0/24 | K8s Pods | 중간 |
| 30 | Database | 10.0.20.0/24 | PG, ES, Neo4j, Redis | 높음 |
| 40 | Storage | 10.0.30.0/24 | MinIO, SAN | 높음 |
| 100 | Management | 10.0.100.0/24 | Monitoring, Vault, Bastion | 최고 |

### 2.6 방화벽 정책 요약

```mermaid
flowchart LR
    subgraph Rules["방화벽 정책"]
        R1["Rule 1: Internet → DMZ<br/>ALLOW TCP 443, 80"]
        R2["Rule 2: DMZ → App<br/>ALLOW TCP 80, 8080"]
        R3["Rule 3: App → Data<br/>ALLOW TCP 5432, 9200, 7687, 6379"]
        R4["Rule 4: App → Storage<br/>ALLOW TCP 9000"]
        R5["Rule 5: App → Internet<br/>ALLOW TCP 443 (DeepSeek)"]
        R6["Rule 6: Mgmt → ALL<br/>ALLOW TCP 22, 161"]
        R7["Rule 7: DEFAULT<br/>DENY ALL"]
    end

    R1 --> R2 --> R3 --> R4 --> R5 --> R6 --> R7
```

| 규칙 | 출발지 | 목적지 | 포트 | 프로토콜 | 동작 |
|------|--------|--------|------|----------|------|
| 1 | Internet | DMZ | 443, 80 | TCP | ALLOW |
| 2 | DMZ | Application | 80, 8080 | TCP | ALLOW |
| 3 | Application | Database | 5432, 9200, 7687, 6379 | TCP | ALLOW |
| 4 | Application | Storage | 9000 | TCP | ALLOW |
| 5 | AI Service | Internet | 443 | TCP | ALLOW (DeepSeek only) |
| 6 | Management | ALL | 22, 161, 8200 | TCP/UDP | ALLOW |
| 7 | ANY | ANY | ANY | ANY | DENY |

### 2.7 환경별 구성

| 환경 | 목적 | 리소스 배율 |
|------|------|-------------|
| **Development** | 개발/테스트 | 0.25x |
| **Staging** | 통합 테스트 | 0.5x |
| **Production** | 운영 서비스 | 1.0x |

### 2.8 데이터 흐름도 (Data Flow Diagram)

시스템 내 주요 데이터 흐름을 나타냅니다.

#### 2.8.1 전체 데이터 흐름 개요

```mermaid
flowchart LR
    subgraph Input["입력 소스"]
        User["👤 사용자"]
        Doc["📄 문서 파일"]
        API["🔗 외부 API"]
    end

    subgraph Process["처리 계층"]
        FE["🖥️ Frontend"]
        BE["⚙️ Backend"]
        AI["🧠 AI Service"]
    end

    subgraph Storage["저장소"]
        PG[("🐘 PostgreSQL<br/>메타데이터")]
        ES[("🔍 Elasticsearch<br/>벡터/청크")]
        Neo[("🕸️ Neo4j<br/>그래프")]
        MinIO[("📦 MinIO<br/>원본 파일")]
        Redis[("💾 Redis<br/>캐시")]
    end

    subgraph External["외부 서비스"]
        DeepSeek["🤖 DeepSeek API"]
    end

    User -->|"요청"| FE
    Doc -->|"업로드"| FE
    FE -->|"API 호출"| BE
    BE <-->|"LLM/검색"| AI
    AI <-->|"추론"| DeepSeek

    BE -->|"CRUD"| PG
    BE -->|"캐싱"| Redis
    BE -->|"파일 저장"| MinIO

    AI -->|"벡터 검색"| ES
    AI -->|"그래프 탐색"| Neo

    PG -.->|"동기화"| ES
    PG -.->|"동기화"| Neo

    classDef input fill:#ffeaa7,stroke:#fdcb6e
    classDef process fill:#81ecec,stroke:#00cec9
    classDef storage fill:#a29bfe,stroke:#6c5ce7
    classDef external fill:#fd79a8,stroke:#e84393

    class User,Doc,API input
    class FE,BE,AI process
    class PG,ES,Neo,MinIO,Redis storage
    class DeepSeek external
```

#### 2.8.2 문서 업로드 및 처리 흐름

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 사용자
    participant FE as 🖥️ Frontend
    participant BE as ⚙️ Backend
    participant MinIO as 📦 MinIO
    participant AI as 🧠 AI Service
    participant DS as 🤖 DeepSeek
    participant PG as 🐘 PostgreSQL
    participant ES as 🔍 Elasticsearch
    participant Neo as 🕸️ Neo4j

    U->>FE: 문서 업로드 (PDF/DOCX)
    FE->>BE: POST /api/v1/documents

    BE->>MinIO: 원본 파일 저장
    MinIO-->>BE: 파일 URL 반환

    BE->>PG: 문서 메타데이터 저장 (pending)
    PG-->>BE: document_id 반환

    BE->>AI: POST /internal/v1/process

    Note over AI: Docling으로 문서 파싱
    Note over AI: HybridChunker로 청킹

    AI->>DS: 메타데이터 추출 요청
    DS-->>AI: document_type, project_name, dates

    AI->>DS: 엔티티/관계 추출 요청
    DS-->>AI: entities, relationships

    Note over AI: BGE-M3로 임베딩 생성

    par 병렬 저장
        AI->>ES: 청크 + 벡터 저장
        AI->>Neo: 엔티티 + 관계 저장
        AI->>PG: 메타데이터 업데이트
    end

    AI-->>BE: 처리 완료 응답
    BE->>PG: 상태 업데이트 (completed)
    BE-->>FE: 업로드 성공 응답
    FE-->>U: 완료 알림
```

#### 2.8.3 Hybrid 검색 흐름

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 사용자
    participant FE as 🖥️ Frontend
    participant BE as ⚙️ Backend
    participant Redis as 💾 Redis
    participant AI as 🧠 AI Service
    participant DS as 🤖 DeepSeek
    participant ES as 🔍 Elasticsearch
    participant Neo as 🕸️ Neo4j

    U->>FE: 검색 쿼리 입력
    FE->>BE: POST /api/v1/search

    BE->>Redis: 캐시 조회

    alt 캐시 히트
        Redis-->>BE: 캐시된 결과 반환
    else 캐시 미스
        BE->>AI: POST /internal/v1/search/hybrid

        AI->>DS: 의도 분석 (DeepSeek-R1)
        DS-->>AI: intent, filters, strategy

        par 병렬 검색
            AI->>ES: 벡터 검색 (BGE-M3)
            ES-->>AI: vector_results
            AI->>Neo: 그래프 탐색
            Neo-->>AI: graph_results
        end

        Note over AI: RRF 결과 융합

        AI->>DS: 답변 합성 (DeepSeek-Chat)
        DS-->>AI: synthesized_answer

        AI-->>BE: 검색 결과 + 답변
        BE->>Redis: 결과 캐싱 (TTL: 5분)
    end

    BE-->>FE: 검색 결과 응답
    FE-->>U: 결과 표시
```

#### 2.8.4 RAG Chat 스트리밍 흐름

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 사용자
    participant FE as 🖥️ Frontend
    participant BE as ⚙️ Backend
    participant AI as 🧠 AI Service
    participant DS as 🤖 DeepSeek
    participant ES as 🔍 Elasticsearch
    participant PG as 🐘 PostgreSQL

    U->>FE: 질문 입력
    FE->>BE: POST /api/v1/chat (SSE)

    BE->>PG: 대화 이력 조회
    PG-->>BE: conversation_history

    BE->>AI: POST /internal/v1/chat/stream

    AI->>ES: 관련 문서 검색
    ES-->>AI: relevant_chunks

    AI->>DS: 스트리밍 요청

    loop 토큰 스트리밍
        DS-->>AI: token_chunk
        AI-->>BE: SSE event
        BE-->>FE: SSE event
        FE-->>U: 실시간 렌더링
    end

    AI-->>BE: [DONE]
    BE->>PG: 대화 이력 저장
    BE-->>FE: stream_end
    FE-->>U: 완료
```

#### 2.8.5 인증/인가 흐름

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 사용자
    participant FE as 🖥️ Frontend
    participant KC as 🔐 Keycloak
    participant BE as ⚙️ Backend
    participant Redis as 💾 Redis
    participant PG as 🐘 PostgreSQL

    U->>FE: 로그인 요청
    FE->>KC: Authorization Code 요청
    KC->>U: 로그인 페이지 리다이렉트
    U->>KC: 자격 증명 입력
    KC-->>FE: Authorization Code

    FE->>KC: Token 교환 요청
    KC-->>FE: Access Token + Refresh Token

    FE->>FE: Token 저장 (메모리)

    Note over FE,BE: 보호된 리소스 요청

    FE->>BE: API 요청 + Bearer Token
    BE->>KC: Token 검증
    KC-->>BE: Token 유효성 + Claims

    BE->>Redis: 세션 정보 저장
    BE->>PG: 사용자 권한 조회
    PG-->>BE: roles, permissions

    BE->>BE: 권한 검사 (@PreAuthorize)
    BE-->>FE: 리소스 응답
    FE-->>U: 데이터 표시
```

#### 2.8.6 데이터 동기화 흐름 (Triple Store)

```mermaid
flowchart TB
    subgraph Source["원본 데이터 (SSOT)"]
        PG[("🐘 PostgreSQL<br/>documents 테이블")]
    end

    subgraph Sync["동기화 프로세스"]
        Event["📢 Domain Event<br/>(CREATE/UPDATE/DELETE)"]
        Queue["📬 Message Queue<br/>(RabbitMQ)"]
        Worker["⚙️ Sync Worker"]
    end

    subgraph Targets["대상 저장소"]
        ES[("🔍 Elasticsearch<br/>knowledge-chunks")]
        Neo[("🕸️ Neo4j<br/>Entity/Relationship")]
    end

    subgraph Monitoring["모니터링"]
        Recon["🔄 Reconciliation Job<br/>(Daily 03:00)"]
        Alert["🚨 Alert Manager"]
    end

    PG -->|"트랜잭션 커밋"| Event
    Event -->|"비동기 발행"| Queue
    Queue -->|"consume"| Worker

    Worker -->|"upsert"| ES
    Worker -->|"merge"| Neo

    Worker -->|"실패 시"| Queue

    Recon -->|"정합성 검증"| PG
    Recon -->|"정합성 검증"| ES
    Recon -->|"정합성 검증"| Neo
    Recon -->|"불일치 감지"| Alert

    classDef source fill:#55efc4,stroke:#00b894
    classDef sync fill:#81ecec,stroke:#00cec9
    classDef target fill:#a29bfe,stroke:#6c5ce7
    classDef monitor fill:#fd79a8,stroke:#e84393

    class PG source
    class Event,Queue,Worker sync
    class ES,Neo target
    class Recon,Alert monitor
```

#### 2.8.7 데이터 저장소별 역할 요약

```mermaid
flowchart LR
    subgraph DataStores["데이터 저장소 역할"]
        PG["🐘 PostgreSQL<br/>━━━━━━━━━━━━<br/>• SSOT (진실의 원천)<br/>• 문서 메타데이터<br/>• 사용자/권한<br/>• 트랜잭션 보장"]

        ES["🔍 Elasticsearch<br/>━━━━━━━━━━━━<br/>• 벡터 검색<br/>• 전문 검색<br/>• 청크 저장<br/>• Zero-Join 메타"]

        Neo["🕸️ Neo4j<br/>━━━━━━━━━━━━<br/>• 지식 그래프<br/>• 엔티티 관계<br/>• 전문가 탐색<br/>• 멀티홉 쿼리"]

        Redis["💾 Redis<br/>━━━━━━━━━━━━<br/>• 세션 캐시<br/>• API 캐시<br/>• Rate Limit<br/>• Pub/Sub"]

        MinIO["📦 MinIO<br/>━━━━━━━━━━━━<br/>• 원본 문서<br/>• 첨부 파일<br/>• 백업 아카이브<br/>• 버전 관리"]
    end

    PG -.->|"동기화"| ES
    PG -.->|"동기화"| Neo
    PG -->|"파일 참조"| MinIO

    classDef pg fill:#336791,stroke:#336791,color:#fff
    classDef es fill:#00bfb3,stroke:#00bfb3,color:#fff
    classDef neo fill:#008cc1,stroke:#008cc1,color:#fff
    classDef redis fill:#dc382d,stroke:#dc382d,color:#fff
    classDef minio fill:#c72c48,stroke:#c72c48,color:#fff

    class PG pg
    class ES es
    class Neo neo
    class Redis redis
    class MinIO minio
```

| 저장소 | 역할 | 데이터 유형 | 일관성 |
|--------|------|-------------|--------|
| PostgreSQL | SSOT | 메타데이터, 사용자, 권한 | Strong |
| Elasticsearch | 검색 엔진 | 벡터, 청크, 비정규화 메타 | Eventual |
| Neo4j | 그래프 DB | 엔티티, 관계 | Eventual |
| Redis | 캐시 | 세션, API 응답 | Volatile |
| MinIO | 오브젝트 | 원본 파일, 첨부 | Strong |

---

## 3. 컨테이너 설계

### 3.1 Docker 이미지 구성

#### 3.1.1 Frontend (React)

```dockerfile
# Dockerfile.frontend
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```yaml
# nginx.conf
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip 압축
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # SPA 라우팅
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 프록시
    location /api/ {
        proxy_pass http://api-gateway:8080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }

    # 정적 자산 캐싱
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 3.1.2 Backend (Spring Boot)

```dockerfile
# Dockerfile.backend
FROM eclipse-temurin:21-jre-alpine AS runtime

# 보안: non-root 사용자
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

WORKDIR /app

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8081/actuator/health || exit 1

# JAR 복사
COPY --chown=appuser:appgroup target/*.jar app.jar

# JVM 최적화
ENV JAVA_OPTS="-XX:+UseContainerSupport \
               -XX:MaxRAMPercentage=75.0 \
               -XX:+UseG1GC \
               -XX:+UseStringDeduplication \
               -Djava.security.egd=file:/dev/./urandom"

EXPOSE 8081 8082

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

#### 3.1.3 AI Service (FastAPI)

```dockerfile
# Dockerfile.ai-service
FROM python:3.11-slim AS base

# 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 가상환경
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션
FROM python:3.11-slim AS runtime

# non-root 사용자
RUN useradd -m -u 1000 appuser
USER appuser

WORKDIR /app

# 가상환경 복사
COPY --from=base /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 소스 복사
COPY --chown=appuser:appuser src/ ./src/

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 3.2 이미지 레지스트리

```yaml
# Harbor 프라이빗 레지스트리
registry:
  url: harbor.company.local
  projects:
    - knowledge-platform/frontend
    - knowledge-platform/backend
    - knowledge-platform/ai-service

  retention_policy:
    development: 10_images
    staging: 20_images
    production: 50_images

  vulnerability_scanning: true
  signing: enabled
```

---

## 4. Kubernetes 배포

> ℹ️ **미구현**: 이하 섹션 4 (Kubernetes 배포) 전체는 참조 설계로만 문서화됨. 실제 배포는 Docker Compose로만 진행되었으며 K8s 배포는 미진행으로 프로젝트 종료.

### 4.1 네임스페이스 구조

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: knowledge-platform
  labels:
    name: knowledge-platform
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: knowledge-platform-staging
---
apiVersion: v1
kind: Namespace
metadata:
  name: knowledge-platform-dev
```

### 4.2 Backend Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: knowledge-platform
  labels:
    app: backend
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8082"
        prometheus.io/path: "/actuator/prometheus"
    spec:
      serviceAccountName: backend-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000

      containers:
      - name: backend
        image: harbor.company.local/knowledge-platform/backend:v1.0.0
        imagePullPolicy: Always

        ports:
        - name: http
          containerPort: 8081
        - name: management
          containerPort: 8082

        env:
        - name: SPRING_PROFILES_ACTIVE
          value: "prod"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        - name: DATABASE_USERNAME
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: username
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: password

        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2000m"
            memory: "2Gi"

        livenessProbe:
          httpGet:
            path: /actuator/health/liveness
            port: management
          initialDelaySeconds: 60
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /actuator/health/readiness
            port: management
          initialDelaySeconds: 30
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: logs
          mountPath: /app/logs

      volumes:
      - name: config
        configMap:
          name: backend-config
      - name: logs
        emptyDir: {}

      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - backend
              topologyKey: kubernetes.io/hostname

      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: backend
```

### 4.3 AI Service Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-service
  namespace: knowledge-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-service
  template:
    metadata:
      labels:
        app: ai-service
    spec:
      containers:
      - name: ai-service
        image: harbor.company.local/knowledge-platform/ai-service:v1.0.0

        ports:
        - containerPort: 8000

        env:
        - name: DEEPSEEK_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-credentials
              key: deepseek-api-key
        - name: ELASTICSEARCH_URL
          value: "http://elasticsearch:9200"
        - name: NEO4J_URI
          value: "bolt://neo4j:7687"
        - name: NEO4J_USER
          valueFrom:
            secretKeyRef:
              name: neo4j-credentials
              key: username
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: neo4j-credentials
              key: password

        resources:
          requests:
            cpu: "1000m"
            memory: "4Gi"
          limits:
            cpu: "4000m"
            memory: "8Gi"

        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 30

        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
```

### 4.4 Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: knowledge-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-service-hpa
  namespace: knowledge-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-service
  minReplicas: 2
  maxReplicas: 6
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
```

### 4.5 Service 정의

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: knowledge-platform
spec:
  type: ClusterIP
  selector:
    app: backend
  ports:
  - name: http
    port: 8081
    targetPort: 8081
  - name: management
    port: 8082
    targetPort: 8082
---
apiVersion: v1
kind: Service
metadata:
  name: ai-service
  namespace: knowledge-platform
spec:
  type: ClusterIP
  selector:
    app: ai-service
  ports:
  - name: http
    port: 8000
    targetPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: knowledge-platform
spec:
  type: ClusterIP
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
```

---

## 5. 네트워크 설계

### 5.1 Ingress 설정

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: knowledge-platform-ingress
  namespace: knowledge-platform
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - knowledge.company.com
    - api.knowledge.company.com
    secretName: knowledge-platform-tls
  rules:
  - host: knowledge.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
  - host: api.knowledge.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 8080
```

### 5.2 Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-network-policy
  namespace: knowledge-platform
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # API Gateway에서만 접근 허용
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8081
  # Prometheus 스크래핑 허용
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 8082
  egress:
  # PostgreSQL
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  # Redis
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  # AI Service
  - to:
    - podSelector:
        matchLabels:
          app: ai-service
    ports:
    - protocol: TCP
      port: 8000
  # DNS
  - to:
    ports:
    - protocol: UDP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-service-network-policy
  namespace: knowledge-platform
spec:
  podSelector:
    matchLabels:
      app: ai-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 8000
  egress:
  # Elasticsearch
  - to:
    - podSelector:
        matchLabels:
          app: elasticsearch
    ports:
    - protocol: TCP
      port: 9200
  # Neo4j
  - to:
    - podSelector:
        matchLabels:
          app: neo4j
    ports:
    - protocol: TCP
      port: 7687
  # DeepSeek API (외부)
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
    ports:
    - protocol: TCP
      port: 443
```

### 5.3 서비스 메시 (Istio)

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: backend-vs
  namespace: knowledge-platform
spec:
  hosts:
  - backend
  http:
  - route:
    - destination:
        host: backend
        port:
          number: 8081
    timeout: 30s
    retries:
      attempts: 3
      perTryTimeout: 10s
      retryOn: gateway-error,connect-failure,refused-stream
---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: backend-dr
  namespace: knowledge-platform
spec:
  host: backend
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
    loadBalancer:
      simple: LEAST_CONN
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

---

## 6. 스토리지 설계

### 6.1 Persistent Volume 설정

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-storage
provisioner: kubernetes.io/vsphere-volume  # 또는 다른 프로비저너
parameters:
  storagePolicyName: "SSD-High-Performance"
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgresql-data
  namespace: knowledge-platform
spec:
  storageClassName: fast-storage
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: elasticsearch-data
  namespace: knowledge-platform
spec:
  storageClassName: fast-storage
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 500Gi
```

### 6.2 MinIO (Object Storage)

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: minio
  namespace: knowledge-platform
spec:
  serviceName: minio-headless
  replicas: 4
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
      - name: minio
        image: minio/minio:RELEASE.2024-01-01T00-00-00Z
        args:
        - server
        - http://minio-{0...3}.minio-headless.knowledge-platform.svc.cluster.local/data
        - --console-address
        - ":9001"
        env:
        - name: MINIO_ROOT_USER
          valueFrom:
            secretKeyRef:
              name: minio-credentials
              key: root-user
        - name: MINIO_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: minio-credentials
              key: root-password
        ports:
        - containerPort: 9000
          name: api
        - containerPort: 9001
          name: console
        volumeMounts:
        - name: data
          mountPath: /data
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      storageClassName: fast-storage
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 100Gi
```

### 6.3 스토리지 용량 계획

| 구성 요소 | 초기 용량 | 1년 후 예상 | 비고 |
|-----------|-----------|-------------|------|
| PostgreSQL | 100 GB | 300 GB | 메타데이터, 사용자 |
| Elasticsearch | 500 GB | 2 TB | 벡터 + 청크 |
| Neo4j | 50 GB | 200 GB | 그래프 데이터 |
| MinIO | 1 TB | 5 TB | 원본 문서 |
| 로그 | 100 GB | 500 GB | 30일 보관 |

---

## 7. 데이터베이스 인프라

### 7.1 PostgreSQL HA (Patroni)

```yaml
apiVersion: acid.zalan.do/v1
kind: postgresql
metadata:
  name: knowledge-db
  namespace: knowledge-platform
spec:
  teamId: "knowledge"
  numberOfInstances: 2

  postgresql:
    version: "16"
    parameters:
      shared_buffers: "2GB"
      work_mem: "256MB"
      maintenance_work_mem: "512MB"
      max_connections: "200"
      log_statement: "ddl"

  volume:
    size: 100Gi
    storageClass: fast-storage

  resources:
    requests:
      cpu: "1"
      memory: "4Gi"
    limits:
      cpu: "4"
      memory: "8Gi"

  patroni:
    initdb:
      encoding: "UTF8"
      locale: "C"
      data-checksums: "true"
    pg_hba:
    - local   all  all                trust
    - host    all  all  127.0.0.1/32  md5
    - host    all  all  10.0.0.0/8    md5
```

### 7.2 Elasticsearch Cluster

```yaml
apiVersion: elasticsearch.k8s.elastic.co/v1
kind: Elasticsearch
metadata:
  name: knowledge-es
  namespace: knowledge-platform
spec:
  version: 8.11.0
  nodeSets:
  - name: master
    count: 3
    config:
      node.roles: ["master"]
    volumeClaimTemplates:
    - metadata:
        name: elasticsearch-data
      spec:
        accessModes:
        - ReadWriteOnce
        resources:
          requests:
            storage: 10Gi
        storageClassName: fast-storage
    podTemplate:
      spec:
        containers:
        - name: elasticsearch
          resources:
            requests:
              cpu: "500m"
              memory: "2Gi"
            limits:
              cpu: "1"
              memory: "4Gi"

  - name: data
    count: 3
    config:
      node.roles: ["data", "ingest"]
    volumeClaimTemplates:
    - metadata:
        name: elasticsearch-data
      spec:
        accessModes:
        - ReadWriteOnce
        resources:
          requests:
            storage: 500Gi
        storageClassName: fast-storage
    podTemplate:
      spec:
        containers:
        - name: elasticsearch
          resources:
            requests:
              cpu: "2"
              memory: "8Gi"
            limits:
              cpu: "4"
              memory: "16Gi"
```

### 7.3 Neo4j Cluster

```yaml
apiVersion: neo4j.com/v1
kind: Neo4j
metadata:
  name: knowledge-graph
  namespace: knowledge-platform
spec:
  core:
    standalone: false
    numberOfMembers: 3

  image: neo4j:5.15-enterprise

  volumes:
    data:
      mode: defaultStorageClass
      defaultStorageClass:
        requests:
          storage: 50Gi

  neo4j:
    edition: "enterprise"
    resources:
      cpu: "2"
      memory: "8Gi"
    config:
      dbms.memory.heap.initial_size: "4g"
      dbms.memory.heap.max_size: "4g"
      dbms.memory.pagecache.size: "2g"
```

### 7.4 Redis Cluster

```yaml
apiVersion: redis.redis.opstreelabs.in/v1beta2
kind: RedisCluster
metadata:
  name: knowledge-cache
  namespace: knowledge-platform
spec:
  clusterSize: 3
  clusterVersion: v7

  kubernetesConfig:
    image: redis:7.2-alpine
    imagePullPolicy: IfNotPresent
    resources:
      requests:
        cpu: "500m"
        memory: "1Gi"
      limits:
        cpu: "1"
        memory: "2Gi"

  redisExporter:
    enabled: true
    image: oliver006/redis_exporter:latest

  storage:
    volumeClaimTemplate:
      spec:
        accessModes:
        - ReadWriteOnce
        resources:
          requests:
            storage: 10Gi
        storageClassName: fast-storage
```

---

## 8. 모니터링 및 로깅

### 8.1 Prometheus Stack

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: backend-monitor
  namespace: monitoring
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: backend
  namespaceSelector:
    matchNames:
    - knowledge-platform
  endpoints:
  - port: management
    path: /actuator/prometheus
    interval: 30s
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ai-service-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: ai-service
  namespaceSelector:
    matchNames:
    - knowledge-platform
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### 8.2 Grafana 대시보드

```json
{
  "dashboard": {
    "title": "Knowledge Platform Overview",
    "panels": [
      {
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(http_server_requests_seconds_count{application='knowledge-platform'}[5m])) by (uri)",
            "legendFormat": "{{uri}}"
          }
        ]
      },
      {
        "title": "Response Time P95",
        "type": "stat",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket{application='knowledge-platform'}[5m])) by (le))"
          }
        ]
      },
      {
        "title": "AI Service Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(llm_token_usage_total[1h])) by (model)"
          }
        ]
      },
      {
        "title": "Search Latency",
        "type": "heatmap",
        "targets": [
          {
            "expr": "sum(rate(search_latency_seconds_bucket[5m])) by (le)"
          }
        ]
      }
    ]
  }
}
```

### 8.3 Loki (로그 수집)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: promtail-config
  namespace: monitoring
data:
  promtail.yaml: |
    server:
      http_listen_port: 9080

    positions:
      filename: /tmp/positions.yaml

    clients:
      - url: http://loki:3100/loki/api/v1/push

    scrape_configs:
      - job_name: kubernetes-pods
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            target_label: app
          - source_labels: [__meta_kubernetes_namespace]
            target_label: namespace
        pipeline_stages:
          - json:
              expressions:
                level: level
                message: message
                traceId: traceId
          - labels:
              level:
              traceId:
```

### 8.4 알림 규칙 (AlertManager)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: knowledge-platform-alerts
  namespace: monitoring
spec:
  groups:
  - name: knowledge-platform
    rules:
    # 고가용성 알림
    - alert: BackendPodDown
      expr: kube_deployment_status_replicas_available{deployment="backend"} < 2
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Backend pods insufficient"
        description: "Less than 2 backend pods are running"

    # API 응답 시간
    - alert: HighApiLatency
      expr: histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket{application="knowledge-platform"}[5m])) by (le)) > 1
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "High API latency detected"
        description: "P95 latency is above 1 second"

    # AI Service 오류율
    - alert: AIServiceHighErrorRate
      expr: sum(rate(http_requests_total{app="ai-service",status=~"5.."}[5m])) / sum(rate(http_requests_total{app="ai-service"}[5m])) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "AI Service high error rate"
        description: "Error rate is above 5%"

    # Elasticsearch 클러스터
    - alert: ElasticsearchClusterRed
      expr: elasticsearch_cluster_health_status{color="red"} == 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Elasticsearch cluster is RED"

    # 디스크 용량
    - alert: PersistentVolumeUsageHigh
      expr: kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes > 0.85
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "PV usage above 85%"
```

---

## 9. CI/CD 파이프라인

> ℹ️ **미구현**: CI/CD 파이프라인 (GitLab CI, ArgoCD) 은 미구현으로 종료. 수동 docker-compose up/down 방식으로만 운영됨.

### 9.1 GitLab CI/CD

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - security
  - deploy-dev
  - deploy-staging
  - deploy-prod

variables:
  DOCKER_REGISTRY: harbor.company.local
  PROJECT_NAME: knowledge-platform

# === 빌드 ===
build-backend:
  stage: build
  image: eclipse-temurin:21-jdk
  script:
    - ./gradlew build -x test
    - docker build -t $DOCKER_REGISTRY/$PROJECT_NAME/backend:$CI_COMMIT_SHA -f Dockerfile.backend .
    - docker push $DOCKER_REGISTRY/$PROJECT_NAME/backend:$CI_COMMIT_SHA
  artifacts:
    paths:
      - build/

build-ai-service:
  stage: build
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - python -m pytest tests/ --cov=src
    - docker build -t $DOCKER_REGISTRY/$PROJECT_NAME/ai-service:$CI_COMMIT_SHA -f Dockerfile.ai-service .
    - docker push $DOCKER_REGISTRY/$PROJECT_NAME/ai-service:$CI_COMMIT_SHA

build-frontend:
  stage: build
  image: node:20
  script:
    - npm ci
    - npm run build
    - npm run test:ci
    - docker build -t $DOCKER_REGISTRY/$PROJECT_NAME/frontend:$CI_COMMIT_SHA -f Dockerfile.frontend .
    - docker push $DOCKER_REGISTRY/$PROJECT_NAME/frontend:$CI_COMMIT_SHA

# === 테스트 ===
test-integration:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker-compose -f docker-compose.test.yml up -d
    - ./run-integration-tests.sh
    - docker-compose -f docker-compose.test.yml down

# === 보안 스캔 ===
security-scan:
  stage: security
  image: aquasec/trivy:latest
  script:
    - trivy image --severity HIGH,CRITICAL $DOCKER_REGISTRY/$PROJECT_NAME/backend:$CI_COMMIT_SHA
    - trivy image --severity HIGH,CRITICAL $DOCKER_REGISTRY/$PROJECT_NAME/ai-service:$CI_COMMIT_SHA
    - trivy image --severity HIGH,CRITICAL $DOCKER_REGISTRY/$PROJECT_NAME/frontend:$CI_COMMIT_SHA

sonarqube-analysis:
  stage: security
  image: sonarsource/sonar-scanner-cli
  script:
    - sonar-scanner -Dsonar.projectKey=$PROJECT_NAME -Dsonar.sources=.

# === 배포 ===
deploy-dev:
  stage: deploy-dev
  image: bitnami/kubectl:latest
  script:
    - kubectl config use-context dev-cluster
    - helm upgrade --install knowledge-platform ./helm/knowledge-platform
        --namespace knowledge-platform-dev
        --set image.tag=$CI_COMMIT_SHA
        --set environment=development
  environment:
    name: development
  only:
    - develop

deploy-staging:
  stage: deploy-staging
  image: bitnami/kubectl:latest
  script:
    - kubectl config use-context staging-cluster
    - helm upgrade --install knowledge-platform ./helm/knowledge-platform
        --namespace knowledge-platform-staging
        --set image.tag=$CI_COMMIT_SHA
        --set environment=staging
  environment:
    name: staging
  only:
    - main
  when: manual

deploy-prod:
  stage: deploy-prod
  image: bitnami/kubectl:latest
  script:
    - kubectl config use-context prod-cluster
    - helm upgrade --install knowledge-platform ./helm/knowledge-platform
        --namespace knowledge-platform
        --set image.tag=$CI_COMMIT_SHA
        --set environment=production
  environment:
    name: production
  only:
    - main
  when: manual
  rules:
    - if: $CI_COMMIT_TAG
```

### 9.2 Helm Chart 구조

```
helm/knowledge-platform/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-staging.yaml
├── values-prod.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── ai-service-deployment.yaml
│   ├── ai-service-service.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── hpa.yaml
│   └── networkpolicy.yaml
└── charts/
    ├── postgresql/
    ├── elasticsearch/
    └── redis/
```

```yaml
# values-prod.yaml
replicaCount:
  backend: 3
  aiService: 2
  frontend: 3

resources:
  backend:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2000m"
      memory: "2Gi"
  aiService:
    requests:
      cpu: "1000m"
      memory: "4Gi"
    limits:
      cpu: "4000m"
      memory: "8Gi"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: knowledge.company.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: knowledge-tls
      hosts:
        - knowledge.company.com
```

### 9.3 ArgoCD (GitOps)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: knowledge-platform
  namespace: argocd
spec:
  project: default

  source:
    repoURL: https://gitlab.company.local/knowledge-platform/infra.git
    targetRevision: main
    path: helm/knowledge-platform
    helm:
      valueFiles:
        - values-prod.yaml

  destination:
    server: https://kubernetes.default.svc
    namespace: knowledge-platform

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

---

## 10. 보안 인프라

> ℹ️ **미구현**: HashiCorp Vault, Pod Security Policy 등 보안 인프라는 미구현. 시크릿 관리는 Docker Compose .env 파일 방식으로 운영됨.

### 10.1 HashiCorp Vault

```yaml
apiVersion: vault.hashicorp.com/v1
kind: Vault
metadata:
  name: vault
  namespace: vault
spec:
  size: 3

  config:
    storage:
      postgresql:
        connection_url: "postgres://vault:xxx@postgresql:5432/vault"
        table: "vault_kv_store"

    listener:
      tcp:
        address: "0.0.0.0:8200"
        tls_disable: false
        tls_cert_file: "/vault/tls/tls.crt"
        tls_key_file: "/vault/tls/tls.key"

    ui: true

    seal:
      transit:
        address: "https://vault-transit.company.local:8200"
        key_name: "autounseal"
```

```bash
# Vault 정책 설정
vault policy write knowledge-platform - <<EOF
# PostgreSQL 비밀번호
path "secret/data/knowledge-platform/database/*" {
  capabilities = ["read"]
}

# DeepSeek API 키
path "secret/data/knowledge-platform/ai/*" {
  capabilities = ["read"]
}

# 암호화 키
path "transit/encrypt/knowledge-platform" {
  capabilities = ["update"]
}

path "transit/decrypt/knowledge-platform" {
  capabilities = ["update"]
}
EOF
```

### 10.2 Pod Security Policy

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
spec:
  privileged: false
  runAsUser:
    rule: MustRunAsNonRoot
  seLinux:
    rule: RunAsAny
  fsGroup:
    rule: MustRunAs
    ranges:
    - min: 1
      max: 65535
  supplementalGroups:
    rule: MustRunAs
    ranges:
    - min: 1
      max: 65535
  volumes:
  - 'configMap'
  - 'emptyDir'
  - 'projected'
  - 'secret'
  - 'downwardAPI'
  - 'persistentVolumeClaim'
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
  - ALL
```

### 10.3 TLS 인증서 관리

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@company.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: knowledge-platform-cert
  namespace: knowledge-platform
spec:
  secretName: knowledge-platform-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - knowledge.company.com
  - api.knowledge.company.com
```

---

## 11. 재해 복구

### 11.1 백업 전략

```yaml
# Velero 백업 스케줄
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: knowledge-platform-daily
  namespace: velero
spec:
  schedule: "0 2 * * *"  # 매일 02:00
  template:
    includedNamespaces:
    - knowledge-platform
    includedResources:
    - persistentvolumeclaims
    - configmaps
    - secrets
    storageLocation: default
    ttl: 720h  # 30일 보관
---
# PostgreSQL 백업
apiVersion: postgresql.cnpg.io/v1
kind: ScheduledBackup
metadata:
  name: knowledge-db-backup
spec:
  schedule: "0 */6 * * *"  # 6시간마다
  backupOwnerReference: self
  cluster:
    name: knowledge-db
  target: prefer-standby
```

### 11.2 RTO/RPO 목표

| 시스템 | RPO | RTO | 백업 주기 |
|--------|-----|-----|-----------|
| PostgreSQL | 1시간 | 2시간 | 6시간 + WAL |
| Elasticsearch | 4시간 | 4시간 | 일일 |
| Neo4j | 4시간 | 4시간 | 일일 |
| MinIO | 24시간 | 8시간 | 일일 |
| Kubernetes | 1시간 | 1시간 | 일일 + GitOps |

### 11.3 DR 사이트

```
┌─────────────────────────────────────────────────────────────────┐
│                       Primary Site                               │
│  [Kubernetes Cluster]                                            │
│  - knowledge-platform namespace                                  │
│  - All application pods                                          │
│  - Primary databases                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ Replication
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DR Site                                   │
│  [Standby Kubernetes Cluster]                                    │
│  - PostgreSQL Replica (Streaming)                                │
│  - Elasticsearch Cross-Cluster Replication                       │
│  - Neo4j Replica                                                 │
│  - MinIO Bucket Replication                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12. 비용 추정

### 12.1 온프레미스 리소스 요구사항

| 구성 요소 | CPU | Memory | Storage | 수량 |
|-----------|-----|--------|---------|------|
| Master Node | 4 | 8 GB | 100 GB | 3 |
| Worker Node | 16 | 64 GB | 500 GB | 5 |
| Storage Node | 8 | 32 GB | 2 TB | 4 |
| **합계** | **124 cores** | **448 GB** | **10.3 TB** | 12 |

### 12.2 라이선스 비용 (연간)

| 소프트웨어 | 라이선스 | 비용 (예상) |
|------------|----------|-------------|
| Red Hat OpenShift | Enterprise | 포함 |
| Neo4j Enterprise | 3-node cluster | $50,000 |
| Elasticsearch (Self-managed) | Basic (Free) | $0 |
| HashiCorp Vault Enterprise | HA Cluster | $20,000 |
| **합계** | | **$70,000** |

### 12.3 외부 서비스 비용 (월간)

| 서비스 | 사용량 | 비용 |
|--------|--------|------|
| DeepSeek API | 10M tokens | $140 |
| 도메인/SSL | - | $10 |
| **합계** | | **$150/월** |

---

## 13. 부록

### 13.1 환경 변수 목록

```yaml
# Backend
SPRING_PROFILES_ACTIVE: prod
DATABASE_URL: jdbc:postgresql://postgresql:5432/knowledge
DATABASE_USERNAME: <from-vault>
DATABASE_PASSWORD: <from-vault>
REDIS_HOST: redis
REDIS_PORT: 6379
AI_SERVICE_URL: http://ai-service:8000

# AI Service
DEEPSEEK_API_KEY: <from-vault>
ELASTICSEARCH_URL: http://elasticsearch:9200
NEO4J_URI: bolt://neo4j:7687
NEO4J_USER: <from-vault>
NEO4J_PASSWORD: <from-vault>
REDIS_URL: redis://redis:6379

# Frontend
VITE_API_URL: https://api.knowledge.company.com
VITE_AUTH_URL: https://auth.knowledge.company.com
```

### 13.2 포트 맵

| 서비스 | 내부 포트 | 외부 포트 | 프로토콜 |
|--------|-----------|-----------|----------|
| Frontend | 80 | 443 | HTTPS |
| API Gateway | 8080 | 443 | HTTPS |
| Backend | 8081 | - | - |
| Backend (Mgmt) | 8082 | - | - |
| AI Service | 8000 | - | - |
| PostgreSQL | 5432 | - | - |
| Elasticsearch | 9200 | - | - |
| Neo4j (Bolt) | 7687 | - | - |
| Redis | 6379 | - | - |
| Vault | 8200 | - | - |

### 13.3 헬스체크 엔드포인트

| 서비스 | 엔드포인트 | 기대 응답 |
|--------|------------|-----------|
| Backend | /actuator/health | {"status": "UP"} |
| AI Service | /health | {"status": "ok"} |
| Frontend | / | HTTP 200 |
| PostgreSQL | pg_isready | 0 |
| Elasticsearch | /_cluster/health | "green" |
| Neo4j | /db/neo4j/cluster/available | true |
| Redis | PING | PONG |

---

**문서 끝**

**작성 완료**: 2026-01-16
**검토 필요**: 네트워크팀, 보안팀, DBA팀
**다음 단계**: 인프라 구축 POC

---

## 현행화 이력

| 일자 | 작성자 | 내용 |
|------|--------|------|
| 2026-02-20 | Claude (doc-agent) | 프로젝트 종료 후 현행화 — K8s 참조 설계 미구현, Docker Compose 18개 컨테이너 단일 노드로 운영 종료 반영 |
