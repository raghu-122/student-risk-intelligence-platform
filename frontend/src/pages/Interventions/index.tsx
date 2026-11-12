import { FormEvent, useState } from 'react';
import RecordListPage, { RecordColumn, RecordRow } from '../../components/common/RecordListPage';
import { interventionsApi } from '../../services/api';

const columns: RecordColumn[] = [
  { key: 'intervention_id', label: 'Intervention' },
  { key: 'student_id', label: 'Student' },
  { key: 'intervention_type', label: 'Type' },
  { key: 'intervention_status', label: 'Status' },
  { key: 'trigger_date', label: 'Trigger date' },
  { key: 'due_date', label: 'Due date' },
  { key: 'assigned_staff_id', label: 'Assigned staff' },
];

const transitions: Record<string, string[]> = {
  RECOMMENDED: ['APPROVED', 'REJECTED'],
  APPROVED: ['ASSIGNED', 'CANCELLED'],
  ASSIGNED: ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
  COMPLETED: [],
  CANCELLED: [],
  REJECTED: [],
};

export default function Interventions() {
  const [refresh, setRefresh] = useState(0);
  const [actionError, setActionError] = useState('');
  const [saving, setSaving] = useState(false);

  const createIntervention = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setActionError('');
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const triggerDate = String(form.get('trigger_date'));
    const startDate = String(form.get('start_date'));
    if (startDate && startDate < triggerDate) {
      setActionError('Start date must be on or after the trigger date.');
      setSaving(false);
      return;
    }
    try {
      await interventionsApi.create({
        student_id: String(form.get('student_id')).trim(),
        enrollment_id: String(form.get('enrollment_id')).trim() || null,
        intervention_type: String(form.get('intervention_type')),
        trigger_date: triggerDate,
        start_date: startDate || null,
        due_date: String(form.get('due_date')) || null,
        assigned_staff_id: String(form.get('assigned_staff_id')).trim() || null,
        expected_outcome: String(form.get('expected_outcome')).trim() || null,
      });
      formElement.reset();
      setRefresh((value) => value + 1);
    } catch {
      setActionError('Could not create intervention. Verify the student, enrollment, and staff IDs.');
    } finally {
      setSaving(false);
    }
  };

  const rowActions = (row: RecordRow, reload: () => void) => {
    const next = transitions[String(row.intervention_status)]?.[0];
    if (!next) return <span className="text-xs text-gray-400">Final state</span>;
    return (
      <button
        onClick={async () => {
          setActionError('');
          try {
            await interventionsApi.transition(
              String(row.intervention_id),
              next,
              next === 'COMPLETED' ? 'Marked completed in the intervention tracker.' : undefined,
              next === 'COMPLETED' ? new Date().toISOString().slice(0, 10) : undefined,
            );
            reload();
          } catch {
            setActionError(`Could not move intervention ${String(row.intervention_id)} to ${next}.`);
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
        <h2 className="mb-4 font-semibold text-gray-800">Create an intervention</h2>
        <form onSubmit={createIntervention} className="grid gap-3 md:grid-cols-2">
          <input name="student_id" required placeholder="Student ID" className="rounded-lg border px-3 py-2 text-sm" />
          <input name="enrollment_id" placeholder="Enrollment ID (optional)" className="rounded-lg border px-3 py-2 text-sm" />
          <select name="intervention_type" className="rounded-lg border px-3 py-2 text-sm">
            {['ATTENDANCE_COUNSELLING', 'ACADEMIC_TUTORING', 'INSTRUCTOR_MEETING', 'ENGAGEMENT_SUPPORT', 'ADVISOR_REVIEW', 'WELFARE_ASSESSMENT', 'PERSONALIZED_PLAN'].map((value) => <option key={value}>{value}</option>)}
          </select>
          <input name="assigned_staff_id" placeholder="Assigned staff ID (optional)" className="rounded-lg border px-3 py-2 text-sm" />
          <label className="text-xs text-gray-500">Trigger date<input name="trigger_date" type="date" required className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm" /></label>
          <label className="text-xs text-gray-500">Start date<input name="start_date" type="date" className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm" /></label>
          <label className="text-xs text-gray-500">Due date<input name="due_date" type="date" className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm" /></label>
          <input name="expected_outcome" placeholder="Expected outcome (optional)" className="rounded-lg border px-3 py-2 text-sm" />
          <button disabled={saving} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 md:col-span-2">
            {saving ? 'Creating…' : 'Create intervention'}
          </button>
        </form>
        {actionError && <p role="alert" className="mt-3 text-sm text-red-600">{actionError}</p>}
      </section>
      <RecordListPage
        key={refresh}
        title="Interventions"
        subtitle="Track lifecycle changes and completion"
        load={interventionsApi.list}
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
