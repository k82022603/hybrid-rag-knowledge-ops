import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import App from './App';
import { store } from './store';
import { KeycloakProvider } from './auth';
import './index.css';

// React Query 클라이언트 설정
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// 로딩 컴포넌트
const LoadingScreen: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
    <div className="text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 mb-4">
        <div className="spinner-lg text-primary-600" />
      </div>
      <h2 className="text-lg font-medium text-gray-700 dark:text-gray-300">
        Loading...
      </h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
        Initializing application
      </p>
    </div>
  </div>
);

// 인증 성공 콜백
const handleAuthSuccess = (user: { id: string; username: string; email: string }) => {
  console.log('Authentication successful:', user.username);
};

// 인증 에러 콜백
const handleAuthError = (error: Error) => {
  console.error('Authentication error:', error.message);
};

// 로그아웃 콜백
const handleAuthLogout = () => {
  console.log('User logged out');
  // 필요한 경우 상태 초기화
  queryClient.clear();
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <KeycloakProvider
          loadingComponent={<LoadingScreen />}
          onAuthSuccess={handleAuthSuccess}
          onAuthError={handleAuthError}
          onAuthLogout={handleAuthLogout}
        >
          <App />
        </KeycloakProvider>
      </QueryClientProvider>
    </Provider>
  </React.StrictMode>
);
