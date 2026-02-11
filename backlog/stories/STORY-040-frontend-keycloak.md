# STORY-040: Frontend Keycloak 연동

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-29 |
| **Epic** | EPIC-003 |
| **Status** | Done |
| **Priority** | Critical |
| **Story Points** | 5 |
| **Assignee** | Frontend |
| **Sprint** | 3 |

---

## User Story

**As a** 사용자,
**I want** Keycloak SSO를 통해 로그인,
**So that** 안전하게 인증하고 시스템 기능에 접근할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 미인증 사용자, **When** 보호된 페이지 접근, **Then** Keycloak 로그인 페이지로 리다이렉트
- [ ] **Given** Keycloak 로그인 성공, **When** 콜백 처리, **Then** 토큰 저장 및 원래 페이지로 리다이렉트
- [ ] **Given** 로그아웃 버튼 클릭, **When** 로그아웃 실행, **Then** Keycloak 세션 종료 및 로그인 페이지 이동
- [ ] **Given** 토큰 만료 5분 전, **When** Silent Refresh, **Then** 토큰 자동 갱신
- [ ] **Given** 사용자 정보 필요, **When** useAuth 훅 호출, **Then** 사용자 이름, 역할 정보 반환

---

## Tasks

- [ ] keycloak-js 라이브러리 설치
- [ ] KeycloakProvider 컴포넌트 구현
- [ ] useAuth 커스텀 훅 구현
- [ ] ProtectedRoute 컴포넌트 구현
- [ ] Silent Refresh 설정
- [ ] 로그인/로그아웃 플로우 구현
- [ ] 에러 핸들링 (토큰 만료, 네트워크 오류)
- [ ] 단위/E2E 테스트 작성

---

## 기술 노트

### KeycloakProvider

```typescript
// frontend/src/features/auth/KeycloakProvider.tsx
import Keycloak from 'keycloak-js';
import { createContext, useEffect, useState, ReactNode } from 'react';

interface AuthContextType {
  keycloak: Keycloak | null;
  initialized: boolean;
  authenticated: boolean;
  user: UserInfo | null;
  login: () => void;
  logout: () => void;
  getToken: () => Promise<string>;
}

const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: 'hybrid-rag',
  clientId: 'frontend-app'
};

export const AuthContext = createContext<AuthContextType | null>(null);

export const KeycloakProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [keycloak, setKeycloak] = useState<Keycloak | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    const kc = new Keycloak(keycloakConfig);

    kc.init({
      onLoad: 'check-sso',
      silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
      checkLoginIframe: false
    }).then((authenticated) => {
      setKeycloak(kc);
      setInitialized(true);

      if (authenticated) {
        setUser({
          id: kc.subject!,
          username: kc.tokenParsed?.preferred_username,
          email: kc.tokenParsed?.email,
          roles: kc.tokenParsed?.realm_access?.roles || []
        });

        // Token Refresh 설정
        setInterval(() => {
          kc.updateToken(60).catch(() => {
            console.warn('Token refresh failed');
            kc.logout();
          });
        }, 60000);
      }
    }).catch((error) => {
      console.error('Keycloak init failed:', error);
      setInitialized(true);
    });
  }, []);

  const login = () => keycloak?.login();
  const logout = () => keycloak?.logout({ redirectUri: window.location.origin });

  const getToken = async (): Promise<string> => {
    if (!keycloak) throw new Error('Keycloak not initialized');
    await keycloak.updateToken(30);
    return keycloak.token!;
  };

  return (
    <AuthContext.Provider value={{
      keycloak,
      initialized,
      authenticated: !!keycloak?.authenticated,
      user,
      login,
      logout,
      getToken
    }}>
      {children}
    </AuthContext.Provider>
  );
};
```

### useAuth 훅

```typescript
// frontend/src/features/auth/useAuth.ts
import { useContext } from 'react';
import { AuthContext } from './KeycloakProvider';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within KeycloakProvider');
  }
  return context;
};

// 사용 예시
export const UserProfile: React.FC = () => {
  const { user, logout, authenticated } = useAuth();

  if (!authenticated) {
    return <LoginButton />;
  }

  return (
    <div>
      <span>{user?.username}</span>
      <button onClick={logout}>로그아웃</button>
    </div>
  );
};
```

### ProtectedRoute

```typescript
// frontend/src/features/auth/ProtectedRoute.tsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRoles = []
}) => {
  const { authenticated, initialized, user, login } = useAuth();
  const location = useLocation();

  if (!initialized) {
    return <LoadingSpinner />;
  }

  if (!authenticated) {
    // 로그인 페이지로 리다이렉트 (원래 경로 저장)
    login();
    return null;
  }

  if (requiredRoles.length > 0) {
    const hasRole = requiredRoles.some(role => user?.roles.includes(role));
    if (!hasRole) {
      return <Navigate to="/unauthorized" state={{ from: location }} replace />;
    }
  }

  return <>{children}</>;
};

// 라우터 설정
// App.tsx
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route path="/" element={
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  } />
  <Route path="/admin" element={
    <ProtectedRoute requiredRoles={['ADMIN']}>
      <AdminPage />
    </ProtectedRoute>
  } />
</Routes>
```

### Silent Check SSO

```html
<!-- public/silent-check-sso.html -->
<!DOCTYPE html>
<html>
<head>
  <script>
    parent.postMessage(location.href, location.origin);
  </script>
</head>
<body></body>
</html>
```

### 영향 범위
- `frontend/src/features/auth/KeycloakProvider.tsx`
- `frontend/src/features/auth/useAuth.ts`
- `frontend/src/features/auth/ProtectedRoute.tsx`
- `frontend/public/silent-check-sso.html`
- `frontend/src/App.tsx`

---

## 테스트 계획

- [ ] Unit Test: useAuth 훅
- [ ] Unit Test: ProtectedRoute 렌더링
- [ ] Integration Test: 로그인 플로우 (mock Keycloak)
- [ ] E2E Test: 실제 Keycloak 로그인/로그아웃

---

## 참고 자료

- [Keycloak JS Adapter](https://www.keycloak.org/docs/latest/securing_apps/#_javascript_adapter)
- [Frontend 상세 설계서](../../knowledge_service/docs/02_design/02_frontend_detailed_design.md)
