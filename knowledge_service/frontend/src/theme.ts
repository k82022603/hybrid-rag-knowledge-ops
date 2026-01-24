/**
 * Theme utilities for Tailwind CSS
 *
 * 다크 모드 및 테마 관련 유틸리티
 */

// 다크 모드 설정
export type ThemeMode = 'light' | 'dark' | 'system';

/**
 * 현재 테마 모드 가져오기
 */
export const getThemeMode = (): ThemeMode => {
  const stored = localStorage.getItem('theme') as ThemeMode | null;
  if (stored && ['light', 'dark', 'system'].includes(stored)) {
    return stored;
  }
  return 'system';
};

/**
 * 테마 모드 설정
 */
export const setThemeMode = (mode: ThemeMode): void => {
  localStorage.setItem('theme', mode);
  applyTheme(mode);
};

/**
 * 테마 적용
 */
export const applyTheme = (mode: ThemeMode): void => {
  const root = document.documentElement;

  if (mode === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  } else if (mode === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
};

/**
 * 시스템 테마 변경 감지 리스너 등록
 */
export const initThemeListener = (): (() => void) => {
  const mode = getThemeMode();
  applyTheme(mode);

  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const handleChange = () => {
    if (getThemeMode() === 'system') {
      applyTheme('system');
    }
  };

  mediaQuery.addEventListener('change', handleChange);
  return () => mediaQuery.removeEventListener('change', handleChange);
};

/**
 * 테마 토글
 */
export const toggleTheme = (): void => {
  const current = getThemeMode();
  const next: ThemeMode = current === 'light' ? 'dark' : current === 'dark' ? 'system' : 'light';
  setThemeMode(next);
};

/**
 * 현재 다크 모드 여부
 */
export const isDarkMode = (): boolean => {
  return document.documentElement.classList.contains('dark');
};

// 색상 팔레트 (Tailwind config와 동기화)
export const colors = {
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
  },
  secondary: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
  },
  success: {
    500: '#22c55e',
    600: '#16a34a',
  },
  warning: {
    500: '#f59e0b',
    600: '#d97706',
  },
  error: {
    500: '#ef4444',
    600: '#dc2626',
  },
} as const;
