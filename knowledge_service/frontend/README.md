# Knowledge Portal Frontend

React 18 기반 지식 검색 포털 UI

## Tech Stack

- **Framework**: React 18, TypeScript 5.4+
- **Build Tool**: Vite 5.x
- **State Management**: Redux Toolkit, React Query
- **UI Library**: MUI v5 (Material-UI)
- **Styling**: Emotion
- **HTTP Client**: Axios

## Project Structure

```
frontend/
├── src/
│   ├── components/       # UI 컴포넌트
│   │   ├── common/       # 공통 컴포넌트 (Layout, Header, Sidebar)
│   │   ├── search/       # 검색 컴포넌트 (ChatSearch, KeywordSearch)
│   │   ├── knowledge/    # 지식 관리 컴포넌트
│   │   └── dashboard/    # 대시보드 컴포넌트
│   ├── pages/            # 페이지 컴포넌트
│   ├── hooks/            # 커스텀 훅
│   ├── services/         # API 서비스
│   ├── store/            # Redux 스토어 및 슬라이스
│   ├── types/            # TypeScript 타입 정의
│   ├── utils/            # 유틸리티 함수
│   └── assets/           # 정적 자원
├── public/               # 정적 파일
├── nginx.conf            # Nginx 설정 (Docker)
├── Dockerfile            # Docker 빌드
└── package.json
```

## Getting Started

### Prerequisites

- Node.js >= 18.0.0
- npm >= 9.0.0

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env
```

### Development

```bash
# Start development server
npm run dev

# Open http://localhost:3000
```

### Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Linting & Formatting

```bash
# Run ESLint
npm run lint

# Fix ESLint issues
npm run lint:fix

# Format code with Prettier
npm run format
```

### Testing

```bash
# Run tests
npm run test

# Run tests with coverage
npm run test:coverage
```

## Docker

```bash
# Build image
docker build -t knowledge-portal-frontend .

# Run container
docker run -p 80:80 knowledge-portal-frontend
```

## Features

### Dashboard
- 검색 통계 시각화
- 시스템 상태 모니터링
- 사용자 활동 로그

### Search
- **Chat Search**: SSE 스트리밍을 통한 실시간 AI 응답
- **Keyword Search**: 페이지네이션 및 필터링 지원

### Knowledge Management
- 문서 업로드/수정/삭제
- 처리 상태 모니터링
- 지식 그래프 시각화 (예정)

## API Proxy

개발 환경에서 `/api` 요청은 `http://localhost:8080`으로 프록시됩니다.
프로덕션 환경에서는 nginx가 프록시를 처리합니다.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API URL |
| `VITE_KEYCLOAK_URL` | Keycloak server URL |
| `VITE_KEYCLOAK_REALM` | Keycloak realm name |
| `VITE_KEYCLOAK_CLIENT_ID` | Keycloak client ID |
