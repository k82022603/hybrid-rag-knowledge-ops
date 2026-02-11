/**
 * AdminPage - 관리자 페이지
 *
 * 사용자 관리, 시스템 설정, 감사 로그, 시스템 통계
 * ADMIN 역할만 접근 가능
 */
import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  UsersIcon,
  Cog6ToothIcon,
  ClipboardDocumentListIcon,
  ChartBarIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  DocumentTextIcon,
  UserGroupIcon,
  ClockIcon,
  ShieldCheckIcon,
  NoSymbolIcon,
  ServerStackIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import {
  adminService,
  type AdminUser,
  type SystemSettings,
  type AuditLog,
} from '@/services/adminService';

/**
 * Admin Tab type
 */
type AdminTab = 'users' | 'settings' | 'audit-logs' | 'stats' | 'cache';

const ADMIN_TABS: { key: AdminTab; label: string; icon: React.ReactNode }[] = [
  { key: 'stats', label: 'System Stats', icon: <ChartBarIcon className="h-5 w-5" /> },
  { key: 'users', label: 'User Management', icon: <UsersIcon className="h-5 w-5" /> },
  { key: 'cache', label: 'Cache', icon: <ServerStackIcon className="h-5 w-5" /> },
  { key: 'settings', label: 'System Settings', icon: <Cog6ToothIcon className="h-5 w-5" /> },
  { key: 'audit-logs', label: 'Audit Logs', icon: <ClipboardDocumentListIcon className="h-5 w-5" /> },
];

/**
 * StatCard 컴포넌트
 */
const StatCard: React.FC<{
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
}> = ({ title, value, icon, color, subtitle }) => (
  <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
    <div className="flex items-center gap-3 mb-3">
      <div className={`p-2 rounded-lg ${color}`}>
        {icon}
      </div>
      <span className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</span>
    </div>
    <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
    {subtitle && <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{subtitle}</p>}
  </div>
);

/**
 * SystemStatsPanel - 시스템 통계 탭
 */
const SystemStatsPanel: React.FC = () => {
  const { data: stats, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: () => adminService.getSystemStats(),
    refetchInterval: 60000, // Refresh every minute
  });

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
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Failed to load system statistics.</p>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700"
        >
          <ArrowPathIcon className="h-4 w-4" />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="system-stats">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          title="Total Documents"
          value={stats?.totalDocuments?.toLocaleString() ?? '0'}
          icon={<DocumentTextIcon className="h-5 w-5 text-primary-600 dark:text-primary-400" />}
          color="bg-primary-50 dark:bg-primary-900/30"
        />
        <StatCard
          title="Total Users"
          value={stats?.totalUsers?.toLocaleString() ?? '0'}
          icon={<UserGroupIcon className="h-5 w-5 text-accent-600 dark:text-accent-400" />}
          color="bg-accent-50 dark:bg-accent-900/30"
          subtitle={`${stats?.activeUsers ?? 0} active`}
        />
        <StatCard
          title="Search Queries"
          value={stats?.totalSearches?.toLocaleString() ?? '0'}
          icon={<MagnifyingGlassIcon className="h-5 w-5 text-success-600 dark:text-success-400" />}
          color="bg-success-50 dark:bg-success-900/30"
          subtitle={`${stats?.totalSearchesToday ?? 0} today`}
        />
        <StatCard
          title="Avg Response Time"
          value={`${stats?.avgResponseTime ?? 0}ms`}
          icon={<ClockIcon className="h-5 w-5 text-warning-600 dark:text-warning-400" />}
          color="bg-warning-50 dark:bg-warning-900/30"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Storage Used</h3>
          <p className="text-xl font-bold text-gray-900 dark:text-white">{stats?.storageUsed ?? 'N/A'}</p>
          <div className="mt-3 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div className="bg-primary-600 h-2 rounded-full" style={{ width: '45%' }} />
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Indexing Rate</h3>
          <p className="text-xl font-bold text-gray-900 dark:text-white">{stats?.indexingRate ?? 0}%</p>
          <div className="mt-3 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${
                (stats?.indexingRate ?? 0) >= 90 ? 'bg-success-500' : (stats?.indexingRate ?? 0) >= 70 ? 'bg-warning-500' : 'bg-error-500'
              }`}
              style={{ width: `${stats?.indexingRate ?? 0}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * UserManagement - 사용자 관리 탭
 */
const UserManagement: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [roleDialogUser, setRoleDialogUser] = useState<AdminUser | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'users', { page, search: searchQuery, status: statusFilter }],
    queryFn: () => adminService.getUsers(page, 20, searchQuery || undefined, statusFilter || undefined),
  });

  const toggleStatusMutation = useMutation({
    mutationFn: ({ userId, status }: { userId: string; status: 'active' | 'inactive' }) =>
      adminService.toggleUserStatus(userId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });

  const updateRolesMutation = useMutation({
    mutationFn: ({ userId, roles }: { userId: string; roles: string[] }) =>
      adminService.updateUserRoles({ userId, roles }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      setRoleDialogUser(null);
    },
  });

  const users = data?.users ?? [];
  const totalPages = Math.ceil((data?.totalCount ?? 0) / 20);

  const openRoleDialog = useCallback((user: AdminUser) => {
    setRoleDialogUser(user);
    setSelectedRoles([...user.roles]);
  }, []);

  const AVAILABLE_ROLES = ['USER', 'KNOWLEDGE_MANAGER', 'ADMIN'];

  const statusBadge = (status: string) => {
    const classes: Record<string, string> = {
      active: 'bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-400',
      inactive: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
      locked: 'bg-error-50 text-error-700 dark:bg-error-900/30 dark:text-error-400',
    };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${classes[status] || classes.inactive}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-4" data-testid="user-management">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 sm:max-w-md">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            placeholder="사용자 검색..."
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            aria-label="Search users"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
          aria-label="Filter by status"
        >
          <option value="">전체 상태</option>
          <option value="active">활성</option>
          <option value="inactive">비활성</option>
          <option value="locked">Locked</option>
        </select>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <ArrowPathIcon className="h-6 w-6 text-primary-500 animate-spin" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-12">
          <ExclamationTriangleIcon className="h-8 w-8 text-error-500 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Failed to load users.</p>
        </div>
      )}

      {/* User Table */}
      {!isLoading && !isError && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Roles</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Last Login</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {users.map((user: AdminUser) => (
                  <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center text-sm font-medium text-primary-700 dark:text-primary-300">
                          {(user.name || user.username).charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">{user.name || user.username}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {user.roles.filter((r) => !r.startsWith('default-')).map((role) => (
                          <span
                            key={role}
                            className="inline-flex items-center px-2 py-0.5 rounded text-2xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
                          >
                            {role}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">{statusBadge(user.status)}</td>
                    <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">
                      {user.lastLogin ? new Date(user.lastLogin).toLocaleString('ko-KR') : 'Never'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openRoleDialog(user)}
                          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
                          title="Edit roles"
                          aria-label={`Edit roles for ${user.name || user.username}`}
                        >
                          <ShieldCheckIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() =>
                            toggleStatusMutation.mutate({
                              userId: user.id,
                              status: user.status === 'active' ? 'inactive' : 'active',
                            })
                          }
                          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
                          title={user.status === 'active' ? 'Deactivate user' : 'Activate user'}
                          aria-label={user.status === 'active' ? `Deactivate ${user.name || user.username}` : `Activate ${user.name || user.username}`}
                        >
                          <NoSymbolIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-500">{data?.totalCount ?? 0} users total</p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Role Edit Dialog */}
      <Transition appear show={roleDialogUser !== null} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={() => setRoleDialogUser(null)}>
          <Transition.Child as={Fragment} enter="ease-out duration-300" enterFrom="opacity-0" enterTo="opacity-100" leave="ease-in duration-200" leaveFrom="opacity-100" leaveTo="opacity-0">
            <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
          </Transition.Child>
          <div className="fixed inset-0 flex items-center justify-center p-4">
            <Transition.Child as={Fragment} enter="ease-out duration-300" enterFrom="opacity-0 scale-95" enterTo="opacity-100 scale-100" leave="ease-in duration-200" leaveFrom="opacity-100 scale-100" leaveTo="opacity-0 scale-95">
              <Dialog.Panel className="mx-auto max-w-sm w-full rounded-xl bg-white dark:bg-gray-800 p-6 shadow-xl">
                <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-white">
                  Edit Roles
                </Dialog.Title>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {roleDialogUser?.name || roleDialogUser?.username}
                </p>

                <div className="mt-4 space-y-2">
                  {AVAILABLE_ROLES.map((role) => (
                    <label
                      key={role}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedRoles.includes(role)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedRoles((prev) => [...prev, role]);
                          } else {
                            setSelectedRoles((prev) => prev.filter((r) => r !== role));
                          }
                        }}
                        className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-900 dark:text-white">{role}</span>
                    </label>
                  ))}
                </div>

                <div className="mt-6 flex justify-end gap-3">
                  <button
                    onClick={() => setRoleDialogUser(null)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      if (roleDialogUser) {
                        updateRolesMutation.mutate({ userId: roleDialogUser.id, roles: selectedRoles });
                      }
                    }}
                    disabled={updateRolesMutation.isPending}
                    className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
                  >
                    {updateRolesMutation.isPending ? 'Saving...' : 'Save Roles'}
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition>
    </div>
  );
};

/**
 * SystemSettingsPanel - 시스템 설정 탭
 */
const SystemSettingsPanel: React.FC = () => {
  const queryClient = useQueryClient();
  const [successMsg, setSuccessMsg] = useState('');

  const { data: settings, isLoading } = useQuery({
    queryKey: ['admin', 'settings'],
    queryFn: () => adminService.getSystemSettings(),
  });

  const [formData, setFormData] = useState<Partial<SystemSettings>>({});

  // Sync form data when settings load
  React.useEffect(() => {
    if (settings) {
      setFormData(settings);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: (data: Partial<SystemSettings>) => adminService.updateSystemSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'settings'] });
      setSuccessMsg('Settings saved successfully.');
      setTimeout(() => setSuccessMsg(''), 3000);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <ArrowPathIcon className="h-6 w-6 text-primary-500 animate-spin" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" data-testid="system-settings">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="chunkSize" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Chunk Size
          </label>
          <input
            id="chunkSize"
            type="number"
            value={formData.chunkSize ?? 512}
            onChange={(e) => setFormData((prev) => ({ ...prev, chunkSize: parseInt(e.target.value) }))}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <label htmlFor="chunkOverlap" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Chunk Overlap
          </label>
          <input
            id="chunkOverlap"
            type="number"
            value={formData.chunkOverlap ?? 50}
            onChange={(e) => setFormData((prev) => ({ ...prev, chunkOverlap: parseInt(e.target.value) }))}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="embeddingModel" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Embedding Model
          </label>
          <input
            id="embeddingModel"
            type="text"
            value={formData.embeddingModel ?? ''}
            onChange={(e) => setFormData((prev) => ({ ...prev, embeddingModel: e.target.value }))}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <label htmlFor="llmModel" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            LLM Model
          </label>
          <input
            id="llmModel"
            type="text"
            value={formData.llmModel ?? ''}
            onChange={(e) => setFormData((prev) => ({ ...prev, llmModel: e.target.value }))}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      <div>
        <label htmlFor="maxUploadSize" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Max Upload Size (MB)
        </label>
        <input
          id="maxUploadSize"
          type="number"
          value={formData.maxUploadSize ?? 50}
          onChange={(e) => setFormData((prev) => ({ ...prev, maxUploadSize: parseInt(e.target.value) }))}
          className="w-full sm:max-w-xs px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Toggle settings */}
      <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">Indexing Enabled</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Enable automatic document indexing.</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={formData.indexingEnabled ?? true}
            onClick={() => setFormData((prev) => ({ ...prev, indexingEnabled: !(prev.indexingEnabled ?? true) }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 ${
              formData.indexingEnabled ?? true ? 'bg-primary-600' : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${formData.indexingEnabled ?? true ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">Maintenance Mode</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Restrict access during maintenance.</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={formData.maintenanceMode ?? false}
            onClick={() => setFormData((prev) => ({ ...prev, maintenanceMode: !(prev.maintenanceMode ?? false) }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 ${
              formData.maintenanceMode ? 'bg-warning-500' : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${formData.maintenanceMode ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
        </div>
      </div>

      {/* Error */}
      {updateMutation.isError && (
        <div className="flex items-center gap-2 p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg" role="alert">
          <ExclamationTriangleIcon className="h-5 w-5 text-error-500" />
          <span className="text-sm text-error-700 dark:text-error-300">Failed to save settings.</span>
        </div>
      )}

      {/* Success */}
      {successMsg && (
        <div className="flex items-center gap-2 p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
          <CheckCircleIcon className="h-5 w-5 text-success-500" />
          <span className="text-sm text-success-700 dark:text-success-300">{successMsg}</span>
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {updateMutation.isPending && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
          Save Settings
        </button>
      </div>
    </form>
  );
};

/**
 * CacheManagementPanel - 캐시 관리 탭
 */
const CacheManagementPanel: React.FC = () => {
  const queryClient = useQueryClient();
  const [confirmClear, setConfirmClear] = useState(false);
  const [resultMsg, setResultMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [invalidatePattern, setInvalidatePattern] = useState('');

  const { data: stats, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'cache-stats'],
    queryFn: () => adminService.getCacheStats(),
    refetchInterval: 15000,
  });

  const { data: status } = useQuery({
    queryKey: ['admin', 'cache-status'],
    queryFn: () => adminService.getCacheStatus(),
  });

  const clearMutation = useMutation({
    mutationFn: () => adminService.clearCache(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'cache-stats'] });
      setResultMsg({ type: 'success', text: data.message });
      setConfirmClear(false);
      setTimeout(() => setResultMsg(null), 5000);
    },
    onError: () => {
      setResultMsg({ type: 'error', text: 'Failed to clear cache.' });
      setTimeout(() => setResultMsg(null), 5000);
    },
  });

  const invalidateMutation = useMutation({
    mutationFn: (pattern?: string) => adminService.invalidateCache(pattern),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'cache-stats'] });
      setResultMsg({ type: 'success', text: data.message });
      setInvalidatePattern('');
      setTimeout(() => setResultMsg(null), 5000);
    },
    onError: () => {
      setResultMsg({ type: 'error', text: 'Failed to invalidate cache.' });
      setTimeout(() => setResultMsg(null), 5000);
    },
  });

  const resetStatsMutation = useMutation({
    mutationFn: () => adminService.resetCacheStats(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'cache-stats'] });
      setResultMsg({ type: 'success', text: 'Cache statistics reset.' });
      setTimeout(() => setResultMsg(null), 5000);
    },
  });

  const hitRate = stats ? (stats.hit_rate * 100).toFixed(1) : '0';

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
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Failed to load cache stats.</p>
        <button onClick={() => refetch()} className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700">
          <ArrowPathIcon className="h-4 w-4" /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="cache-management">
      {/* Status Banner */}
      <div className={`flex items-center gap-3 p-4 rounded-xl border ${
        status?.status === 'available'
          ? 'bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800'
          : 'bg-warning-50 dark:bg-warning-900/20 border-warning-200 dark:border-warning-800'
      }`}>
        <ServerStackIcon className={`h-5 w-5 ${status?.status === 'available' ? 'text-success-600' : 'text-warning-600'}`} />
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            Redis Cache — {status?.status === 'available' ? 'Online' : status?.status ?? 'Unknown'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{status?.message}</p>
        </div>
        <button
          onClick={() => refetch()}
          className="p-1.5 rounded-lg hover:bg-white/50 dark:hover:bg-gray-700/50 text-gray-500"
          title="Refresh"
        >
          <ArrowPathIcon className="h-4 w-4" />
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          title="Hit Rate"
          value={`${hitRate}%`}
          icon={<CheckCircleIcon className="h-5 w-5 text-success-600 dark:text-success-400" />}
          color="bg-success-50 dark:bg-success-900/30"
          subtitle={`${stats?.hits ?? 0} hits / ${stats?.misses ?? 0} misses`}
        />
        <StatCard
          title="Total Requests"
          value={stats?.total_requests?.toLocaleString() ?? '0'}
          icon={<ChartBarIcon className="h-5 w-5 text-primary-600 dark:text-primary-400" />}
          color="bg-primary-50 dark:bg-primary-900/30"
        />
        <StatCard
          title="Cache Size"
          value={stats?.size === -1 ? 'N/A (Redis)' : String(stats?.size ?? 0)}
          icon={<ServerStackIcon className="h-5 w-5 text-accent-600 dark:text-accent-400" />}
          color="bg-accent-50 dark:bg-accent-900/30"
          subtitle={`Backend: ${stats?.backend ?? 'unknown'}`}
        />
        <StatCard
          title="TTL"
          value={`${Math.floor((stats?.ttl_seconds ?? 0) / 60)}min`}
          icon={<ClockIcon className="h-5 w-5 text-warning-600 dark:text-warning-400" />}
          color="bg-warning-50 dark:bg-warning-900/30"
          subtitle={`${stats?.ttl_seconds ?? 0}s`}
        />
      </div>

      {/* Actions */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 space-y-5">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">Cache Actions</h3>

        {/* Clear All Cache */}
        <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">Clear All Cache</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Remove all cached search results. This cannot be undone.</p>
          </div>
          {!confirmClear ? (
            <button
              onClick={() => setConfirmClear(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-error-600 rounded-lg hover:bg-error-700 transition-colors"
            >
              <TrashIcon className="h-4 w-4" />
              Clear Cache
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setConfirmClear(false)}
                className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={() => clearMutation.mutate()}
                disabled={clearMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-error-600 rounded-lg hover:bg-error-700 disabled:opacity-50"
              >
                {clearMutation.isPending && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
                Confirm Clear
              </button>
            </div>
          )}
        </div>

        {/* Pattern Invalidation */}
        <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg space-y-3">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">Invalidate by Pattern</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Delete cache entries matching a pattern (e.g., &quot;search_cache:*&quot;).</p>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={invalidatePattern}
              onChange={(e) => setInvalidatePattern(e.target.value)}
              placeholder="Pattern (e.g., search_cache:*)"
              className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            />
            <button
              onClick={() => invalidateMutation.mutate(invalidatePattern || undefined)}
              disabled={invalidateMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-warning-600 rounded-lg hover:bg-warning-700 disabled:opacity-50 whitespace-nowrap"
            >
              {invalidateMutation.isPending && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
              Invalidate
            </button>
          </div>
        </div>

        {/* Reset Stats */}
        <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">Reset Statistics</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Reset hit/miss counters to zero. Cache data is preserved.</p>
          </div>
          <button
            onClick={() => resetStatsMutation.mutate()}
            disabled={resetStatsMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50"
          >
            {resetStatsMutation.isPending && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
            Reset Stats
          </button>
        </div>
      </div>

      {/* Result Message */}
      {resultMsg && (
        <div className={`flex items-center gap-2 p-3 rounded-lg border ${
          resultMsg.type === 'success'
            ? 'bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800'
            : 'bg-error-50 dark:bg-error-900/20 border-error-200 dark:border-error-800'
        }`}>
          {resultMsg.type === 'success'
            ? <CheckCircleIcon className="h-5 w-5 text-success-500" />
            : <ExclamationTriangleIcon className="h-5 w-5 text-error-500" />
          }
          <span className={`text-sm ${resultMsg.type === 'success' ? 'text-success-700 dark:text-success-300' : 'text-error-700 dark:text-error-300'}`}>
            {resultMsg.text}
          </span>
        </div>
      )}
    </div>
  );
};

/**
 * AuditLogTable - 감사 로그 탭
 */
const AuditLogTable: React.FC = () => {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'audit-logs', { page, action: actionFilter }],
    queryFn: () => adminService.getAuditLogs(page, 50, actionFilter ? { action: actionFilter } : undefined),
  });

  const logs = data?.logs ?? [];
  const totalPages = Math.ceil((data?.totalCount ?? 0) / 50);

  return (
    <div className="space-y-4" data-testid="audit-logs">
      {/* Filter */}
      <div className="flex gap-3">
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
          aria-label="Filter by action"
        >
          <option value="">All Actions</option>
          <option value="LOGIN">Login</option>
          <option value="LOGOUT">Logout</option>
          <option value="UPLOAD">Upload</option>
          <option value="DELETE">Delete</option>
          <option value="SEARCH">Search</option>
          <option value="SETTINGS_CHANGE">Settings Change</option>
        </select>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <ArrowPathIcon className="h-6 w-6 text-primary-500 animate-spin" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-12">
          <ExclamationTriangleIcon className="h-8 w-8 text-error-500 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Failed to load audit logs.</p>
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Timestamp</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Action</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Resource</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {logs.map((log: AuditLog) => (
                  <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                    <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString('ko-KR')}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{log.userName}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                      {log.resource}
                      {log.details && (
                        <span className="block text-xs text-gray-400 truncate max-w-xs">{log.details}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 font-mono">{log.ipAddress}</td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center text-sm text-gray-500">
                      No audit logs found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-500">{data?.totalCount ?? 0} logs total</p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * AdminPage 메인 컴포넌트
 */
const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('stats');

  return (
    <div className="space-y-6" data-testid="admin-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Administration</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage users, system settings, and monitor activity
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Tab Navigation */}
        <div className="lg:w-56 flex-shrink-0">
          <nav className="space-y-1" aria-label="Admin navigation">
            {ADMIN_TABS.map((tab) => {
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
          {activeTab === 'stats' && <SystemStatsPanel />}
          {activeTab === 'users' && <UserManagement />}
          {activeTab === 'cache' && <CacheManagementPanel />}
          {activeTab === 'settings' && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <SystemSettingsPanel />
            </div>
          )}
          {activeTab === 'audit-logs' && <AuditLogTable />}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
