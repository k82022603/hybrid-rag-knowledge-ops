/**
 * DashboardPage - Dashboard page route component
 *
 * Renders the feature-based Dashboard component.
 * This page is the default landing page after login.
 *
 * STORY-041: Dashboard UI implementation
 * - AC1: Welcome message with user name
 * - AC2: StatCards (documents, searches, users, response time)
 * - AC3: Recent 5 search records
 * - AC4: Quick search navigates to /search
 * - AC5: Sidebar menu navigation
 */
import React from 'react';
import { Dashboard } from '@/features/dashboard';

const DashboardPage: React.FC = () => {
  return <Dashboard />;
};

export default DashboardPage;
