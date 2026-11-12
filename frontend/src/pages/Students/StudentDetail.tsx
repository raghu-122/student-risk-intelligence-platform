import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ErrorState, LoadingSpinner, PageHeader, RiskBadge } from '../../components/common';
import { attendanceApi, studentsApi } from '../../services/api';

type Row = Record<string, unknown>;

interface StudentProfileData {
  student: Row;
  enrollments: Row[];
  risks: Row[];
  cases: Row[];
  interventions: Row[];
}

function RowsTable({ title, rows, columns }: { title: string; rows: Row[]; columns: string[] }) {
  return (
    <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <h3 className="mb-3 font-semibold text-gray-800">{title}</h3>
      {rows.length === 0 ? <p className="text-sm text-gray-400">No records available.</p> : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-gray-500">
              <tr>{columns.map((column) => <th className="whitespace-nowrap px-3 py-2 font-medium" key={column}>{column.replace(/_/g, ' ')}</th>)}</tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((row, index) => (
                <tr key={String(row[columns[0]] ?? index)}>
                  {columns.map((column) => <td className="whitespace-nowrap px-3 py-2 text-gray-700" key={column}>{String(row[column] ?? '—')}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function StudentDetail() {
  const { id = '' } = useParams();
  const [data, setData] = useState<StudentProfileData | null>(null);
  const [attendance, setAttendance] = useState<Record<string, Row>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      studentsApi.get(id),
      studentsApi.getEnrollments(id),
      studentsApi.getRiskHistory(id),
      studentsApi.getSupportCases(id),
      studentsApi.getInterventions(id),
    ])
      .then(async ([student, enrollments, risks, cases, interventions]) => {
        const enrollmentRows = enrollments.data as Row[];
        const summaries = await Promise.all(enrollmentRows.map(async (enrollment) => {
          const enrollmentId = String(enrollment.enrollment_id);
          const response = await attendanceApi.getSummary(enrollmentId);
          return [enrollmentId, response.data as Row] as const;
        }));
        if (!active) return;
        setData({
          student: student.data as Row,
          enrollments: enrollmentRows,
          risks: risks.data as Row[],
          cases: cases.data as Row[],
          interventions: interventions.data as Row[],
        });
        setAttendance(Object.fromEntries(summaries));
      })
      .catch(() => {
        if (active) setError('Could not load this student profile and its risk history.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [id]);

  if (loading) return <LoadingSpinner message="Loading student profile..." />;
  if (error || !data) return <ErrorState message={error || 'Student not found.'} />;

  const student = data.student;
  const latestRisk = data.risks[0];
  const factors = latestRisk?.factor_scores;
  const factorRows = factors && typeof factors === 'object'
    ? Object.entries(factors as Record<string, unknown>).map(([factor, score]) => ({ factor, score }))
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${student.first_name} ${student.last_name}`}
        subtitle={`${student.student_id} · ${student.program} · ${student.department}`}
        action={<Link to="/students" className="text-sm text-indigo-600 hover:underline">Back to students</Link>}
      />
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border bg-white p-5 shadow-sm">
          <p className="text-sm text-gray-500">Student status</p>
          <p className="mt-1 text-lg font-semibold">{String(student.current_status)}</p>
          <p className="mt-2 text-sm text-gray-500">{String(student.email)}</p>
        </div>
        <div className="rounded-xl border bg-white p-5 shadow-sm">
          <p className="text-sm text-gray-500">Latest risk</p>
          {latestRisk ? <div className="mt-2 flex items-center gap-3"><strong className="text-2xl">{String(latestRisk.risk_score ?? '—')}</strong><RiskBadge category={String(latestRisk.risk_category)} /></div> : <p className="mt-2 text-sm text-gray-400">No risk assessment yet.</p>}
          {latestRisk && <p className="mt-2 text-xs text-gray-500">Cutoff {String(latestRisk.cutoff_date)} · completeness {typeof latestRisk.data_completeness === 'number' ? `${Math.round(latestRisk.data_completeness * 100)}%` : '—'}</p>}
        </div>
        <div className="rounded-xl border bg-white p-5 shadow-sm">
          <p className="text-sm text-gray-500">Attendance by enrollment</p>
          <div className="mt-2 space-y-1">
            {data.enrollments.map((enrollment) => {
              const summary = attendance[String(enrollment.enrollment_id)];
              return <p className="text-sm" key={String(enrollment.enrollment_id)}>{String(enrollment.course_id)}: {typeof summary?.attendance_rate === 'number' ? `${(summary.attendance_rate * 100).toFixed(1)}%` : 'No records'}</p>;
            })}
          </div>
        </div>
      </div>
      {latestRisk && (
        <section className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 className="mb-3 font-semibold text-gray-800">Risk factor explanation</h3>
          {factorRows.length === 0 ? <p className="text-sm text-gray-400">No factor details are available for this assessment.</p> : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {factorRows.map(({ factor, score }) => (
                <div key={factor} className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs uppercase tracking-wide text-gray-500">{factor.replace(/_/g, ' ')}</p>
                  <p className="mt-1 font-semibold text-gray-900">{score === null ? 'Insufficient data' : String(score)}</p>
                </div>
              ))}
            </div>
          )}
          {Array.isArray(latestRisk.reasons) && (
            <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-gray-600">
              {(latestRisk.reasons as unknown[]).map((reason, index) => <li key={index}>{String(reason)}</li>)}
            </ul>
          )}
        </section>
      )}
      <RowsTable title="Enrollments" rows={data.enrollments} columns={['course_id', 'status', 'final_grade', 'effective_from', 'effective_to']} />
      <RowsTable title="Risk history" rows={data.risks} columns={['risk_id', 'risk_score', 'risk_category', 'cutoff_date', 'assessment_timestamp']} />
      <RowsTable title="Support cases" rows={data.cases} columns={['case_id', 'case_type', 'priority', 'case_status', 'opened_at']} />
      <RowsTable title="Interventions" rows={data.interventions} columns={['intervention_id', 'intervention_type', 'intervention_status', 'trigger_date', 'due_date']} />
    </div>
  );
}
