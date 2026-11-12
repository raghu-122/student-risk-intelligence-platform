import { useState } from 'react';
import { Download } from 'lucide-react';
import { PageHeader } from '../../components/common';
import { reportsApi } from '../../services/api';

const reportOptions = [
  { label: 'Students', filename: 'students.csv', download: reportsApi.downloadStudents },
  { label: 'Risk assessments', filename: 'risk-assessments.csv', download: reportsApi.downloadRisk },
  { label: 'Interventions', filename: 'interventions.csv', download: reportsApi.downloadInterventions },
  { label: 'Outcomes', filename: 'outcomes.csv', download: reportsApi.downloadOutcomes },
  { label: 'Data-quality issues', filename: 'data-quality.csv', download: reportsApi.downloadDataQuality },
  { label: 'Ground-truth labels', filename: 'ground-truth.csv', download: reportsApi.downloadGroundTruth },
  { label: 'Validation report', filename: 'validation-report.json', download: reportsApi.downloadValidationReport },
];

export default function Reports() {
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState('');
  return (
    <div>
      <PageHeader title="Reports & Exports" subtitle="Download persisted records and evaluation evidence" />
      {error && <p role="alert" className="mb-4 text-sm text-red-600">{error}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {reportOptions.map((report) => (
          <button
            key={report.filename}
            disabled={Boolean(downloading)}
            onClick={async () => {
              setDownloading(report.filename);
              setError('');
              try {
                const response = await report.download();
                const url = URL.createObjectURL(response.data as Blob);
                const anchor = document.createElement('a');
                anchor.href = url;
                anchor.download = report.filename;
                anchor.click();
                anchor.remove();
                window.setTimeout(() => URL.revokeObjectURL(url), 1000);
              } catch {
                setError(`Could not download ${report.label.toLowerCase()}.`);
              } finally {
                setDownloading('');
              }
            }}
            className="flex items-center justify-between rounded-xl border border-gray-100 bg-white p-5 text-left shadow-sm hover:border-indigo-200 disabled:opacity-50"
          >
            <span><span className="block font-medium text-gray-800">{report.label}</span><span className="text-xs text-gray-500">{report.filename}</span></span>
            <span className="flex items-center gap-2 text-sm text-indigo-600"><Download size={16} />{downloading === report.filename ? 'Preparing…' : 'Download'}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
