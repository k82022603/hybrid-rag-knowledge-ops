/**
 * LoginForm - 사용자 로그인 폼 컴포넌트
 *
 * Features:
 * - 이메일/비밀번호 입력
 * - 비밀번호 표시/숨김 토글
 * - Remember me 옵션
 * - 폼 유효성 검사
 * - 접근성 지원 (WCAG 2.1 AA)
 * - 키보드 네비게이션
 */
import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginAsync, clearError, selectIsLoading, selectAuthError } from '@/store/slices/authSlice';
import { useAppDispatch, useAppSelector } from '@/store';

interface LoginFormProps {
  onForgotPassword?: () => void;
  onSSOLogin?: () => void;
  redirectPath?: string;
}

const LoginForm: React.FC<LoginFormProps> = ({
  onForgotPassword,
  onSSOLogin,
  redirectPath = '/dashboard',
}) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const isLoading = useAppSelector(selectIsLoading);
  const error = useAppSelector(selectAuthError);

  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // Validation state
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [touched, setTouched] = useState({ email: false, password: false });

  // Email validation
  const validateEmail = useCallback((value: string): string => {
    if (!value) return '이메일을 입력해주세요.';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) return '유효한 이메일 형식이 아닙니다.';
    return '';
  }, []);

  // Password validation
  const validatePassword = useCallback((value: string): string => {
    if (!value) return '비밀번호를 입력해주세요.';
    if (value.length < 8) return '비밀번호는 8자 이상이어야 합니다.';
    return '';
  }, []);

  // Handle email change
  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setEmail(value);
    if (touched.email) {
      setEmailError(validateEmail(value));
    }
    if (error) dispatch(clearError());
  };

  // Handle password change
  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setPassword(value);
    if (touched.password) {
      setPasswordError(validatePassword(value));
    }
    if (error) dispatch(clearError());
  };

  // Handle blur events
  const handleEmailBlur = () => {
    setTouched((prev) => ({ ...prev, email: true }));
    setEmailError(validateEmail(email));
  };

  const handlePasswordBlur = () => {
    setTouched((prev) => ({ ...prev, password: true }));
    setPasswordError(validatePassword(password));
  };

  // Form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate all fields
    const emailErr = validateEmail(email);
    const passwordErr = validatePassword(password);
    setEmailError(emailErr);
    setPasswordError(passwordErr);
    setTouched({ email: true, password: true });

    if (emailErr || passwordErr) return;

    try {
      // Use async thunk for login
      const result = await dispatch(
        loginAsync({ email, password, rememberMe })
      ).unwrap();

      // Remember me 처리
      if (rememberMe) {
        localStorage.setItem('rememberEmail', email);
      } else {
        localStorage.removeItem('rememberEmail');
      }

      // Login successful - navigate to dashboard
      if (result) {
        navigate(redirectPath, { replace: true });
      }
    } catch {
      // Error is already handled by Redux slice
      // Just let the UI show the error from state
    }
  };

  // Load remembered email on mount
  React.useEffect(() => {
    const rememberedEmail = localStorage.getItem('rememberEmail');
    if (rememberedEmail) {
      setEmail(rememberedEmail);
      setRememberMe(true);
    }
  }, []);

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      {/* Global error message */}
      {error && (
        <div
          role="alert"
          className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
        >
          <div className="flex items-center gap-3">
            <svg
              className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          </div>
        </div>
      )}

      {/* Email field */}
      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          이메일
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg
              className="h-5 w-5 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207"
              />
            </svg>
          </div>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={handleEmailChange}
            onBlur={handleEmailBlur}
            aria-invalid={!!emailError}
            aria-describedby={emailError ? 'email-error' : undefined}
            className={`
              block w-full pl-10 pr-3 py-2.5
              border rounded-lg
              text-gray-900 dark:text-white
              placeholder-gray-400 dark:placeholder-gray-500
              bg-white dark:bg-gray-800
              transition-colors duration-200
              focus:outline-none focus:ring-2 focus:ring-offset-0
              ${
                emailError
                  ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                  : 'border-gray-300 dark:border-gray-600 focus:border-primary-500 focus:ring-primary-500/20'
              }
            `}
            placeholder="name@company.com"
          />
        </div>
        {emailError && (
          <p id="email-error" className="mt-1.5 text-sm text-red-600 dark:text-red-400" role="alert">
            {emailError}
          </p>
        )}
      </div>

      {/* Password field */}
      <div>
        <label
          htmlFor="password"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          비밀번호
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg
              className="h-5 w-5 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <input
            id="password"
            name="password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            required
            value={password}
            onChange={handlePasswordChange}
            onBlur={handlePasswordBlur}
            aria-invalid={!!passwordError}
            aria-describedby={passwordError ? 'password-error' : undefined}
            className={`
              block w-full pl-10 pr-10 py-2.5
              border rounded-lg
              text-gray-900 dark:text-white
              placeholder-gray-400 dark:placeholder-gray-500
              bg-white dark:bg-gray-800
              transition-colors duration-200
              focus:outline-none focus:ring-2 focus:ring-offset-0
              ${
                passwordError
                  ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                  : 'border-gray-300 dark:border-gray-600 focus:border-primary-500 focus:ring-primary-500/20'
              }
            `}
            placeholder="••••••••"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 표시'}
          >
            {showPassword ? (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            )}
          </button>
        </div>
        {passwordError && (
          <p id="password-error" className="mt-1.5 text-sm text-red-600 dark:text-red-400" role="alert">
            {passwordError}
          </p>
        )}
      </div>

      {/* Remember me & Forgot password */}
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            className="
              w-4 h-4 rounded border-gray-300 dark:border-gray-600
              text-primary-600
              focus:ring-2 focus:ring-primary-500/20 focus:ring-offset-0
              bg-white dark:bg-gray-800
              cursor-pointer
            "
          />
          <span className="text-sm text-gray-600 dark:text-gray-400">로그인 유지</span>
        </label>
        {onForgotPassword && (
          <button
            type="button"
            onClick={onForgotPassword}
            className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium transition-colors"
          >
            비밀번호 찾기
          </button>
        )}
      </div>

      {/* Submit button */}
      <button
        type="submit"
        disabled={isLoading}
        className="
          w-full py-2.5 px-4
          bg-primary-600 hover:bg-primary-700
          disabled:bg-primary-400 disabled:cursor-not-allowed
          text-white font-medium
          rounded-lg
          transition-colors duration-200
          focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800
          flex items-center justify-center gap-2
        "
      >
        {isLoading ? (
          <>
            <svg
              className="animate-spin h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>로그인 중...</span>
          </>
        ) : (
          <span>로그인</span>
        )}
      </button>

      {/* SSO Login option */}
      {onSSOLogin && (
        <>
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200 dark:border-gray-700" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                또는
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={onSSOLogin}
            className="
              w-full py-2.5 px-4
              bg-white dark:bg-gray-700
              border border-gray-300 dark:border-gray-600
              hover:bg-gray-50 dark:hover:bg-gray-600
              text-gray-700 dark:text-gray-200 font-medium
              rounded-lg
              transition-colors duration-200
              focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:ring-offset-2 dark:focus:ring-offset-gray-800
              flex items-center justify-center gap-2
            "
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            <span>회사 SSO로 로그인</span>
          </button>
        </>
      )}
    </form>
  );
};

export default LoginForm;
