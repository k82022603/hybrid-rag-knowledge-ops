import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type { User } from '@/types';

/**
 * Auth State Interface
 */
interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  authMethod: 'direct' | 'keycloak' | null;
}

/**
 * Login Credentials Interface
 */
interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

/**
 * Login Response Interface
 */
interface LoginResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

// Storage keys
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'auth_access_token',
  REFRESH_TOKEN: 'auth_refresh_token',
  USER: 'auth_user',
  AUTH_METHOD: 'auth_method',
} as const;

/**
 * Load persisted auth state from localStorage
 */
const loadPersistedState = (): Partial<AuthState> => {
  try {
    const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
    const userStr = localStorage.getItem(STORAGE_KEYS.USER);
    const authMethod = localStorage.getItem(STORAGE_KEYS.AUTH_METHOD) as 'direct' | 'keycloak' | null;

    if (accessToken && userStr) {
      const user = JSON.parse(userStr) as User;
      return {
        accessToken,
        refreshToken,
        user,
        isAuthenticated: true,
        authMethod,
      };
    }
  } catch (error) {
    console.error('Failed to load persisted auth state:', error);
  }
  return {};
};

/**
 * Persist auth state to localStorage
 */
const persistAuthState = (state: Partial<AuthState>) => {
  try {
    if (state.accessToken) {
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, state.accessToken);
    } else {
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    }

    if (state.refreshToken) {
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, state.refreshToken);
    } else {
      localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    }

    if (state.user) {
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(state.user));
    } else {
      localStorage.removeItem(STORAGE_KEYS.USER);
    }

    if (state.authMethod) {
      localStorage.setItem(STORAGE_KEYS.AUTH_METHOD, state.authMethod);
    } else {
      localStorage.removeItem(STORAGE_KEYS.AUTH_METHOD);
    }
  } catch (error) {
    console.error('Failed to persist auth state:', error);
  }
};

/**
 * Clear persisted auth state
 */
const clearPersistedState = () => {
  try {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER);
    localStorage.removeItem(STORAGE_KEYS.AUTH_METHOD);
  } catch (error) {
    console.error('Failed to clear persisted auth state:', error);
  }
};

// Initial state with persisted data
const persistedState = loadPersistedState();
const initialState: AuthState = {
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  authMethod: null,
  ...persistedState,
};

/**
 * Async thunk for direct login (non-Keycloak)
 */
export const loginAsync = createAsyncThunk<
  LoginResponse,
  LoginCredentials,
  { rejectValue: string }
>(
  'auth/loginAsync',
  async (credentials, thunkAPI) => {
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: credentials.email,
          password: credentials.password,
        }),
      });

      if (!response.ok) {
        // Try to parse error message from response
        try {
          const errorData = await response.json();
          return thunkAPI.rejectWithValue(errorData.message || getErrorMessage(response.status));
        } catch {
          return thunkAPI.rejectWithValue(getErrorMessage(response.status));
        }
      }

      const data: LoginResponse = await response.json();
      return data;
    } catch (error) {
      if (error instanceof Error) {
        // Network error or other fetch error
        if (error.message === 'Failed to fetch') {
          return thunkAPI.rejectWithValue('서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.');
        }
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue('로그인 중 오류가 발생했습니다.');
    }
  }
);

/**
 * Async thunk for token refresh
 */
export const refreshTokenAsync = createAsyncThunk<
  { accessToken: string; expiresIn: number },
  void,
  { rejectValue: string; state: { auth: AuthState } }
>(
  'auth/refreshTokenAsync',
  async (_, thunkAPI) => {
    try {
      const state = thunkAPI.getState();
      const refreshToken = state.auth.refreshToken;

      if (!refreshToken) {
        return thunkAPI.rejectWithValue('No refresh token available');
      }

      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refreshToken }),
      });

      if (!response.ok) {
        return thunkAPI.rejectWithValue('Token refresh failed');
      }

      const data = await response.json();
      return data;
    } catch {
      return thunkAPI.rejectWithValue('Token refresh failed');
    }
  }
);

/**
 * Get error message based on HTTP status code
 */
const getErrorMessage = (status: number): string => {
  switch (status) {
    case 400:
      return '입력 정보를 확인해주세요.';
    case 401:
      return '이메일 또는 비밀번호가 올바르지 않습니다.';
    case 403:
      return '접근 권한이 없습니다.';
    case 404:
      return '계정을 찾을 수 없습니다.';
    case 423:
      return '계정이 잠겼습니다. 관리자에게 문의하세요.';
    case 429:
      return '로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.';
    case 500:
    case 502:
    case 503:
      return '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
    default:
      return '로그인에 실패했습니다.';
  }
};

/**
 * Auth Slice
 */
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    // Synchronous login start (for UI feedback)
    loginStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },

    // Synchronous login success (used by LoginForm directly or Keycloak)
    loginSuccess: (state, action: PayloadAction<User & { accessToken?: string; refreshToken?: string }>) => {
      const { accessToken, refreshToken, ...user } = action.payload;
      state.isLoading = false;
      state.isAuthenticated = true;
      state.user = user;
      state.accessToken = accessToken || state.accessToken;
      state.refreshToken = refreshToken || state.refreshToken;
      state.error = null;
      state.authMethod = 'direct';

      // Persist state
      persistAuthState({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        authMethod: state.authMethod,
      });
    },

    // Synchronous login failure
    loginFailure: (state, action: PayloadAction<string>) => {
      state.isLoading = false;
      state.isAuthenticated = false;
      state.user = null;
      state.accessToken = null;
      state.refreshToken = null;
      state.error = action.payload;
      state.authMethod = null;
      clearPersistedState();
    },

    // Set Keycloak authentication state
    setKeycloakAuth: (state, action: PayloadAction<{ user: User; token: string }>) => {
      state.user = action.payload.user;
      state.accessToken = action.payload.token;
      state.isAuthenticated = true;
      state.isLoading = false;
      state.error = null;
      state.authMethod = 'keycloak';

      // Persist state (Keycloak tokens are managed by Keycloak, but we store user info)
      persistAuthState({
        accessToken: action.payload.token,
        user: action.payload.user,
        authMethod: 'keycloak',
      });
    },

    // Logout
    logout: (state) => {
      state.isAuthenticated = false;
      state.user = null;
      state.accessToken = null;
      state.refreshToken = null;
      state.error = null;
      state.authMethod = null;
      clearPersistedState();
    },

    // Clear error
    clearError: (state) => {
      state.error = null;
    },

    // Update access token
    updateAccessToken: (state, action: PayloadAction<string>) => {
      state.accessToken = action.payload;
      persistAuthState({
        accessToken: action.payload,
        refreshToken: state.refreshToken,
        user: state.user,
        authMethod: state.authMethod,
      });
    },
  },
  extraReducers: (builder) => {
    // Login async
    builder
      .addCase(loginAsync.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginAsync.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.accessToken = action.payload.accessToken;
        state.refreshToken = action.payload.refreshToken;
        state.error = null;
        state.authMethod = 'direct';

        // Persist state
        persistAuthState({
          accessToken: action.payload.accessToken,
          refreshToken: action.payload.refreshToken,
          user: action.payload.user,
          authMethod: 'direct',
        });
      })
      .addCase(loginAsync.rejected, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = false;
        state.user = null;
        state.accessToken = null;
        state.refreshToken = null;
        state.error = action.payload || '로그인에 실패했습니다.';
        state.authMethod = null;
        clearPersistedState();
      });

    // Token refresh async
    builder
      .addCase(refreshTokenAsync.fulfilled, (state, action) => {
        state.accessToken = action.payload.accessToken;
        persistAuthState({
          accessToken: action.payload.accessToken,
          refreshToken: state.refreshToken,
          user: state.user,
          authMethod: state.authMethod,
        });
      })
      .addCase(refreshTokenAsync.rejected, (state) => {
        // Token refresh failed - logout
        state.isAuthenticated = false;
        state.user = null;
        state.accessToken = null;
        state.refreshToken = null;
        state.authMethod = null;
        clearPersistedState();
      });
  },
});

export const {
  loginStart,
  loginSuccess,
  loginFailure,
  setKeycloakAuth,
  logout,
  clearError,
  updateAccessToken,
} = authSlice.actions;

// Selectors
export const selectAuth = (state: { auth: AuthState }) => state.auth;
export const selectUser = (state: { auth: AuthState }) => state.auth.user;
export const selectIsAuthenticated = (state: { auth: AuthState }) => state.auth.isAuthenticated;
export const selectIsLoading = (state: { auth: AuthState }) => state.auth.isLoading;
export const selectAuthError = (state: { auth: AuthState }) => state.auth.error;
export const selectAccessToken = (state: { auth: AuthState }) => state.auth.accessToken;

export default authSlice.reducer;
