import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';
import { Users, AlertTriangle, Zap, TrendingUp } from 'lucide-react';
import { dashboardApi } from '../../services/api';
import { LoadingSpinner, ErrorState, StatCard, RiskBadge } from '../../components/common';

const RISK_COLORS: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
  INSUFFICIENT_DATA: '#94a3b8',
};

export default function Dashboard() {
  const [stats, setStats] = useState<Record<string, number> | null>(null);
  const [riskDist, setRiskDist] = useState<{ category: string; count: number }[]>([]);
  const [atRisk, setAtRisk] = useState<unknown[]>([]);
  const [recentInterventions, setRecentInterventions] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      dashboardApi.getStats(),
      dashboardApi.getRiskDistribution(),
      dashboardApi.getAtRiskStudents(8),
      dashboardApi.getRecentInterventions(5),
    ])
      .then(([s, rd, ar, ri]) => {
        setStats(s.data);
        setRiskDist(rd.data || []);
        setAtRisk(ar.data || []);
        setRecentInterventions(ri.data || []);
      })
      .catch(() => setError('Failed to load dashboard data'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner message="Loading dashboard..." />;
  if (error) return <ErrorState message={error} />;

  const pieData = riskDist.map((r: { category: string; count: number }) => ({
    name: r.category, value: r.count,
  }));

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Students" value={stats?.total_students ?? 0}
          icon={<Users size={22} />} color="indigo" />
        <StatCard label="At Risk Students" value={stats?.students_at_risk ?? stats?.at_risk_students ?? 0}
          sub={`${stats?.high_risk_students ?? stats?.critical_students ?? 0} high risk`}
          icon={<AlertTriangle size={22} />} color="red" />
        <StatCard label="Open Interventions" value={stats?.active_interventions ?? stats?.open_interventions ?? 0}
          icon={<Zap size={22} />} color="orange" />
        <StatCard label="Students Improving" value={stats?.students_improving ?? stats?.outcomes_tracked ?? 0}
          icon={<TrendingUp size={22} />} color="green" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Distribution Pie */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-700 mb-4">Risk Distribution</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={RISK_COLORS[entry.name] || '#94a3b8'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-400 text-sm text-center py-10">No risk data</p>}
        </div>

        {/* Risk Bar Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-700 mb-4">Students by Risk Category</h3>
          {riskDist.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={riskDist} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="category" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[4,4,0,0]}>
                  {riskDist.map((entry) => (
                    <Cell key={entry.category} fill={RISK_COLORS[entry.category] || '#94a3b8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-400 text-sm text-center py-10">No data</p>}
        </div>
      </div>

      {/* At-Risk Students Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-700">Top At-Risk Students</h3>
          <Link to="/risk" className="text-sm text-indigo-600 hover:underline">View all →</Link>
        </div>
        {(atRisk as Record<string, unknown>[]).length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-2 font-medium">Student</th>
                  <th className="pb-2 font-medium">Risk Score</th>
                  <th className="pb-2 font-medium">Category</th>
                  <th className="pb-2 font-medium">Department</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(atRisk as Record<string, unknown>[]).map((s) => (
                  <tr key={s.student_id as string} className="hover:bg-gray-50">
                    <td className="py-2.5">
                      <Link to={`/students/${s.student_id}`} className="text-indigo-600 hover:underline font-medium">
                        {s.full_name as string}
                      </Link>
                    </td>
                    <td className="py-2.5 font-mono">{typeof s.risk_score === 'number' ? s.risk_score.toFixed(1) : '—'}</td>
                    <td className="py-2.5">
                      <RiskBadge category={s.risk_category as string} />
                    </td>
                    <td className="py-2.5 text-gray-500">{s.department as string}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="text-gray-400 text-sm">No high-risk students found</p>}
      </div>

      {/* Recent Interventions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-700">Recent Interventions</h3>
          <Link to="/interventions" className="text-sm text-indigo-600 hover:underline">View all →</Link>
        </div>
        {(recentInterventions as Record<string, unknown>[]).length > 0 ? (
          <div className="space-y-3">
            {(recentInterventions as Record<string, unknown>[]).map((i) => (
              <div key={i.intervention_id as string} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div>
                  <span className="font-medium text-sm text-gray-800">{(i.intervention_type as string).replace(/_/g, ' ')}</span>
                  <span className="text-xs text-gray-400 ml-2">· {i.student_id as string}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  i.intervention_status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                  i.intervention_status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-600'
                }`}>{i.intervention_status as string}</span>
              </div>
            ))}
          </div>
        ) : <p className="text-gray-400 text-sm">No recent interventions</p>}
      </div>
    </div>
  );
}

