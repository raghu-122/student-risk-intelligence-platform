import { useEffect, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import type { AxiosResponse } from 'axios';
import { EmptyState, ErrorState, LoadingSpinner, PageHeader, Pagination } from './index';

export type RecordRow = Record<string, unknown>;

export interface RecordColumn {
  key: string;
  label: string;
  render?: (value: unknown, row: RecordRow) => ReactNode;
}

interface PageResult {
  items?: RecordRow[];
  total?: number;
  pages?: number;
}

interface RecordListPageProps {
  title: string;
  subtitle: string;
  load: (params: Record<string, unknown>) => Promise<AxiosResponse<unknown>>;
  columns: RecordColumn[];
  pageSize?: number;
  filterKey?: string;
  filterLabel?: string;
  filterPlaceholder?: string;
  refreshToken?: number;
  rowActions?: (row: RecordRow, refresh: () => void) => ReactNode;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export default function RecordListPage({
  title,
  subtitle,
  load,
  columns,
  pageSize = 25,
  filterKey,
  filterLabel = 'Filter',
  filterPlaceholder = '',
  refreshToken = 0,
  rowActions,
}: RecordListPageProps) {
  const [rows, setRows] = useState<RecordRow[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [draftFilter, setDraftFilter] = useState('');
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    const params: Record<string, unknown> = { page, page_size: pageSize };
    if (filterKey && filter) params[filterKey] = filter;

    load(params)
      .then((response) => {
        if (!active) return;
        const result = response.data as PageResult | RecordRow[];
        const items = Array.isArray(result) ? result : result.items ?? [];
        const totalItems = Array.isArray(result) ? items.length : result.total ?? items.length;
        setRows(items);
        setTotal(totalItems);
        setPages(Array.isArray(result) ? 1 : Math.max(1, result.pages ?? Math.ceil(totalItems / pageSize)));
      })
      .catch(() => {
        if (active) setError(`Could not load ${title.toLowerCase()}. Check the backend connection and try again.`);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [filter, filterKey, load, page, pageSize, refreshToken, retryToken, title]);

  const submitFilter = (event: FormEvent) => {
    event.preventDefault();
    setPage(1);
    setFilter(draftFilter.trim());
  };

  if (loading) return <LoadingSpinner message={`Loading ${title.toLowerCase()}...`} />;
  if (error) return <ErrorState message={error} onRetry={() => setRetryToken((value) => value + 1)} />;

  return (
    <section>
      <PageHeader title={title} subtitle={`${subtitle} · ${total.toLocaleString()} records`} />
      {filterKey && (
        <form onSubmit={submitFilter} className="flex gap-2 mb-4 max-w-xl">
          <label className="sr-only" htmlFor={`${filterKey}-filter`}>{filterLabel}</label>
          <input
            id={`${filterKey}-filter`}
            value={draftFilter}
            onChange={(event) => setDraftFilter(event.target.value)}
            placeholder={filterPlaceholder || filterLabel}
            className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button type="submit" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
            Apply
          </button>
        </form>
      )}
      <div className="overflow-x-auto rounded-xl border border-gray-100 bg-white shadow-sm">
        {rows.length === 0 ? <EmptyState message={`No ${title.toLowerCase()} found`} /> : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-gray-500">
              <tr>
                {columns.map((column) => <th key={column.key} className="whitespace-nowrap px-4 py-3 font-medium">{column.label}</th>)}
                {rowActions && <th className="whitespace-nowrap px-4 py-3 font-medium">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {rows.map((row, index) => (
                <tr key={String(row[columns[0]?.key] ?? index)} className="hover:bg-gray-50">
                  {columns.map((column) => (
                    <td key={column.key} className="max-w-sm px-4 py-3 text-gray-700">
                      {column.render ? column.render(row[column.key], row) : formatValue(row[column.key])}
                    </td>
                  ))}
                  {rowActions && <td className="px-4 py-3">{rowActions(row, () => setRetryToken((value) => value + 1))}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <Pagination page={page} totalPages={pages} onPageChange={setPage} />
    </section>
  );
}
