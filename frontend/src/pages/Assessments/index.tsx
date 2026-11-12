import { useState } from 'react';
import RecordListPage, { RecordColumn } from '../../components/common/RecordListPage';
import { assessmentsApi } from '../../services/api';

const assessmentColumns: RecordColumn[] = [
  { key: 'assessment_date', label: 'Date' },
  { key: 'assessment_name', label: 'Assessment' },
  { key: 'assessment_type', label: 'Type' },
  { key: 'course_id', label: 'Course' },
  { key: 'maximum_marks', label: 'Maximum marks' },
  { key: 'weightage', label: 'Weight' },
];

const resultColumns: RecordColumn[] = [
  { key: 'assessment_id', label: 'Assessment' },
  { key: 'enrollment_id', label: 'Enrollment' },
  { key: 'marks_obtained', label: 'Marks' },
  { key: 'percentage', label: 'Percent' },
  { key: 'submission_status', label: 'Submission status' },
];

export default function Assessments() {
  const [view, setView] = useState<'assessments' | 'results'>('assessments');
  return (
    <div className="space-y-5">
      <div className="flex gap-2">
        <button onClick={() => setView('assessments')} className={`rounded-lg px-4 py-2 text-sm ${view === 'assessments' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border'}`}>Assessments</button>
        <button onClick={() => setView('results')} className={`rounded-lg px-4 py-2 text-sm ${view === 'results' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border'}`}>Results</button>
      </div>
      {view === 'assessments' ? (
        <RecordListPage title="Assessments" subtitle="Assessment schedule and course weightings" load={assessmentsApi.list} columns={assessmentColumns} filterKey="course_id" filterLabel="Course ID" filterPlaceholder="Filter by course ID" />
      ) : (
        <RecordListPage title="Assessment results" subtitle="Submitted, late, and missing assessment records" load={assessmentsApi.listResults} columns={resultColumns} pageSize={50} filterKey="enrollment_id" filterLabel="Enrollment ID" filterPlaceholder="Filter by enrollment ID" />
      )}
    </div>
  );
}
