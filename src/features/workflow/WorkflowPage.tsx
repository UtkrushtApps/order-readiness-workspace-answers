import { useMemo, useState } from 'react';
import type { WorkflowFilters } from '../../api/contracts';
import { WorkflowFiltersPanel } from './components/WorkflowFilters';
import { WorkflowResults } from './components/WorkflowResults';
import { useWorkflowData } from './hooks/useWorkflowData';

const initialFilters: WorkflowFilters = {
  status: 'all',
  readiness: 'all',
  search: '',
  page: 1,
  pageSize: 25
};

export function WorkflowPage() {
  const [filters, setFilters] = useState<WorkflowFilters>(initialFilters);
  const { data, error, loading, reload } = useWorkflowData(filters);

  const resultSummary = useMemo(() => {
    if (!data) {
      return 'No queue data loaded';
    }
    return `${data.meta.total} matching orders across ${data.meta.totalPages} pages`;
  }, [data]);

  const onPageChange = (page: number) => {
    setFilters((current) => ({ ...current, page }));
  };

  return (
    <section className="workflow-card" aria-labelledby="workflow-title">
      <div className="workflow-heading">
        <div>
          <h2 id="workflow-title">Readiness queue</h2>
          <p>{resultSummary}</p>
        </div>
        <button type="button" className="secondary" onClick={reload}>
          Refresh
        </button>
      </div>

      <WorkflowFiltersPanel filters={filters} onChange={setFilters} />
      <WorkflowResults response={data} loading={loading} error={error} onPageChange={onPageChange} />
    </section>
  );
}
