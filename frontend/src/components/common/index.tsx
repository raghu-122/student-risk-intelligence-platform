export function LoadingSpinner({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
      <p className="text-gray-500 text-sm">{message}</p>
    </div>
  );
}

export function ErrorState({ message = 'Something went wrong', onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3 text-red-500">
      <div className="text-4xl">⚠️</div>
      <p className="font-medium">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="text-sm text-indigo-600 hover:underline">
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message = 'No data found' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3 text-gray-400">
      <div className="text-4xl">📭</div>
      <p>{message}</p>
    </div>
  );
}

export function Badge({ label, color }: { label: string; color: 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray' | 'indigo' }) {
  const colors = {
    red: 'bg-red-100 text-red-700',
    orange: 'bg-orange-100 text-orange-700',
    yellow: 'bg-yellow-100 text-yellow-700',
    green: 'bg-green-100 text-green-700',
    blue: 'bg-blue-100 text-blue-700',
    gray: 'bg-gray-100 text-gray-600',
    indigo: 'bg-indigo-100 text-indigo-700',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[color]}`}>
      {label}
    </span>
  );
}

export function RiskBadge({ category }: { category: string }) {
  const map: Record<string, { label: string; color: 'red' | 'orange' | 'yellow' | 'green' | 'gray' }> = {
    CRITICAL: { label: 'Critical', color: 'red' },
    HIGH: { label: 'High', color: 'orange' },
    MEDIUM: { label: 'Medium', color: 'yellow' },
    LOW: { label: 'Low', color: 'green' },
    INSUFFICIENT_DATA: { label: 'No Data', color: 'gray' },
  };
  const cfg = map[category] ?? { label: category, color: 'gray' as const };
  return <Badge label={cfg.label} color={cfg.color} />;
}

export function StatCard({ label, value, sub, icon, color = 'indigo' }: {
  label: string; value: string | number; sub?: string;
  icon?: React.ReactNode; color?: 'indigo' | 'red' | 'green' | 'orange';
}) {
  const colors = {
    indigo: 'bg-indigo-50 text-indigo-600',
    red: 'bg-red-50 text-red-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
  };
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-start gap-4">
      {icon && <div className={`p-3 rounded-lg ${colors[color]}`}>{icon}</div>}
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800">{title}</h2>
        {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

export function Pagination({
  page, totalPages, onPageChange,
}: { page: number; totalPages: number; onPageChange: (p: number) => void }) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-center gap-2 mt-4">
      <button
        onClick={() => onPageChange(page - 1)} disabled={page <= 1}
        className="px-3 py-1.5 text-sm border rounded disabled:opacity-40 hover:bg-gray-50"
      >← Prev</button>
      <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
      <button
        onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}
        className="px-3 py-1.5 text-sm border rounded disabled:opacity-40 hover:bg-gray-50"
      >Next →</button>
    </div>
  );
}

