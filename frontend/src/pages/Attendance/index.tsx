import RecordListPage, { RecordColumn } from '../../components/common/RecordListPage';
import { attendanceApi } from '../../services/api';
import { Badge } from '../../components/common';

const columns: RecordColumn[] = [
  { key: 'attendance_date', label: 'Date' },
  { key: 'enrollment_id', label: 'Enrollment' },
  { key: 'session_number', label: 'Session' },
  {
    key: 'attendance_status',
    label: 'Status',
    render: (value) => <Badge label={String(value ?? 'Unknown')} color={value === 'PRESENT' ? 'green' : value === 'APPROVED_ABSENCE' ? 'blue' : value === 'LATE' ? 'orange' : 'red'} />,
  },
];

export default function Attendance() {
  return (
    <RecordListPage
      title="Attendance"
      subtitle="Attendance events; approved absences are excluded from risk denominators"
      load={attendanceApi.list}
      columns={columns}
      pageSize={50}
      filterKey="enrollment_id"
      filterLabel="Enrollment ID"
      filterPlaceholder="Filter by enrollment ID"
    />
  );
}
