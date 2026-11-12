import { FormEvent, useState } from 'react';
import RecordListPage, { RecordColumn, RecordRow } from '../../components/common/RecordListPage';
import { supportCasesApi } from '../../services/api';

const columns: RecordColumn[] = [
  { key: 'case_id', label: 'Case' },
  { key: 'student_id', label: 'Student' },
  { key: 'case_type', label: 'Type' },
  { key: 'priority', label: 'Priority' },
  { key: 'case_status', label: 'Status' },
  { key: 'assigned_staff_id', label: 'Assigned staff' },
  { key: 'opened_at', label: 'Opened' },
];

const transitions: Record<string, string[]> = {
  OPEN: ['ASSIGNED'],
  ASSIGNED: ['IN_PROGRESS', 'OPEN'],
  IN_PROGRESS: ['RESOLVED', 'ASSIGNED'],
  RESOLVED: ['CLOSED', 'IN_PROGRESS'],
  CLOSED: ['IN_PROGRESS'],
};

export default function SupportCases() {
  const [refresh, setRefresh] = useState(0);
  const [actionError, setActionError] = useState('');
  const [saving, setSaving] = useState(false);

  const createCase = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setActionError('');
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await supportCasesApi.create({
        student_id: String(form.get('student_id')).trim(),
        case_type: String(form.get('case_type')),
        priority: String(form.get('priority')),
        description: String(form.get('description')).trim(),
        assigned_staff_id: String(form.get('assigned_staff_id')).trim() || null,
      });
      formElement.reset();
      setRefresh((value) => value + 1);
    } catch {
      setActionError('Could not create support case. Verify the student and staff IDs.');
    } finally {
      setSaving(false);
    }
  };

  const rowActions = (row: RecordRow, reload: () => void) => {
    const next = transitions[String(row.case_status)]?.[0];
    if (!next) return <span className="text-xs text-gray-400">Final state</span>;
    return (
      <button
        onClick={async () => {
          setActionError('');
          try {
            await supportCasesApi.transition(String(row.case_id), next);
            reload();
          } catch {
            setActionError(`Could not move case ${String(row.case_id)} to ${next}.`);
          }
        }}
        className="whitespace-nowrap rounded border px-2 py-1 text-xs text-indigo-700 hover:bg-indigo-50"
      >
        Move to {next.replace(/_/g, ' ')}
      </button>
    );
  };

  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="mb-4 font-semibold text-gray-800">Open a support case</h2>
        <form onSubmit={createCase} className="grid gap-3 md:grid-cols-2">
          <input name="student_id" required placeholder="Student ID" className="rounded-lg border px-3 py-2 text-sm" />
          <input name="assigned_staff_id" placeholder="Assigned staff ID (optional)" className="rounded-lg border px-3 py-2 text-sm" />
          <select name="case_type" className="rounded-lg border px-3 py-2 text-sm">
            {['ACADEMIC', 'ATTENDANCE', 'WELFARE', 'BEHAVIORAL', 'FINANCIAL'].map((value) => <option key={value}>{value}</option>)}
          </select>
          <select name="priority" className="rounded-lg border px-3 py-2 text-sm">
            {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((value) => <option key={value}>{value}</option>)}
          </select>
          <textarea name="description" required minLength={5} placeholder="Describe the support need" className="min-h-20 rounded-lg border px-3 py-2 text-sm md:col-span-2" />
          <button disabled={saving} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 md:col-span-2">
            {saving ? 'Creating…' : 'Create case'}
          </button>
        </form>
        {actionError && <p role="alert" className="mt-3 text-sm text-red-600">{actionError}</p>}
      </section>
      <RecordListPage
        key={refresh}
        title="Support Cases"
        subtitle="Manage case ownership and lifecycle transitions"
        load={supportCasesApi.list}
        columns={columns}
        pageSize={25}
        filterKey="student_id"
        filterLabel="Student ID"
        filterPlaceholder="Filter by student ID"
        rowActions={rowActions}
      />
    </div>
  );
}
