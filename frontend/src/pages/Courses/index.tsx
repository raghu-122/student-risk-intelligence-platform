import RecordListPage, { RecordColumn } from '../../components/common/RecordListPage';
import { coursesApi } from '../../services/api';

const columns: RecordColumn[] = [
  { key: 'course_code', label: 'Code' },
  { key: 'course_name', label: 'Course' },
  { key: 'department', label: 'Department' },
  { key: 'credits', label: 'Credits' },
  { key: 'semester', label: 'Semester' },
  { key: 'instructor_id', label: 'Instructor' },
];

export default function Courses() {
  return (
    <RecordListPage
      title="Courses"
      subtitle="Course catalogue and instructor assignments"
      load={coursesApi.list}
      columns={columns}
      filterKey="search"
      filterLabel="Search courses"
      filterPlaceholder="Search by course name or code"
    />
  );
}
