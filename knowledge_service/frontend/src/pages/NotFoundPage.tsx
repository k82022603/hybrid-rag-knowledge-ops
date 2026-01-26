/**
 * NotFoundPage - 404 에러 페이지
 *
 * Tailwind CSS 기반
 */
import { useNavigate } from 'react-router-dom';
import { HomeIcon } from '@heroicons/react/24/outline';

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div
      className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4"
      data-testid="not-found-page"
    >
      <p className="text-8xl font-bold text-gray-200 dark:text-gray-700">404</p>
      <h1 className="mt-4 text-xl font-semibold text-gray-900 dark:text-white">
        Page Not Found
      </h1>
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400 max-w-md">
        The page you are looking for does not exist or has been moved.
      </p>
      <button
        onClick={() => navigate('/dashboard')}
        className="mt-6 inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors shadow-sm"
      >
        <HomeIcon className="h-5 w-5" />
        Go to Dashboard
      </button>
    </div>
  );
};

export default NotFoundPage;
