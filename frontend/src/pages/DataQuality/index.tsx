import { useEffect, useState } from 'react';
import RecordListPage, { RecordColumn } from '../../components/common/RecordListPage';
import { dataQualityApi } from '../../services/api';
import { ErrorState, LoadingSpinner } from '../../components/common';

interface QualitySummary {
  total_issues?: number;
  injected_anomalies?: number;
  by_type?: { type: string; count: number }[];
  by_severity?: { severity: string; count: number }[];
  anomaly_descriptions?: Record<string, string>;
}

const columns: RecordColumn[] = [
  { key: 'issue_type', label: 'Issue' },
  { key: 'severity', label: 'Severity' },
  { key: 'affected_entity', label: 'Entity' },
  { key: 'affected_record_id', label: 'Record' },
  { key: 'detection_status', label: 'Detection' },
  { key: 'explanation', label: 'Explanation' },
  { key: 'is_injected_anomaly', label: 'Injected' },
];

export default function DataQuality() {
  const [summary, setSummary] = useState<QualitySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [checking, setChecking] = useState(false);

  const loadSummary = () => {
    setLoading(true);
    setError('');
    dataQualityApi.getSummary()
      .then((response) => setSummary(response.data))
      .catch(() => setError('Could not load data-quality summary.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadSummary(); }, []);

  const runChecks = async () => {
    setChecking(true);
    setActionError('');
    try {
      await dataQualityApi.runChecks();
      setRefresh((value) => value + 1);
      loadSummary();
    } catch {
      setActionError('Could not run anomaly checks. Ensure the backend is available.');
    } finally {
      setChecking(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading data-quality summary..." />;
  if (error) return <ErrorState message={error} onRetry={loadSummary} />;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Data Quality & Anomalies</h2>
          <p className="mt-1 text-sm text-gray-500">Run the five anomaly detectors and review persisted findings.</p>
        </div>
        <button onClick={runChecks} disabled={checking} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
          {checking ? 'Checking…' : 'Run checks'}
        </button>
      </div>
      {actionError && <p role="alert" className="text-sm text-red-600">{actionError}</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border bg-white p-5 shadow-sm"><p className="text-sm text-gray-500">Recorded issues</p><p className="mt-1 text-2xl font-semibold">{summary?.total_issues ?? 0}</p></div>
        <div className="rounded-xl border bg-white p-5 shadow-sm"><p className="text-sm text-gray-500">Injected anomaly findings</p><p className="mt-1 text-2xl font-semibold">{summary?.injected_anomalies ?? 0}</p></div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <h3 className="mb-3 font-semibold">Findings by type</h3>
          {(summary?.by_type ?? []).map((item) => <div key={item.type} className="flex justify-between gap-4 border-t py-2 text-sm"><span>{item.type}</span><strong>{item.count}</strong></div>)}
        </section>
        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <h3 className="mb-3 font-semibold">Detector coverage</h3>
          {Object.entries(summary?.anomaly_descriptions ?? {}).map(([type, description]) => <div key={type} className="border-t py-2"><p className="text-xs font-semibold text-gray-700">{type}</p><p className="text-sm text-gray-500">{description}</p></div>)}
        </section>
      </div>
      <RecordListPage key={refresh} title="Detected issues" subtitle="Persisted data-quality findings" load={dataQualityApi.list} columns={columns} pageSize={50} filterKey="issue_type" filterLabel="Issue type" filterPlaceholder="Filter by anomaly type" />
    </div>
  );
}
