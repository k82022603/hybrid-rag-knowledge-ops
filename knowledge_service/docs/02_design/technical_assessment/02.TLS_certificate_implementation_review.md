# TLS 인증서 구현 검토

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | TLS 인증서 구현 검토 |
| **버전** | 1.0 |
| **작성일** | 2026-01-16 |
| **작성자** | Claude AI |
| **상태** | 검토 완료 |

---

## 1. 검토 배경

### 1.1 검토 목적

민감 데이터 암호화 설계서에서 정의된 TLS/mTLS 인증서의 실제 구현 시점과 방법을 명확히 하여, 개발 단계별로 적절한 보안 수준을 적용합니다.

### 1.2 질문에 대한 답변

> "인증서 설치해야하는 것인가?"

**현재 단계(설계)에서는 인증서 설치가 필요하지 않습니다.**

---

## 2. 인증서 종류 및 용도

### 2.1 인증서 유형 분류

```
┌─────────────────────────────────────────────────────────────┐
│                    인증서 종류 및 적용 위치                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [1] 외부 TLS 인증서                                        │
│      └─ 용도: HTTPS 통신 (Frontend ↔ Gateway)               │
│      └─ 발급: Let's Encrypt 또는 상용 CA                    │
│                                                             │
│  [2] 내부 mTLS 인증서                                       │
│      └─ 용도: 서비스 간 통신 (Backend ↔ AI Service)         │
│      └─ 발급: 자체 CA (Internal CA)                         │
│                                                             │
│  [3] DB 연결 TLS 인증서                                     │
│      └─ 용도: 데이터베이스 연결 암호화                       │
│      └─ 발급: 클라우드 제공 또는 자체 CA                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 상세 용도

| 인증서 | 적용 구간 | 발급 방법 | 비용 |
|--------|----------|----------|------|
| **외부 TLS** | Client → Nginx → Gateway | Let's Encrypt | 무료 |
| **Gateway TLS** | Gateway 서버 인증서 | Let's Encrypt | 무료 |
| **mTLS (Backend)** | Backend ↔ AI Service | 자체 CA | 무료 |
| **PostgreSQL TLS** | Backend → PostgreSQL | 자체/클라우드 | 무료 |
| **Elasticsearch TLS** | Backend → ES | 자체/클라우드 | 무료 |
| **Neo4j TLS** | AI Service → Neo4j | 자체/클라우드 | 무료 |

---

## 3. 환경별 인증서 필요 여부

### 3.1 환경별 정리

| 환경 | 외부 TLS | 내부 mTLS | DB TLS | 비고 |
|------|---------|----------|--------|------|
| **로컬 개발** | 불필요 | 불필요 | 불필요 | HTTP로 개발 |
| **Docker Compose (개발)** | 선택적 | 선택적 | 선택적 | 자체 서명 가능 |
| **Docker Compose (테스트)** | 권장 | 권장 | 권장 | 자체 서명 |
| **스테이징** | 필수 | 필수 | 필수 | 정식 또는 자체 CA |
| **운영 (Production)** | **필수** | **필수** | **필수** | 정식 CA |

### 3.2 현재 단계 판단

```
현재 단계: 설계 (Phase 1)
    │
    ▼
┌─────────────────────────────────────────┐
│  인증서 설치 필요 없음                   │
│                                         │
│  - 설계서 작성 및 검토 중               │
│  - 코드 구현 전 단계                    │
│  - 로컬 개발 환경 준비 단계             │
└─────────────────────────────────────────┘
    │
    ▼
다음 단계: 구현 (Phase 2)
    │
    ▼
┌─────────────────────────────────────────┐
│  Docker Compose 환경 구성 시 검토        │
│                                         │
│  - 개발 편의를 위해 HTTP 사용 가능       │
│  - 통합 테스트 시 자체 서명 인증서 적용  │
└─────────────────────────────────────────┘
    │
    ▼
배포 단계: 스테이징/운영 (Phase 3)
    │
    ▼
┌─────────────────────────────────────────┐
│  정식 인증서 설치 필수                   │
│                                         │
│  - Let's Encrypt 또는 상용 CA           │
│  - 자체 CA로 내부 mTLS 구성             │
│  - DB 연결 TLS 활성화                   │
└─────────────────────────────────────────┘
```

---

## 4. 단계별 구현 계획

### 4.1 Phase 1: 설계 (현재)

**인증서 작업: 없음**

```
수행 사항:
- TLS/mTLS 설계 문서 작성 ✓
- 인증서 구조 정의 ✓
- 암호화 알고리즘 선정 ✓

산출물:
- data_encryption_design.md ✓
- 본 문서 (TLS 인증서 구현 검토) ✓
```

### 4.2 Phase 2: 구현 (개발 환경)

**인증서 작업: 선택적**

```yaml
# docker-compose.yml (개발 환경 - HTTP)
services:
  gateway:
    ports:
      - "8080:8080"  # HTTP
    environment:
      - SPRING_PROFILES_ACTIVE=dev
      - SERVER_SSL_ENABLED=false

  backend:
    environment:
      - AI_SERVICE_URL=http://ai-service:8000  # HTTP
```

**자체 서명 인증서 테스트 시:**

```bash
# 자체 서명 인증서 생성 (개발용)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout dev-key.pem -out dev-cert.pem \
  -subj "/CN=localhost"
```

### 4.3 Phase 3: 배포 (스테이징/운영)

**인증서 작업: 필수**

#### 4.3.1 외부 TLS (Let's Encrypt)

```bash
# Certbot으로 Let's Encrypt 인증서 발급
sudo certbot certonly --nginx -d api.company.com

# 자동 갱신 설정
sudo certbot renew --dry-run
```

#### 4.3.2 내부 mTLS (자체 CA)

```bash
#!/bin/bash
# generate_internal_certs.sh

# 1. Root CA 생성
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -sha256 -days 3650 \
  -key ca-key.pem -out ca-cert.pem \
  -subj "/C=KR/ST=Seoul/O=Company/CN=Internal CA"

# 2. Backend 인증서
openssl genrsa -out backend-key.pem 2048
openssl req -new -key backend-key.pem -out backend.csr \
  -subj "/C=KR/ST=Seoul/O=Company/CN=backend"
openssl x509 -req -sha256 -days 365 \
  -in backend.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out backend-cert.pem

# 3. AI Service 인증서
openssl genrsa -out ai-service-key.pem 2048
openssl req -new -key ai-service-key.pem -out ai-service.csr \
  -subj "/C=KR/ST=Seoul/O=Company/CN=ai-service"
openssl x509 -req -sha256 -days 365 \
  -in ai-service.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out ai-service-cert.pem

# 4. PKCS12 변환 (Java용)
openssl pkcs12 -export -out backend-keystore.p12 \
  -inkey backend-key.pem -in backend-cert.pem \
  -certfile ca-cert.pem -password pass:changeit
```

#### 4.3.3 DB 연결 TLS

```yaml
# PostgreSQL TLS 연결
spring:
  datasource:
    url: jdbc:postgresql://db-host:5432/knowledge?ssl=true&sslmode=verify-full
    hikari:
      data-source-properties:
        sslMode: verify-full
        sslRootCert: /app/certs/ca-cert.pem
```

---

## 5. 인증서 관리 체크리스트

### 5.1 개발 환경

| 항목 | 필요 | 비고 |
|------|------|------|
| 외부 TLS 인증서 | X | HTTP 사용 |
| 내부 mTLS 인증서 | X | HTTP 사용 |
| DB TLS 인증서 | X | 로컬 DB 사용 |
| 자체 서명 인증서 | △ | 테스트 시 선택 |

### 5.2 스테이징 환경

| 항목 | 필요 | 비고 |
|------|------|------|
| 외부 TLS 인증서 | O | Let's Encrypt |
| 내부 mTLS 인증서 | O | 자체 CA |
| DB TLS 인증서 | O | 자체 CA |
| 인증서 갱신 자동화 | O | Certbot cron |

### 5.3 운영 환경

| 항목 | 필요 | 비고 |
|------|------|------|
| 외부 TLS 인증서 | **필수** | Let's Encrypt 또는 상용 |
| 내부 mTLS 인증서 | **필수** | 자체 CA |
| DB TLS 인증서 | **필수** | 클라우드 제공 또는 자체 |
| 인증서 갱신 자동화 | **필수** | 자동 갱신 + 알림 |
| 인증서 만료 모니터링 | **필수** | 30일 전 알림 |

---

## 6. 인증서 비용 분석

### 6.1 무료 옵션

| 인증서 | 제공자 | 유효 기간 | 비고 |
|--------|--------|----------|------|
| **Let's Encrypt** | ISRG | 90일 (자동 갱신) | 도메인 검증 (DV) |
| **ZeroSSL** | ZeroSSL | 90일 | 무료 티어 3개 |
| **자체 CA** | 자체 | 설정 가능 | 내부 통신용 |

### 6.2 유료 옵션 (필요 시)

| 인증서 | 제공자 | 연간 비용 | 용도 |
|--------|--------|----------|------|
| OV SSL | DigiCert | $200~500 | 조직 검증 필요 시 |
| EV SSL | DigiCert | $500~1000 | 주소창 녹색 표시 |
| Wildcard | Sectigo | $100~300 | 서브도메인 다수 시 |

### 6.3 권장 사항

```
운영 환경 권장:
├── 외부 TLS: Let's Encrypt (무료)
│   └── 자동 갱신 설정 필수
│
├── 내부 mTLS: 자체 CA (무료)
│   └── 연 1회 갱신
│
└── DB TLS: 클라우드 제공 (포함) 또는 자체 CA
    └── 클라우드 DB 사용 시 자동 제공
```

---

## 7. 인증서 보안 고려사항

### 7.1 개인 키 보호

```bash
# 개인 키 파일 권한 제한
chmod 400 *.key *.pem

# 소유자 제한
chown root:root *.key *.pem
```

### 7.2 인증서 저장 위치

| 환경 | 저장 위치 | 접근 제어 |
|------|----------|----------|
| 개발 | 로컬 파일 | 개발자만 |
| Docker | Docker Secret / Volume | 컨테이너 내부 |
| K8s | Kubernetes Secret | RBAC |
| 운영 | HashiCorp Vault | 정책 기반 |

### 7.3 인증서 갱신 알림

```yaml
# 인증서 만료 모니터링 (Prometheus)
groups:
  - name: ssl-certificates
    rules:
      - alert: SSLCertificateExpiringSoon
        expr: ssl_certificate_expiry_seconds < 2592000  # 30일
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "SSL 인증서 만료 임박"
          description: "{{ $labels.instance }}의 인증서가 30일 내 만료됩니다"
```

---

## 8. 결론

### 8.1 현재 단계 결론

| 질문 | 답변 |
|------|------|
| 지금 인증서 설치 필요? | **아니오** |
| 언제 필요? | 스테이징/운영 배포 시 |
| 개발 중에는? | HTTP로 진행 가능 |

### 8.2 단계별 요약

```
Phase 1 (현재: 설계)
└── 인증서 작업 없음
└── 설계 문서만 작성

Phase 2 (구현)
└── HTTP로 개발
└── 통합 테스트 시 자체 서명 인증서 선택적 사용

Phase 3 (배포)
└── Let's Encrypt로 외부 TLS
└── 자체 CA로 내부 mTLS
└── DB TLS 활성화
```

### 8.3 향후 작업

| 시점 | 작업 | 담당 |
|------|------|------|
| 구현 시작 시 | 자체 서명 인증서 생성 스크립트 준비 | 개발 |
| 스테이징 배포 전 | Let's Encrypt 발급 + 자체 CA 구성 | 인프라 |
| 운영 배포 전 | 인증서 갱신 자동화 + 모니터링 설정 | 인프라 |

---

## 9. 관련 문서

- [민감 데이터 암호화 설계서](../data_encryption_design.md)
- [API 아키텍처 설계 방향 검토](./01.API_architecture_design_review.md)
- [인증/권한 설계서](../authentication_authorization_detailed_design.md)

---

**문서 끝**
