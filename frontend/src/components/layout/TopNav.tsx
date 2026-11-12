import { useLocation } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

const pageTitle: Record<string, string> = {
  '/': 'Dashboard',
  '/students': 'Students',
  '/courses': 'Courses',
  '/attendance': 'Attendance',
  '/assessments': 'Assessments',
  '/engagement': 'LMS Engagement',
  '/risk': 'Risk Intelligence',
  '/support-cases': 'Support Cases',
  '/interventions': 'Interventions',
  '/outcomes': 'Outcomes',
  '/data-quality': 'Data Quality',
  '/reports': 'Reports',
  '/settings': 'Settings',
};

export default function TopNav() {
  const { pathname } = useLocation();
  const { user } = useAuth();

  const title = Object.entries(pageTitle).find(([path]) =>
    path === pathname || (path !== '/' && pathname.startsWith(path))
  )?.[1] ?? 'Platform';

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <h1 className="text-lg font-semibold text-gray-800">{title}</h1>
      <div className="flex items-center gap-4">
        <button className="text-gray-400 hover:text-gray-600">
          <Bell size={20} />
        </button>
        <div className="text-sm text-gray-600">
          {user?.full_name || user?.username}
        </div>
      </div>
    </header>
  );
}

