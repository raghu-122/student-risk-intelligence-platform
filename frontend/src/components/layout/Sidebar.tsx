import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Users, BookOpen, CalendarCheck, FileText,
  Monitor, AlertTriangle, Briefcase, Zap, TrendingUp,
  ShieldAlert, BarChart3, Settings, LogOut, GraduationCap
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/students', label: 'Students', icon: Users },
  { path: '/courses', label: 'Courses', icon: BookOpen },
  { path: '/attendance', label: 'Attendance', icon: CalendarCheck },
  { path: '/assessments', label: 'Assessments', icon: FileText },
  { path: '/engagement', label: 'LMS Engagement', icon: Monitor },
  { path: '/risk', label: 'Risk Intelligence', icon: AlertTriangle },
  { path: '/support-cases', label: 'Support Cases', icon: Briefcase },
  { path: '/interventions', label: 'Interventions', icon: Zap },
  { path: '/outcomes', label: 'Outcomes', icon: TrendingUp },
  { path: '/data-quality', label: 'Data Quality', icon: ShieldAlert },
  { path: '/reports', label: 'Reports', icon: BarChart3 },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white w-64 min-w-64">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-700">
        <GraduationCap className="text-indigo-400" size={28} />
        <div>
          <div className="font-bold text-sm leading-tight">Student Risk</div>
          <div className="text-xs text-gray-400 leading-tight">Intelligence Platform</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4">
        {navItems.map(({ path, label, icon: Icon }) => {
          const active = pathname === path || (path !== '/' && pathname.startsWith(path));
          return (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-6 py-2.5 text-sm transition-colors ${
                active ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="border-t border-gray-700 px-6 py-4">
        <div className="text-xs text-gray-400 truncate">{user?.username}</div>
        <div className="text-xs text-indigo-400 mb-2">{user?.role?.replace(/_/g, ' ')}</div>
        <button
          onClick={logout}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <LogOut size={16} /> Sign out
        </button>
      </div>
    </div>
  );
}

