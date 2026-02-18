/**
 * SearchPage - 검색 페이지
 *
 * 채팅형 검색과 키워드 검색 두 가지 모드 제공
 * Tailwind CSS 기반
 */
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ChatBubbleLeftRightIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import ChatSearch from '@/components/search/ChatSearch';
import KeywordSearch from '@/components/search/KeywordSearch';

type SearchTab = 'chat' | 'keyword';

const TABS: { key: SearchTab; label: string; icon: React.ReactNode; description: string }[] = [
  {
    key: 'chat',
    label: 'Chat Search',
    icon: <ChatBubbleLeftRightIcon className="h-5 w-5" />,
    description: 'Ask questions in natural language',
  },
  {
    key: 'keyword',
    label: 'Keyword Search',
    icon: <MagnifyingGlassIcon className="h-5 w-5" />,
    description: 'Search by keywords with filters',
  },
];

/**
 * SearchPage - 검색 페이지 메인 컴포넌트
 */
const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || undefined;
  const [activeTab, setActiveTab] = useState<SearchTab>('chat');

  return (
    <div className="space-y-6" data-testid="search-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Search</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Search through the knowledge base using chat or keyword search
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-4" aria-label="Search tabs" role="tablist">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                role="tab"
                aria-selected={isActive}
                aria-controls={`tab-panel-${tab.key}`}
                className={`group relative flex items-center gap-2 px-1 py-4 text-sm font-medium transition-colors border-b-2 ${isActive
                    ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:border-gray-600'
                  }`}
              >
                <span
                  className={
                    isActive
                      ? 'text-primary-500 dark:text-primary-400'
                      : 'text-gray-400 group-hover:text-gray-500 dark:text-gray-500'
                  }
                >
                  {tab.icon}
                </span>
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div
        id={`tab-panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
      >
        {activeTab === 'chat' && <ChatSearch initialQuery={initialQuery} />}
        {activeTab === 'keyword' && <KeywordSearch />}
      </div>
    </div>
  );
};

export default SearchPage;
