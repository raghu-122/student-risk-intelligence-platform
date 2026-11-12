import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import RecordListPage, { RecordColumn } from '../../components/common/RecordListPage';
import { ErrorState, LoadingSpinner } from '../../components/common';
import { outcomesApi } from '../../services/api';

interface OutcomeSummary {
  total?: number;
  distribution?: { label: string; count: number; pct: number }[];
  note?: string;
}

const columns: RecordColumn[] = [
  { key: 'student_id', label: 'Student' },
  { key: 'outcome_label', label: 'Outcome' },
  { key: 'baseline_risk_score', label: 'Baseline risk' },
  { key: 'academic_performance_change', label: 'Academic change (pp)' },
  { key: 'attendance_change', label: 'Attendance change (pp)' },
  { key: 'engagement_change', label: 'Engagement change' },
  { key: 'evaluation_period_start', label: 'Period start' },
  { key: 'evaluation_period_end', label: 'Period end' },
];

export default function Outcomes() {
  const [summary, setSummary] = useState<OutcomeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [saving, setSaving] = useState(false);
  const [refresh, setRefresh] = useState(0);

  const loadSummary = () => {
    setLoading(true);
    setError('');
    outcomesApi.getDistribution()
      .then((response) => setSummary(response.data))
      .catch(() => setError('Could not load outcome summary.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadSummary(); }, []);

  if (loading) return <LoadingSpinner message="Loading outcome summary..." />;
  if (error) return <ErrorState message={error} onRetry={loadSummary} />;

  const evaluate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setActionError('');
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await outcomesApi.evaluate({
        student_id: String(form.get('student_id')).trim(),
        enrollment_id: String(form.get('enrollment_id')).trim(),
        intervention_id: String(form.get('intervention_id')).trim() || null,
        baseline_cutoff: String(form.get('baseline_cutoff')),
        evaluation_period_start: String(form.get('evaluation_period_start')),
        evaluation_period_end: String(form.get('evaluation_period_end')),
      });
      formElement.reset();
      setRefresh((value) => value + 1);
      try {
        const response = await outcomesApi.getDistribution();
        setSummary(response.data);
      } catch {
        setActionError('The outcome was saved, but its summary could not be refreshed.');
      }
    } catch {
      setActionError('Could not evaluate this outcome. Check the student, enrollment, and period dates.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {(summary?.distribution ?? []).map((item) => (
          <div key={item.label} className="rounded-xl border bg-white p-5 shadow-sm">
            <p className="text-sm text-gray-500">{item.label}</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{item.count.toLocaleString()}</p>
            <p className="mt-1 text-xs text-gray-400">{item.pct}% of evaluated outcomes</p>
          </div>
        ))}
      </div>
      {summary?.note && <p className="text-sm text-gray-500">{summary.note}</p>}
      <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="mb-4 font-semibold text-gray-800">Evaluate an outcome</h2>
        <form onSubmit={evaluate} className="grid gap-3 md:grid-cols-2">
          <input name="student_id" required placeholder="Student ID" className="rounded-lg border px-3 py-2 text-sm" />
          <input name="enrollment_id" required placeholder="Enrollment ID" className="rounded-lg border px-3 py-2 text-sm" />
          <input name="intervention_id" placeholder="Intervention ID (optional)" className="rounded-lg border px-3 py-2 text-sm" />
          <label className="text-xs text-gray-500">Baseline cutoff<input name="baseline_cutoff" type="date" defaultValue="2026-07-01" required className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm" /></label>
          <label className="text-xs text-gray-500">Evaluation start<input name="evaluation_period_start" type="date" defaultValue="2026-07-02" required className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm" /></label>
          <label className="text-xs text-gray-500">Evaluation end<input name="evaluation_period_end" type="date" defaultValue="2026-12-15" required className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm" /></label>
          <button disabled={saving} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 md:col-span-2">{saving ? 'Evaluating…' : 'Evaluate and save'}</button>
        </form>
        {actionError && <p role="alert" className="mt-3 text-sm text-red-600">{actionError}</p>}
      </section>
      <RecordListPage key={refresh} title="Outcomes" subtitle="Observed change across the evaluation window; not causal attribution" load={outcomesApi.list} columns={columns} pageSize={25} filterKey="student_id" filterLabel="Student ID" filterPlaceholder="Filter by student ID" />
    </div>
  );
}
