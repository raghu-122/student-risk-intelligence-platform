import RecordListPage, { RecordColumn } from '../../components/common/RecordListPage';
import { lmsApi } from '../../services/api';

const columns: RecordColumn[] = [
  { key: 'activity_timestamp', label: 'Timestamp' },
  { key: 'enrollment_id', label: 'Enrollment' },
  { key: 'activity_type', label: 'Activity' },
  { key: 'duration_minutes', label: 'Duration (min)' },
];

export default function Engagement() {
  return (
    <RecordListPage
      title="LMS Engagement"
      subtitle="Learning-platform activity"
      load={lmsApi.list}
      columns={columns}
      pageSize={50}
      filterKey="enrollment_id"
      filterLabel="Enrollment ID"
      filterPlaceholder="Filter by enrollment ID"
    />
  );
}
