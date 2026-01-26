import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import MainLayout from '@/components/common/MainLayout';
import DashboardPage from '@/pages/DashboardPage';
import SearchPage from '@/pages/SearchPage';
import KnowledgePage from '@/pages/KnowledgePage';
import BookmarkPage from '@/pages/BookmarkPage';
import ProfilePage from '@/pages/ProfilePage';
import AdminPage from '@/pages/AdminPage';
import DocumentUploadPage from '@/pages/DocumentUploadPage';
import NotFoundPage from '@/pages/NotFoundPage';
import LoginPage from '@/pages/LoginPage';
import { ProtectedRoute, RequireKnowledgeManager, RequireAdmin } from '@/auth';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route
            path="knowledge"
            element={
              <RequireKnowledgeManager>
                <KnowledgePage />
              </RequireKnowledgeManager>
            }
          />
          <Route path="bookmarks" element={<BookmarkPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route
            path="admin"
            element={
              <RequireAdmin>
                <AdminPage />
              </RequireAdmin>
            }
          />
          <Route
            path="upload"
            element={
              <RequireKnowledgeManager>
                <DocumentUploadPage />
              </RequireKnowledgeManager>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
