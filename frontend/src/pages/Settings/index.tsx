import { useAuth } from '../../contexts/AuthContext';
import { PageHeader } from '../../components/common';

export default function Settings() {
  const { user } = useAuth();
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  return (
    <div>
      <PageHeader title="Platform Settings" subtitle="Read-only environment and account details" />
      <section className="max-w-2xl rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <dl className="space-y-4">
          <div><dt className="text-xs font-medium uppercase text-gray-500">Signed-in account</dt><dd className="mt-1 text-sm text-gray-900">{user?.username ?? 'Unknown'} · {user?.role?.replace(/_/g, ' ') ?? 'Unknown role'}</dd></div>
          <div><dt className="text-xs font-medium uppercase text-gray-500">API base URL</dt><dd className="mt-1 break-all font-mono text-sm text-gray-900">{apiUrl}</dd></div>
          <div><dt className="text-xs font-medium uppercase text-gray-500">Risk cutoff</dt><dd className="mt-1 text-sm text-gray-900">2026-07-01 (defined by the current academic-year configuration)</dd></div>
        </dl>
        <p className="mt-6 border-t pt-4 text-sm text-gray-500">Runtime configuration is supplied through environment variables. This page does not expose secret values or provide controls that are not persisted by the backend.</p>
      </section>
    </div>
  );
}
