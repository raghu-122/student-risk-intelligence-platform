import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Sidebar from './components/layout/Sidebar';
import TopNav from './components/layout/TopNav';
import Login from './pages/Login/index';
import Dashboard from './pages/Dashboard';
import Students from './pages/Students';
import StudentDetail from './pages/Students/StudentDetail';
import Courses from './pages/Courses';
import Attendance from './pages/Attendance';
import Assessments from './pages/Assessments';
import Engagement from './pages/Engagement';
import RiskIntelligence from './pages/RiskIntelligence';
import SupportCases from './pages/SupportCases';
import Interventions from './pages/Interventions';
import Outcomes from './pages/Outcomes';
import DataQuality from './pages/DataQuality';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import { LoadingSpinner } from './components/common';

function ProtectedLayout() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingSpinner message="Authenticating..." />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopNav />
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/students" element={<Students />} />
            <Route path="/students/:id" element={<StudentDetail />} />
            <Route path="/courses" element={<Courses />} />
            <Route path="/attendance" element={<Attendance />} />
            <Route path="/assessments" element={<Assessments />} />
            <Route path="/engagement" element={<Engagement />} />
            <Route path="/risk" element={<RiskIntelligence />} />
            <Route path="/support-cases" element={<SupportCases />} />
            <Route path="/interventions" element={<Interventions />} />
            <Route path="/outcomes" element={<Outcomes />} />
            <Route path="/data-quality" element={<DataQuality />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
