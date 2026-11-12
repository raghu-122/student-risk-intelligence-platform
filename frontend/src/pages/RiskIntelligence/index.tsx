import RecordListPage, { RecordColumn } from '../../components/common/RecordListPage';
import { Link } from 'react-router-dom';
import { RiskBadge } from '../../components/common';
import { riskApi } from '../../services/api';

const columns: RecordColumn[] = [
  {
    key: 'student_id',
    label: 'Student',
    render: (value) => <Link className="text-indigo-600 hover:underline" to={`/students/${value}`}>{String(value ?? '')}</Link>,
  },
  { key: 'risk_score', label: 'Risk score', render: (value) => typeof value === 'number' ? value.toFixed(1) : 'Insufficient data' },
  { key: 'risk_category', label: 'Category', render: (value) => <RiskBadge category={String(value ?? 'INSUFFICIENT_DATA')} /> },
  { key: 'cutoff_date', label: 'Cutoff' },
  { key: 'data_completeness', label: 'Completeness', render: (value) => typeof value === 'number' ? `${Math.round(value * 100)}%` : '—' },
  { key: 'model_version', label: 'Model' },
  { key: 'reasons', label: 'Risk explanation', render: (value) => Array.isArray(value) ? value.join('; ') : String(value ?? '—') },
];

export default function RiskIntelligence() {
  return (
    <RecordListPage
      title="Risk Intelligence"
      subtitle="Explainable scores use information available on each record's cutoff date"
      load={riskApi.list}
      columns={columns}
      pageSize={25}
      filterKey="risk_category"
      filterLabel="Risk category"
      filterPlaceholder="LOW, MEDIUM, HIGH, CRITICAL"
    />
  );
}
