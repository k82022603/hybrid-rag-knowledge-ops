# Frontend 설계서 검토 보고서

> ⚠️ **Update Notice (2026-01-25)**: MUI → Tailwind CSS 마이그레이션 결정
> - 이 리뷰는 MUI v5 기준으로 작성됨
> - 신규 기술 스택: Tailwind CSS 3.4+ + Headless UI + Heroicons
> - 참조: [04.Tailwind_Antigravity_Stitch_도입_영향도_분석.md](../../../../../docs/technical_assessment/Guides/04.Tailwind_Antigravity_Stitch_도입_영향도_분석.md)

## 문서 정보

| 항목 | 내용 |
|------|------|
| **검토 대상** | frontend_detailed_design.md (v1.2 → v2.0), ui_design_system_guide.md (v1.1 → v2.0) |
| **검토일** | 2026-01-22 |
| **업데이트** | 2026-01-25 (Tailwind 마이그레이션 반영) |
| **검토자** | Frontend Agent (Claude Opus 4.5) |
| **상태** | Approved with Minor Recommendations |

---

## 1. 검토 요약

### 1.1 전체 평가

| 평가 항목 | 점수 | 평가 |
|----------|------|------|
| 구현 가능성 | 9/10 | 우수 - React 18로 충분히 구현 가능 |
| 문서 완성도 | 9/10 | 우수 - 매우 상세하고 체계적 |
| 기술적 일관성 | 9/10 | 우수 - 최신 베스트 프랙티스 반영 |
| 다른 문서와의 정합성 | 8/10 | 양호 - 일부 API 엔드포인트 확인 필요 |

### 1.2 핵심 발견 사항

**강점:**
- React 18 + TypeScript 5.4+ 최신 스택 적용
- Feature-based 아키텍처로 모듈화 우수
- Redux Toolkit + React Query 조합으로 상태 관리 명확
- WCAG 2.1 AA 접근성 준수 명시
- 상세한 컴포넌트 설계 및 코드 예시

**개선 필요:**
- Socket.IO 대신 SSE(Server-Sent Events) 고려 필요 (Backend 설계와 일치)
- 일부 API 엔드포인트 경로가 Backend 설계서와 불일치
- 에러 바운더리 Sentry 연동 구현 상세화 필요

---

## 2. 구현 가능성 분석

### 2.1 기술 스택 검토

| 기술 | 버전 | 구현 가능성 | 비고 |
|------|------|------------|------|
| React | 18.3+ | O | 최신 안정 버전 |
| TypeScript | 5.4+ | O | 최신 기능 지원 |
| Vite | 5.x | O | 빌드 성능 우수 |
| **Tailwind CSS** | **3.4+** | **O** | **MUI 대체 (2026-01-25 결정)** |
| **Headless UI** | **2.x** | **O** | **접근성 지원 컴포넌트** |
| **Heroicons** | **2.x** | **O** | **아이콘 라이브러리** |
| Redux Toolkit | 2.x | O | 표준 상태 관리 |
| React Query | 5.x | O | 서버 상태 관리 |
| React Router | 6.x | O | 최신 라우팅 API |
| Framer Motion | 11.x | O | 애니메이션 |
| React Hook Form | 7.x | O | 폼 관리 |
| Zod | 3.x | O | 스키마 검증 |
| Socket.IO | - | △ | SSE 대안 검토 필요 |

### 2.2 구현 복잡도 분석

| 기능 | 복잡도 | 예상 공수 | 비고 |
|------|--------|----------|------|
| 대시보드 | 중 | 3일 | 차트/통계 위젯 |
| 지식 CRUD | 중 | 5일 | 마크다운 에디터 포함 |
| 채팅 검색 (RAG) | 상 | 5일 | 스트리밍 응답 처리 |
| 키워드 검색 | 중 | 3일 | 필터/페이지네이션 |
| 인증/권한 | 중 | 3일 | Keycloak 연동 |
| 문서 내보내기 | 중 | 3일 | Excel/PDF 생성 |
| 관리자 기능 | 중 | 4일 | 사용자/시스템 관리 |

**총 예상 공수: 26일 (1인 기준)**

---

## 3. 누락된 내용 분석

### 3.1 필수 보완 사항

#### 3.1.1 SSE vs WebSocket 결정

**현재 상태:** 설계서에서 Socket.IO/WebSocket 사용
**Backend 설계:** SSE(Server-Sent Events) 사용 명시

```
권장사항:
- Backend와 일치하도록 SSE 채택 권장
- 단방향 스트리밍(AI 응답)에 SSE가 더 적합
- WebSocket은 양방향 통신 필요 시에만 사용
```

#### 3.1.2 Keycloak 연동 상세화

**현재 상태:** 기본 인증 플로우만 정의
**누락 내용:**
- PKCE 플로우 상세 구현 코드
- Silent Refresh 전략
- 토큰 저장 방식 (localStorage vs sessionStorage)
- SSO 로그아웃 처리

```typescript
// 권장 보완 코드
// services/auth/keycloak.ts
import Keycloak from 'keycloak-js';

const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
};

export const keycloak = new Keycloak(keycloakConfig);

export const initKeycloak = async () => {
  return keycloak.init({
    onLoad: 'check-sso',
    pkceMethod: 'S256',
    checkLoginIframe: false,
    silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
  });
};
```

#### 3.1.3 에러 트래킹 연동

**현재 상태:** Sentry 언급만 있음
**누락 내용:**
- Sentry 초기화 설정
- 에러 컨텍스트 수집
- 사용자 정보 연동
- 성능 모니터링 설정

### 3.2 선택적 보완 사항

| 항목 | 우선순위 | 설명 |
|------|---------|------|
| 오프라인 지원 | 낮음 | PWA 캐싱 전략 상세화 |
| 푸시 알림 | 중간 | FCM 연동 방안 |
| 파일 업로드 진행률 | 중간 | Axios 업로드 프로그레스 |
| 이미지 미리보기 | 중간 | File API 활용 |
| 인쇄 스타일 | 낮음 | @media print 정의 |

---

## 4. 불일치/모순 분석

### 4.1 API 엔드포인트 불일치

| Frontend 설계서 | Backend/API 설계서 | 권장 수정 |
|----------------|-------------------|----------|
| `/api/v1/search` | `/api/v1/search/keyword` | Backend에 맞춤 |
| `/api/v1/knowledge` | `/api/v1/knowledges` | Backend에 맞춤 |
| `/api/v1/user/me` | `/api/v1/users/me` | Backend에 맞춤 |

### 4.2 인증 토큰 처리 불일치

**Frontend 설계서:**
- Redux에 accessToken 저장
- Axios 인터셉터에서 Bearer 토큰 추가

**인증 설계서:**
- HttpOnly 쿠키 기반 권장
- CSRF 토큰 처리 필요

```
권장사항:
- 보안을 위해 HttpOnly 쿠키 방식 채택
- accessToken은 메모리에만 저장
- refreshToken은 HttpOnly 쿠키로 관리
```

### 4.3 실시간 통신 프로토콜

**Frontend 설계서:** Socket.IO
**Backend 설계서:** SSE (Server-Sent Events)

```
권장사항:
SSE 채택 권장
- AI 스트리밍 응답은 단방향이므로 SSE 적합
- 구현 복잡도 낮음
- 자동 재연결 지원
```

---

## 5. 개선 제안

### 5.1 아키텍처 개선

#### 5.1.1 SSE 클라이언트 구현 제안

```typescript
// services/sse/chatService.ts
export const createChatStream = (query: string) => {
  const eventSource = new EventSource(
    `/api/v1/search/chat/stream?query=${encodeURIComponent(query)}`,
    { withCredentials: true }
  );

  return {
    eventSource,
    subscribe: (callbacks: {
      onMessage: (chunk: string) => void;
      onComplete: () => void;
      onError: (error: Event) => void;
    }) => {
      eventSource.onmessage = (event) => {
        if (event.data === '[DONE]') {
          callbacks.onComplete();
          eventSource.close();
        } else {
          callbacks.onMessage(event.data);
        }
      };
      eventSource.onerror = callbacks.onError;
    },
  };
};
```

#### 5.1.2 에러 바운더리 강화

```typescript
// components/feedback/ErrorBoundary/ErrorBoundary.tsx
import * as Sentry from '@sentry/react';

export const ErrorBoundary = Sentry.withErrorBoundary(
  ({ children }: { children: React.ReactNode }) => <>{children}</>,
  {
    fallback: ({ error, resetError }) => (
      <ErrorFallback error={error} onReset={resetError} />
    ),
    beforeCapture: (scope) => {
      scope.setTag('component', 'ErrorBoundary');
    },
  }
);
```

### 5.2 성능 개선

#### 5.2.1 React Query 캐시 전략 세분화

```typescript
// services/queryClient.ts
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5분
      gcTime: 30 * 60 * 1000,    // 30분
      retry: (failureCount, error) => {
        // 4xx 에러는 재시도 안함
        if ((error as any)?.response?.status >= 400 &&
            (error as any)?.response?.status < 500) {
          return false;
        }
        return failureCount < 3;
      },
    },
  },
});

// 쿼리별 캐시 전략
export const QUERY_STALE_TIMES = {
  knowledge: 5 * 60 * 1000,    // 5분 - 자주 변경
  categories: 60 * 60 * 1000,  // 1시간 - 거의 안변함
  user: 10 * 60 * 1000,        // 10분 - 세션 유지
  dashboard: 2 * 60 * 1000,    // 2분 - 실시간성 필요
};
```

#### 5.2.2 Virtual List 적용 범위

```
권장 적용 대상:
- 지식 목록 (100개 이상)
- 검색 결과 (스크롤 페이지네이션)
- 채팅 메시지 기록 (긴 대화)
- 관리자 사용자 목록
```

### 5.3 접근성 강화

#### 5.3.1 Skip Link 구현

```typescript
// components/common/SkipLink/SkipLink.tsx
export const SkipLink: React.FC = () => (
  <a
    href="#main-content"
    className="skip-link"
    sx={{
      position: 'absolute',
      top: '-40px',
      left: 0,
      background: 'primary.main',
      color: 'primary.contrastText',
      padding: '8px',
      zIndex: 9999,
      '&:focus': {
        top: 0,
      },
    }}
  >
    본문으로 바로가기
  </a>
);
```

#### 5.3.2 Reduced Motion 지원

```typescript
// hooks/useReducedMotion.ts
export const useReducedMotion = () => {
  const [reducedMotion, setReducedMotion] = useState(
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return reducedMotion;
};
```

---

## 6. UI 디자인 시스템 가이드 검토

### 6.1 강점

- 명확한 디자인 원칙 정의 (명확성, 효율성, 일관성, 접근성, 신뢰성)
- 60-30-10 색상 비율 가이드라인
- 상세한 컴포넌트 상태 정의 (Default, Hover, Focus, Pressed, Disabled)
- WCAG 색상 대비비 준수
- 한글 타이포그래피 최적화 (word-break: keep-all)
- 다크 모드 지원 상세화

### 6.2 보완 필요 사항

| 항목 | 현재 상태 | 권장 보완 |
|------|----------|----------|
| 로딩 스켈레톤 | 기본 언급 | 컴포넌트별 스켈레톤 패턴 상세화 |
| 에러 상태 UI | 일부 정의 | 에러 유형별 UI 패턴 추가 |
| 빈 상태 일러스트 | 텍스트만 | SVG 일러스트 디자인 가이드 |
| 애니메이션 타이밍 | 정의됨 | Framer Motion variants 코드 예시 |

---

## 7. 결론 및 권장사항

### 7.1 즉시 수정 필요 (P0)

1. **SSE 채택**: Socket.IO 대신 SSE로 변경하여 Backend와 일치
2. **API 엔드포인트 수정**: Backend 설계서에 맞게 경로 수정
3. **인증 토큰 저장**: HttpOnly 쿠키 방식으로 변경

### 7.2 구현 단계에서 보완 (P1)

1. Keycloak PKCE 연동 코드 상세화
2. Sentry 에러 트래킹 초기화 코드 추가
3. React Query 캐시 전략 세분화

### 7.3 향후 개선 (P2)

1. 오프라인 지원 강화
2. 푸시 알림 연동
3. 성능 모니터링 대시보드 연동

### 7.4 최종 승인

**설계서 상태: Approved**

두 설계서 모두 React 18 기반 구현에 충분한 상세 수준을 갖추고 있으며,
위 권장사항을 반영하면 안정적인 프론트엔드 애플리케이션 개발이 가능합니다.

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-22 | Frontend Agent | 초기 검토 |
