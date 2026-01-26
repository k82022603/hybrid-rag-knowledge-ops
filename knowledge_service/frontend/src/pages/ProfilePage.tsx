/**
 * ProfilePage - 사용자 프로필 페이지
 *
 * 사용자 정보 표시/수정, 비밀번호 변경,
 * 활동 이력, 알림 설정
 */
import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  UserIcon,
  KeyIcon,
  BellIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  PencilIcon,
  MagnifyingGlassIcon,
  ArrowUpTrayIcon,
  DocumentTextIcon,
  ArrowRightStartOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/auth';
import {
  profileService,
  type UpdateProfileRequest,
  type ChangePasswordRequest,
  type ActivityLog,
  type NotificationSettings,
} from '@/services/profileService';

/**
 * Tab configuration
 */
type ProfileTab = 'profile' | 'password' | 'activity' | 'notifications';

const TABS: { key: ProfileTab; label: string; icon: React.ReactNode }[] = [
  { key: 'profile', label: 'Profile', icon: <UserIcon className="h-5 w-5" /> },
  { key: 'password', label: 'Password', icon: <KeyIcon className="h-5 w-5" /> },
  { key: 'activity', label: 'Activity', icon: <ClockIcon className="h-5 w-5" /> },
  { key: 'notifications', label: 'Notifications', icon: <BellIcon className="h-5 w-5" /> },
];

/**
 * Activity type icon mapping
 */
const ACTIVITY_ICONS: Record<string, React.ReactNode> = {
  search: <MagnifyingGlassIcon className="h-4 w-4" />,
  upload: <ArrowUpTrayIcon className="h-4 w-4" />,
  download: <DocumentTextIcon className="h-4 w-4" />,
  edit: <PencilIcon className="h-4 w-4" />,
  login: <ArrowRightStartOnRectangleIcon className="h-4 w-4" />,
};

/**
 * Success Toast component
 */
const SuccessToast: React.FC<{ message: string; onDismiss: () => void }> = ({ message, onDismiss }) => (
  <div className="fixed bottom-4 right-4 z-50 animate-slide-up">
    <div className="flex items-center gap-3 px-4 py-3 bg-success-50 dark:bg-success-900/30 border border-success-200 dark:border-success-800 rounded-lg shadow-lg">
      <CheckCircleIcon className="h-5 w-5 text-success-600 dark:text-success-400 flex-shrink-0" />
      <span className="text-sm font-medium text-success-800 dark:text-success-200">{message}</span>
      <button onClick={onDismiss} className="ml-2 text-success-400 hover:text-success-600" aria-label="Dismiss">
        &times;
      </button>
    </div>
  </div>
);

/**
 * ProfileForm - 프로필 수정 폼
 */
const ProfileForm: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<UpdateProfileRequest>({
    name: user?.name || '',
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    department: user?.department || '',
  });
  const [successMsg, setSuccessMsg] = useState('');

  const updateMutation = useMutation({
    mutationFn: (data: UpdateProfileRequest) => profileService.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      setSuccessMsg('Profile updated successfully.');
      setTimeout(() => setSuccessMsg(''), 3000);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6" data-testid="profile-form">
      {/* User avatar section */}
      <div className="flex items-center gap-4 pb-6 border-b border-gray-200 dark:border-gray-700">
        <div className="w-16 h-16 rounded-full bg-primary-600 flex items-center justify-center text-white text-xl font-bold">
          {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {user?.name || user?.username}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">{user?.email}</p>
          {user?.roles && user.roles.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {user.roles.filter((r) => !r.startsWith('default-')).map((role) => (
                <span
                  key={role}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
                >
                  {role}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Form fields */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="firstName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            First Name
          </label>
          <input
            id="firstName"
            type="text"
            value={formData.firstName || ''}
            onChange={(e) => setFormData((prev) => ({ ...prev, firstName: e.target.value }))}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
        <div>
          <label htmlFor="lastName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Last Name
          </label>
          <input
            id="lastName"
            type="text"
            value={formData.lastName || ''}
            onChange={(e) => setFormData((prev) => ({ ...prev, lastName: e.target.value }))}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      <div>
        <label htmlFor="displayName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Display Name
        </label>
        <input
          id="displayName"
          type="text"
          value={formData.name || ''}
          onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
          className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      <div>
        <label htmlFor="department" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Department
        </label>
        <input
          id="department"
          type="text"
          value={formData.department || ''}
          onChange={(e) => setFormData((prev) => ({ ...prev, department: e.target.value }))}
          className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Email
        </label>
        <input
          type="email"
          value={user?.email || ''}
          disabled
          className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400 cursor-not-allowed"
        />
        <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">Email cannot be changed.</p>
      </div>

      {/* Error */}
      {updateMutation.isError && (
        <div className="flex items-center gap-2 p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg" role="alert">
          <ExclamationTriangleIcon className="h-5 w-5 text-error-500 flex-shrink-0" />
          <span className="text-sm text-error-700 dark:text-error-300">
            {updateMutation.error instanceof Error ? updateMutation.error.message : 'Failed to update profile.'}
          </span>
        </div>
      )}

      {/* Submit */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {updateMutation.isPending ? (
            <ArrowPathIcon className="h-4 w-4 animate-spin" />
          ) : (
            <PencilIcon className="h-4 w-4" />
          )}
          Save Changes
        </button>
      </div>

      {successMsg && <SuccessToast message={successMsg} onDismiss={() => setSuccessMsg('')} />}
    </form>
  );
};

/**
 * PasswordForm - 비밀번호 변경 폼
 */
const PasswordForm: React.FC = () => {
  const [formData, setFormData] = useState<ChangePasswordRequest>({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [successMsg, setSuccessMsg] = useState('');

  const changeMutation = useMutation({
    mutationFn: (data: ChangePasswordRequest) => profileService.changePassword(data),
    onSuccess: () => {
      setFormData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setSuccessMsg('Password changed successfully.');
      setTimeout(() => setSuccessMsg(''), 3000);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.newPassword !== formData.confirmPassword) {
      return;
    }
    if (formData.newPassword.length < 8) {
      return;
    }
    changeMutation.mutate(formData);
  };

  const passwordsMatch = formData.newPassword === formData.confirmPassword || formData.confirmPassword === '';
  const passwordLongEnough = formData.newPassword.length >= 8 || formData.newPassword === '';

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-md" data-testid="password-form">
      <div>
        <label htmlFor="currentPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Current Password
        </label>
        <input
          id="currentPassword"
          type="password"
          value={formData.currentPassword}
          onChange={(e) => setFormData((prev) => ({ ...prev, currentPassword: e.target.value }))}
          required
          className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          autoComplete="current-password"
        />
      </div>

      <div>
        <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          New Password
        </label>
        <input
          id="newPassword"
          type="password"
          value={formData.newPassword}
          onChange={(e) => setFormData((prev) => ({ ...prev, newPassword: e.target.value }))}
          required
          minLength={8}
          className={`w-full px-3 py-2 text-sm rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
            !passwordLongEnough ? 'border-error-300 dark:border-error-600' : 'border-gray-300 dark:border-gray-600'
          }`}
          autoComplete="new-password"
          aria-invalid={!passwordLongEnough}
          aria-describedby="password-hint"
        />
        <p id="password-hint" className={`mt-1 text-xs ${!passwordLongEnough ? 'text-error-500' : 'text-gray-400'}`}>
          Password must be at least 8 characters.
        </p>
      </div>

      <div>
        <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Confirm New Password
        </label>
        <input
          id="confirmPassword"
          type="password"
          value={formData.confirmPassword}
          onChange={(e) => setFormData((prev) => ({ ...prev, confirmPassword: e.target.value }))}
          required
          className={`w-full px-3 py-2 text-sm rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
            !passwordsMatch ? 'border-error-300 dark:border-error-600' : 'border-gray-300 dark:border-gray-600'
          }`}
          autoComplete="new-password"
          aria-invalid={!passwordsMatch}
          aria-describedby="confirm-hint"
        />
        {!passwordsMatch && (
          <p id="confirm-hint" className="mt-1 text-xs text-error-500" role="alert">
            Passwords do not match.
          </p>
        )}
      </div>

      {/* Error */}
      {changeMutation.isError && (
        <div className="flex items-center gap-2 p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg" role="alert">
          <ExclamationTriangleIcon className="h-5 w-5 text-error-500 flex-shrink-0" />
          <span className="text-sm text-error-700 dark:text-error-300">
            {changeMutation.error instanceof Error ? changeMutation.error.message : 'Failed to change password.'}
          </span>
        </div>
      )}

      <button
        type="submit"
        disabled={changeMutation.isPending || !passwordsMatch || !passwordLongEnough}
        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
      >
        {changeMutation.isPending ? (
          <ArrowPathIcon className="h-4 w-4 animate-spin" />
        ) : (
          <KeyIcon className="h-4 w-4" />
        )}
        Change Password
      </button>

      {successMsg && <SuccessToast message={successMsg} onDismiss={() => setSuccessMsg('')} />}
    </form>
  );
};

/**
 * ActivityHistory - 활동 이력 탭
 */
const ActivityHistory: React.FC = () => {
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['profile', 'activities', page],
    queryFn: () => profileService.getActivityHistory(page, 20),
  });

  const activities = data?.activities ?? [];
  const totalPages = Math.ceil((data?.totalCount ?? 0) / 20);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <ArrowPathIcon className="h-6 w-6 text-primary-500 animate-spin" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="h-8 w-8 text-error-500 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">Failed to load activity history.</p>
      </div>
    );
  }

  if (activities.length === 0) {
    return (
      <div className="text-center py-12">
        <ClockIcon className="h-10 w-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
        <p className="text-sm text-gray-500 dark:text-gray-400">No activity history yet.</p>
      </div>
    );
  }

  return (
    <div data-testid="activity-history">
      <ul className="divide-y divide-gray-100 dark:divide-gray-700">
        {activities.map((activity: ActivityLog) => (
          <li key={activity.id} className="flex items-start gap-3 py-3">
            <div className="mt-0.5 p-1.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
              {ACTIVITY_ICONS[activity.type] || <ClockIcon className="h-4 w-4" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900 dark:text-white">{activity.description}</p>
              {activity.resourceName && (
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{activity.resourceName}</p>
              )}
            </div>
            <span className="text-xs text-gray-400 whitespace-nowrap">
              {new Date(activity.timestamp).toLocaleString('ko-KR', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </li>
        ))}
      </ul>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-50 transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-50 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

/**
 * NotificationSettingsPanel - 알림 설정 탭
 */
const NotificationSettingsPanel: React.FC = () => {
  const queryClient = useQueryClient();
  const [successMsg, setSuccessMsg] = useState('');

  const { data: settings, isLoading } = useQuery({
    queryKey: ['profile', 'notifications'],
    queryFn: () => profileService.getNotificationSettings(),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<NotificationSettings>) => profileService.updateNotificationSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile', 'notifications'] });
      setSuccessMsg('Notification settings saved.');
      setTimeout(() => setSuccessMsg(''), 3000);
    },
  });

  const handleToggle = useCallback(
    (key: keyof NotificationSettings) => {
      if (!settings) return;
      updateMutation.mutate({ [key]: !settings[key] });
    },
    [settings, updateMutation]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <ArrowPathIcon className="h-6 w-6 text-primary-500 animate-spin" />
      </div>
    );
  }

  const NOTIFICATION_OPTIONS: { key: keyof NotificationSettings; label: string; description: string }[] = [
    { key: 'emailNotifications', label: 'Email Notifications', description: 'Receive email notifications for important updates.' },
    { key: 'searchAlerts', label: 'Search Alerts', description: 'Get notified when new documents match your saved searches.' },
    { key: 'documentUpdates', label: 'Document Updates', description: 'Receive notifications when bookmarked documents are updated.' },
    { key: 'systemNotifications', label: 'System Notifications', description: 'Get notified about system maintenance and updates.' },
    { key: 'weeklyDigest', label: 'Weekly Digest', description: 'Receive a weekly summary of activity and new documents.' },
  ];

  return (
    <div className="space-y-1" data-testid="notification-settings">
      {NOTIFICATION_OPTIONS.map((option) => (
        <div
          key={option.key}
          className="flex items-center justify-between py-4 border-b border-gray-100 dark:border-gray-700 last:border-0"
        >
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{option.label}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{option.description}</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={settings?.[option.key] ?? false}
            onClick={() => handleToggle(option.key)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
              settings?.[option.key] ? 'bg-primary-600' : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                settings?.[option.key] ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      ))}

      {successMsg && <SuccessToast message={successMsg} onDismiss={() => setSuccessMsg('')} />}
    </div>
  );
};

/**
 * ProfilePage 메인 컴포넌트
 */
const ProfilePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ProfileTab>('profile');

  return (
    <div className="space-y-6" data-testid="profile-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Profile</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Tab Navigation */}
        <div className="lg:w-56 flex-shrink-0">
          <nav className="space-y-1" aria-label="Profile navigation">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                  }`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <span className={isActive ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 dark:text-gray-500'}>
                    {tab.icon}
                  </span>
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="flex-1 min-w-0">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            {activeTab === 'profile' && <ProfileForm />}
            {activeTab === 'password' && <PasswordForm />}
            {activeTab === 'activity' && <ActivityHistory />}
            {activeTab === 'notifications' && <NotificationSettingsPanel />}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
