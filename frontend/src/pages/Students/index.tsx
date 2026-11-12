import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { studentsApi } from '../../services/api';
import { LoadingSpinner, ErrorState, EmptyState, Pagination, RiskBadge, Badge, PageHeader } from '../../components/common';
import { Search } from 'lucide-react';

export default function Students() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<{ items: Record<string, unknown>[]; total: number; pages: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState(searchParams.get('search') || '');

  const page = parseInt(searchParams.get('page') || '1');

  useEffect(() => {
    setLoading(true);
    studentsApi.list({ page, page_size: 20, search: search || undefined })
      .then(r => setData(r.data))
      .catch(() => setError('Failed to load students'))
      .finally(() => setLoading(false));
  }, [page, search]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams(prev => { const p = new URLSearchParams(prev); p.set('page', '1'); if (search) p.set('search', search); else p.delete('search'); return p; });
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorState message={error} />;

  const statusColor = (s: string): 'green' | 'gray' | 'red' | 'orange' | 'blue' => {
    return ({ ACTIVE: 'green', INACTIVE: 'gray', WITHDRAWN: 'red', TRANSFERRED: 'orange', GRADUATED: 'blue' } as Record<string, 'green' | 'gray' | 'red' | 'orange' | 'blue'>)[s] ?? 'gray';
  };

  return (
    <div>
      <PageHeader title="Students" subtitle={`${data?.total ?? 0} total students`} />

      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by name or ID..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <button type="submit" className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">Search</button>
      </form>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {!data?.items.length ? <EmptyState message="No students found" /> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Program</th>
                <th className="px-4 py-3 font-medium">Year</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.items.map((s) => (
                <tr key={s.student_id as string} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{s.student_id as string}</td>
                  <td className="px-4 py-3">
                    <Link to={`/students/${s.student_id}`} className="text-indigo-600 hover:underline font-medium">
                      {s.first_name as string} {s.last_name as string}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{s.program as string}</td>
                  <td className="px-4 py-3 text-gray-600">{s.academic_year as string}</td>
                  <td className="px-4 py-3"><Badge label={s.current_status as string} color={statusColor(s.current_status as string)} /></td>
                  <td className="px-4 py-3">{s.latest_risk_category ? <RiskBadge category={s.latest_risk_category as string} /> : <span className="text-gray-300 text-xs">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <Pagination page={page} totalPages={data?.pages ?? 1} onPageChange={p => setSearchParams({ page: String(p) })} />
    </div>
  );
}

